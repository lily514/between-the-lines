"""One possession: the actions a team makes from getting the ball until the other team has it.

Everything here is in the attacking direction of the team in possession (towards x = 105).
Each step picks an action from the ball's zone, an end point from a random kernel aimed at
goal, and success from a base rate adjusted by distance and the two teams' strengths. The
chain ends when the ball goes to the other team, and says how that team's possession starts,
in that team's own direction, so the engine can hand straight over.
"""

import math
from dataclasses import dataclass

from numpy.random import Generator

from btl.league.league import Role
from btl.schema.vocab import ActionType, BodyPart, Phase, Result
from btl.sim.params import SimParams
from btl.sim.pitch import (
    GOAL_WIDTH,
    PITCH_LENGTH,
    PITCH_WIDTH,
    Lane,
    Point,
    Third,
    clamp_to_pitch,
    distance,
    distance_to_goal,
    goal_angle,
    in_penalty_area,
    mirror,
    zone_of,
)
from btl.sim.shape import Formation, team_shape

CENTRE_SPOT = Point(PITCH_LENGTH / 2, PITCH_WIDTH / 2)
KEEPER_ACTIONS = frozenset({ActionType.KEEPER_SAVE, ActionType.KEEPER_CLAIM})
# Passes and dribbles stop this far inside the lines; there are no throw-ins yet.
EDGE_MARGIN = 1.0
SIX_YARD_DEPTH = 5.5
SIX_YARD_HALF_WIDTH = 9.16


@dataclass(frozen=True, slots=True)
class Side:
    """What a chain needs to know about one team."""

    formation: Formation
    strength: float


@dataclass(frozen=True, slots=True)
class Start:
    """How a possession begins, in the team's own attacking direction.

    A start with ``won_with`` opens with that ball-winning action. One without is a restart
    (a kickoff, or the keeper's kick after a missed shot), so its first action is a set piece.
    """

    ball: Point
    slot: int
    won_with: ActionType | None = None
    kickoff: bool = False
    delay: float = 0.0


@dataclass(frozen=True, slots=True)
class Step:
    """One action, with ``slot`` the actor's formation slot.

    ``duration`` is the time until the next action starts.
    """

    slot: int
    action_type: ActionType
    result: Result
    bodypart: BodyPart
    start: Point
    end: Point
    duration: float
    phase: Phase


@dataclass(frozen=True, slots=True)
class Chain:
    """A whole possession, and how the other team's possession starts."""

    steps: tuple[Step, ...]
    next_start: Start


@dataclass(frozen=True, slots=True)
class _Play:
    """Everything an action needs besides where the ball is and who has it."""

    attack: Side
    defence: Side
    strength_ratio: float
    rng: Generator
    params: SimParams


@dataclass(frozen=True, slots=True)
class _Outcome:
    """One action, then who has the ball next, or how the other team's possession starts."""

    step: Step
    receiver: int
    handover: Start | None = None


def kickoff(side: Side, delay: float = 0.0) -> Start:
    """A kickoff from the centre spot, taken by the outfield player nearest it."""
    return Start(
        CENTRE_SPOT,
        _nearest(side.formation, CENTRE_SPOT, in_possession=True),
        kickoff=True,
        delay=delay,
    )


def play_chain(
    attack: Side, defence: Side, start: Start, rng: Generator, params: SimParams
) -> Chain:
    """Simulate one possession.

    Args:
        attack: The team in possession.
        defence: The other team.
        start: How the possession begins.
        rng: The engine's random stream.
        params: The simulator's knobs.

    Returns:
        The possession's actions, and how the other team's possession starts.
    """
    play = _Play(attack, defence, attack.strength / defence.strength, rng, params)
    steps: list[Step] = []
    ball, slot = start.ball, start.slot
    if start.won_with is not None:
        bodypart = BodyPart.OTHER if start.won_with in KEEPER_ACTIONS else BodyPart.FOOT
        duration = _between(rng, params.reaction_time)
        steps.append(
            Step(
                slot,
                start.won_with,
                Result.SUCCESS,
                bodypart,
                ball,
                ball,
                duration,
                Phase.TRANSITION,
            )
        )
    after_cross = False

    while True:
        phase = _phase(start, steps, params)
        is_keeper = attack.formation.slots[slot].role is Role.GOALKEEPER
        if start.kickoff and not steps:
            back = Point(ball.x - rng.uniform(8, 14), ball.y + rng.uniform(-8, 8))
            outcome = _pass(slot, ball, back, phase, play)
        else:
            action = _choose_action(ball, is_keeper, after_cross, rng, params)
            if action is ActionType.SHOT:
                outcome = _shoot(slot, ball, after_cross, phase, play)
            elif action is ActionType.CROSS:
                outcome = _cross(slot, ball, phase, play)
            elif action is ActionType.DRIBBLE:
                outcome = _dribble(slot, ball, phase, play)
            elif is_keeper:
                target = _kick(ball, params.keeper_pass_length_mean, params.keeper_pass_kappa, play)
                outcome = _pass(slot, ball, target, phase, play)
            else:
                third = zone_of(ball).third
                length_mean, kappa = params.pass_length_mean.of(third), params.pass_kappa.of(third)
                outcome = _pass(slot, ball, _kick(ball, length_mean, kappa, play), phase, play)
        steps.append(outcome.step)
        if outcome.handover is not None:
            return Chain(tuple(steps), outcome.handover)
        after_cross = outcome.step.action_type is ActionType.CROSS
        ball, slot = outcome.step.end, outcome.receiver


def _choose_action(
    ball: Point, is_keeper: bool, after_cross: bool, rng: Generator, params: SimParams
) -> ActionType:
    if is_keeper:
        return ActionType.PASS
    if in_penalty_area(ball):
        shot_share = params.header_share_after_cross if after_cross else params.shot_share_in_box
    elif distance_to_goal(ball) <= params.shot_range:
        shot_share = params.shot_share_in_range
    else:
        shot_share = 0.0
    if rng.random() < shot_share:
        return ActionType.SHOT
    zone = zone_of(ball)
    on_wing = zone.third is Third.ATTACKING and zone.lane is not Lane.CENTRE
    if on_wing and rng.random() < params.cross_share_on_wing:
        return ActionType.CROSS
    if rng.random() < params.dribble_share.of(zone.third):
        return ActionType.DRIBBLE
    return ActionType.PASS


def _pass(slot: int, ball: Point, target: Point, phase: Phase, play: _Play) -> _Outcome:
    end = clamp_to_pitch(target, EDGE_MARGIN)
    length = distance(ball, end)
    params = play.params
    success = params.pass_success.of(zone_of(end).third) * math.exp(
        -max(0.0, length - params.long_pass_from) / params.long_pass_falloff
    )
    if not _succeeds(success, play):
        return _lose(slot, ActionType.PASS, ball, end, params.pass_speed, phase, play)
    duration = length / params.pass_speed + _between(play.rng, params.control_time)
    return _Outcome(
        Step(slot, ActionType.PASS, Result.SUCCESS, BodyPart.FOOT, ball, end, duration, phase),
        _nearest(play.attack.formation, end, in_possession=True, exclude=slot),
    )


def _dribble(slot: int, ball: Point, phase: Phase, play: _Play) -> _Outcome:
    params = play.params
    end = _kick(ball, params.dribble_length_mean, params.dribble_kappa, play)
    if not _succeeds(params.dribble_success, play):
        return _lose(slot, ActionType.DRIBBLE, ball, end, params.dribble_speed, phase, play)
    duration = distance(ball, end) / params.dribble_speed + _between(play.rng, params.reaction_time)
    return _Outcome(
        Step(slot, ActionType.DRIBBLE, Result.SUCCESS, BodyPart.FOOT, ball, end, duration, phase),
        slot,
    )


def _lose(
    slot: int,
    action: ActionType,
    ball: Point,
    end: Point,
    speed: float,
    phase: Phase,
    play: _Play,
) -> _Outcome:
    """A pass or dribble that the nearest opponent gets to, somewhere in its second half."""
    fraction = play.rng.uniform(0.4, 1.0)
    lost_at = Point(ball.x + fraction * (end.x - ball.x), ball.y + fraction * (end.y - ball.y))
    duration = distance(ball, lost_at) / speed + _between(play.rng, play.params.reaction_time)
    winner = _nearest(play.defence.formation, mirror(lost_at), in_possession=False)
    won_with = ActionType.TACKLE if action is ActionType.DRIBBLE else ActionType.INTERCEPTION
    return _Outcome(
        Step(slot, action, Result.FAIL, BodyPart.FOOT, ball, lost_at, duration, phase),
        slot,
        Start(mirror(lost_at), winner, won_with),
    )


def _cross(slot: int, ball: Point, phase: Phase, play: _Play) -> _Outcome:
    rng, params = play.rng, play.params
    end = clamp_to_pitch(Point(rng.uniform(88, 100), rng.normal(PITCH_WIDTH / 2, 6)), EDGE_MARGIN)
    flight = distance(ball, end) / params.pass_speed
    if _succeeds(params.cross_success, play):
        duration = flight + _between(rng, params.reaction_time)
        return _Outcome(
            Step(slot, ActionType.CROSS, Result.SUCCESS, BodyPart.FOOT, ball, end, duration, phase),
            _nearest(play.attack.formation, end, in_possession=True, exclude=slot),
        )
    if rng.random() < params.keeper_claim_share:
        handover = Start(mirror(end), _keeper(play.defence.formation), ActionType.KEEPER_CLAIM)
    else:
        winner = _nearest(play.defence.formation, mirror(end), in_possession=False)
        handover = Start(mirror(end), winner, ActionType.INTERCEPTION)
    return _Outcome(
        Step(slot, ActionType.CROSS, Result.FAIL, BodyPart.FOOT, ball, end, flight, phase),
        slot,
        handover,
    )


def _shoot(slot: int, ball: Point, header: bool, phase: Phase, play: _Play) -> _Outcome:
    """A shot always ends the possession: a goal, a save, or a miss."""
    rng, params = play.rng, play.params
    bodypart = BodyPart.HEAD if header else BodyPart.FOOT
    logit = (
        params.goal_intercept
        + params.goal_per_radian * goal_angle(ball)
        + params.goal_per_metre * distance_to_goal(ball)
    )
    on_target = Point(PITCH_LENGTH, PITCH_WIDTH / 2 + rng.uniform(-1, 1) * (GOAL_WIDTH / 2 - 0.3))
    if _succeeds(1 / (1 + math.exp(-logit)), play):
        result, end = Result.SUCCESS, on_target
        handover = kickoff(play.defence, delay=params.goal_restart_delay)
    elif rng.random() < params.save_share:
        result, end = Result.FAIL, on_target
        save_at = Point(PITCH_LENGTH - 1, on_target.y)
        handover = Start(mirror(save_at), _keeper(play.defence.formation), ActionType.KEEPER_SAVE)
    else:
        wide = rng.choice((-1.0, 1.0)) * rng.uniform(GOAL_WIDTH / 2 + 0.5, 12)
        result, end = Result.FAIL, Point(PITCH_LENGTH, PITCH_WIDTH / 2 + wide)
        # Stands in for a goal kick until restarts arrive.
        across = rng.uniform(-1, 1) * SIX_YARD_HALF_WIDTH
        goal_kick = Point(SIX_YARD_DEPTH, PITCH_WIDTH / 2 + across)
        handover = Start(
            goal_kick, _keeper(play.defence.formation), delay=params.miss_restart_delay
        )
    step = Step(slot, ActionType.SHOT, result, bodypart, ball, end, params.shot_flight, phase)
    return _Outcome(step, slot, handover)


def _phase(start: Start, steps: list[Step], params: SimParams) -> Phase:
    if start.won_with is None:
        return Phase.SET_PIECE if not steps else Phase.OPEN_PLAY
    elapsed = sum(step.duration for step in steps)
    return Phase.TRANSITION if elapsed < params.transition_seconds else Phase.OPEN_PLAY


def _succeeds(probability: float, play: _Play) -> bool:
    """Scale the odds, not the probability, so a stronger side never goes past certainty."""
    odds = probability / (1 - probability) * play.strength_ratio**play.params.strength_exponent
    return play.rng.random() < odds / (1 + odds)


def _kick(ball: Point, length_mean: float, kappa: float, play: _Play) -> Point:
    """An end point a random length away, in a direction scattered around straight at goal."""
    shape = play.params.pass_length_shape
    length = play.rng.gamma(shape, length_mean / shape)
    angle = play.rng.vonmises(0.0, kappa)
    return clamp_to_pitch(
        Point(ball.x + length * math.cos(angle), ball.y + length * math.sin(angle)), EDGE_MARGIN
    )


def _between(rng: Generator, bounds: tuple[float, float]) -> float:
    return rng.uniform(*bounds)


def _keeper(formation: Formation) -> int:
    return next(i for i, slot in enumerate(formation.slots) if slot.role is Role.GOALKEEPER)


def _nearest(
    formation: Formation, ball: Point, in_possession: bool, exclude: int | None = None
) -> int:
    """The slot whose spot in the team's shape is closest to the ball, ignoring ``exclude``.

    ``ball`` is in the team's own direction. Uses the shape without jitter, so choosing a
    player never draws from the shape model's random stream.
    """
    positions = team_shape(formation, ball, in_possession)
    candidates = (index for index in range(len(positions)) if index != exclude)
    return min(candidates, key=lambda index: distance(positions[index], ball))
