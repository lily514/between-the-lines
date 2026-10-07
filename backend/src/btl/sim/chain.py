"""One possession: the actions a team makes from getting the ball until the other team has it.

Everything here is in the attacking direction of the team in possession (towards x = 105).
Each step picks an action from the ball's zone, an end point from a random kernel aimed at
goal, and success from a base rate adjusted by distance and the two teams' strengths. The
chain ends when the ball goes to the other team, and says how that team's possession starts,
in that team's own direction, so the engine can hand straight over.
"""

import math
from dataclasses import dataclass, replace
from enum import Enum

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
    on_pitch,
    where_it_leaves,
    zone_of,
)
from btl.sim.shape import Formation, team_shape

CENTRE_SPOT = Point(PITCH_LENGTH / 2, PITCH_WIDTH / 2)
KEEPER_ACTIONS = frozenset({ActionType.KEEPER_SAVE, ActionType.KEEPER_CLAIM})
CROSSES = frozenset({ActionType.CROSS, ActionType.CORNER_CROSSED})
# A successful pass or dribble stops this far inside the lines.
EDGE_MARGIN = 1.0
SIX_YARD_DEPTH = 5.5
SIX_YARD_HALF_WIDTH = 9.16


class Restart(Enum):
    """The ways play starts again after it stops."""

    KICKOFF = "kickoff"
    THROW_IN = "throw_in"
    GOAL_KICK = "goal_kick"
    CORNER = "corner"


@dataclass(frozen=True, slots=True)
class Side:
    """What a chain needs to know about one team."""

    formation: Formation
    strength: float


@dataclass(frozen=True, slots=True)
class Start:
    """How a possession begins, in the team's own attacking direction.

    Exactly one of ``won_with`` (the possession opens with that ball-winning action) and
    ``restart`` (its first action is a set piece) is set. ``delay`` is the dead-ball time
    before it.
    """

    ball: Point
    slot: int
    won_with: ActionType | None = None
    restart: Restart | None = None
    delay: float = 0.0

    def __post_init__(self) -> None:
        """Check the possession starts in exactly one way."""
        if (self.won_with is None) == (self.restart is None):
            raise ValueError("a possession starts with either a ball-winning action or a restart")


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
    """One action, then what happens next.

    Play goes on with ``receiver`` on the ball, unless ``corner`` gives the same team a corner
    or ``handover`` says how the other team's possession starts.
    """

    step: Step
    receiver: int
    corner: Start | None = None
    handover: Start | None = None


def kickoff(side: Side, delay: float = 0.0) -> Start:
    """A kickoff from the centre spot, taken by the outfield player nearest it."""
    return Start(
        CENTRE_SPOT, _taker(side.formation, CENTRE_SPOT), restart=Restart.KICKOFF, delay=delay
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
    ball, slot, restart = start.ball, start.slot, start.restart
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
    in_transition = start.won_with is not None
    after_cross = False

    while True:
        if restart is not None:
            in_transition = False
            outcome = _restart(restart, slot, ball, play)
        else:
            elapsed = sum(step.duration for step in steps)
            transition = in_transition and elapsed < params.transition_seconds
            outcome = _open_play(slot, ball, after_cross, play, transition)
        steps.append(outcome.step)
        if outcome.handover is not None:
            return Chain(tuple(steps), outcome.handover)
        if outcome.corner is not None:
            ball, slot, restart = outcome.corner.ball, outcome.corner.slot, Restart.CORNER
            after_cross = False
        else:
            ball, slot, restart = outcome.step.end, outcome.receiver, None
            after_cross = outcome.step.action_type in CROSSES


def _open_play(
    slot: int, ball: Point, after_cross: bool, play: _Play, transition: bool
) -> _Outcome:
    rng, params = play.rng, play.params
    phase = Phase.TRANSITION if transition else Phase.OPEN_PLAY
    is_keeper = play.attack.formation.slots[slot].role is Role.GOALKEEPER
    action = _choose_action(ball, is_keeper, after_cross, rng, params)
    if action is ActionType.SHOT:
        return _shoot(slot, ball, after_cross, phase, play)
    if action is ActionType.CROSS:
        return _cross(slot, ball, phase, play)
    if action is ActionType.DRIBBLE:
        return _dribble(slot, ball, phase, play)
    if is_keeper:
        target = _kick(ball, params.keeper_pass_length_mean, params.keeper_pass_kappa, play)
        return _pass(slot, ball, target, phase, play)
    third = zone_of(ball).third
    length_mean, kappa = params.pass_length_mean.of(third), params.pass_kappa.of(third)
    return _pass(slot, ball, _kick(ball, length_mean, kappa, play), phase, play)


def _restart(restart: Restart, slot: int, ball: Point, play: _Play) -> _Outcome:
    rng, params = play.rng, play.params
    phase = Phase.SET_PIECE
    if restart is Restart.KICKOFF:
        back = Point(ball.x - rng.uniform(8, 14), ball.y + rng.uniform(-8, 8))
        return _pass(slot, ball, back, phase, play)
    if restart is Restart.THROW_IN:
        infield = params.throw_in_aim if ball.y < PITCH_WIDTH / 2 else -params.throw_in_aim
        target = _kick(
            ball,
            params.throw_in_length_mean,
            params.throw_in_kappa,
            play,
            infield,
            params.throw_in_longest,
        )
        return _pass(slot, ball, target, phase, play, ActionType.THROW_IN, BodyPart.OTHER)
    if restart is Restart.GOAL_KICK:
        target = _kick(ball, params.keeper_pass_length_mean, params.keeper_pass_kappa, play)
        return _pass(slot, ball, target, phase, play, ActionType.GOALKICK)
    if rng.random() < params.corner_short_share:
        infield = 1.0 if ball.y < PITCH_WIDTH / 2 else -1.0
        target = Point(ball.x - rng.uniform(4, 15), ball.y + infield * rng.uniform(3, 12))
        return _pass(slot, ball, target, phase, play, ActionType.CORNER_SHORT)
    return _cross(slot, ball, phase, play, ActionType.CORNER_CROSSED, params.corner_success)


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


def _pass(
    slot: int,
    ball: Point,
    target: Point,
    phase: Phase,
    play: _Play,
    action: ActionType = ActionType.PASS,
    bodypart: BodyPart = BodyPart.FOOT,
) -> _Outcome:
    """Any kind of pass along the ground or in the air to a teammate.

    ``target`` may be off the pitch: a successful pass stops short of the lines, and a failed
    one may run on out of play.
    """
    end = clamp_to_pitch(target, EDGE_MARGIN)
    length = distance(ball, end)
    params = play.params
    success = params.pass_success.of(zone_of(end).third) * math.exp(
        -max(0.0, length - params.long_pass_from) / params.long_pass_falloff
    )
    if not _succeeds(success, play):
        run_on = _beyond(ball, target, _between(play.rng, params.run_on))
        if not on_pitch(run_on):
            return _out_of_play(slot, action, bodypart, ball, run_on, phase, play)
        return _lose(slot, action, bodypart, ball, end, params.pass_speed, phase, play)
    duration = length / params.pass_speed + _between(play.rng, params.control_time)
    return _Outcome(
        Step(slot, action, Result.SUCCESS, bodypart, ball, end, duration, phase),
        _nearest(play.attack.formation, end, in_possession=True, exclude=slot),
    )


def _dribble(slot: int, ball: Point, phase: Phase, play: _Play) -> _Outcome:
    params = play.params
    end = clamp_to_pitch(
        _kick(ball, params.dribble_length_mean, params.dribble_kappa, play), EDGE_MARGIN
    )
    if not _succeeds(params.dribble_success, play):
        return _lose(
            slot, ActionType.DRIBBLE, BodyPart.FOOT, ball, end, params.dribble_speed, phase, play
        )
    duration = distance(ball, end) / params.dribble_speed + _between(play.rng, params.reaction_time)
    return _Outcome(
        Step(slot, ActionType.DRIBBLE, Result.SUCCESS, BodyPart.FOOT, ball, end, duration, phase),
        slot,
    )


def _lose(
    slot: int,
    action: ActionType,
    bodypart: BodyPart,
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
        Step(slot, action, Result.FAIL, bodypart, ball, lost_at, duration, phase),
        slot,
        handover=Start(mirror(lost_at), winner, won_with),
    )


def _out_of_play(
    slot: int,
    action: ActionType,
    bodypart: BodyPart,
    ball: Point,
    beyond: Point,
    phase: Phase,
    play: _Play,
) -> _Outcome:
    """A pass that goes out, and the other team's restart.

    Over the touchline it's their throw-in where it went out; over the goal line being attacked,
    their goal kick; over the passer's own goal line, their corner.
    """
    params = play.params
    out = where_it_leaves(ball, beyond)
    if out.x == PITCH_LENGTH:
        handover = _goal_kick(play.defence, play)
    elif out.x == 0:
        handover = _corner(play.defence, mirror(out).y, params.corner_delay)
    else:
        throw_in = mirror(out)
        handover = Start(
            throw_in,
            _taker(play.defence.formation, throw_in),
            restart=Restart.THROW_IN,
            delay=params.throw_in_delay,
        )
    flight = distance(ball, out) / params.pass_speed
    return _Outcome(
        Step(slot, action, Result.FAIL, bodypart, ball, out, flight, phase),
        slot,
        handover=handover,
    )


def _cross(
    slot: int,
    ball: Point,
    phase: Phase,
    play: _Play,
    action: ActionType = ActionType.CROSS,
    success: float | None = None,
) -> _Outcome:
    """A cross into the box, from open play or a corner."""
    rng, params = play.rng, play.params
    end = clamp_to_pitch(Point(rng.uniform(88, 100), rng.normal(PITCH_WIDTH / 2, 6)), EDGE_MARGIN)
    flight = distance(ball, end) / params.pass_speed
    if _succeeds(params.cross_success if success is None else success, play):
        duration = flight + _between(rng, params.reaction_time)
        return _Outcome(
            Step(slot, action, Result.SUCCESS, BodyPart.FOOT, ball, end, duration, phase),
            _nearest(play.attack.formation, end, in_possession=True, exclude=slot),
        )
    failed = Step(slot, action, Result.FAIL, BodyPart.FOOT, ball, end, flight, phase)
    if rng.random() < params.cross_out_for_corner:
        corner = _corner(play.attack, ball.y, params.corner_delay)
        return _Outcome(_wait(failed, corner.delay), slot, corner=corner)
    if rng.random() < params.keeper_claim_share:
        handover = Start(mirror(end), _keeper(play.defence.formation), ActionType.KEEPER_CLAIM)
    else:
        winner = _nearest(play.defence.formation, mirror(end), in_possession=False)
        handover = Start(mirror(end), winner, ActionType.INTERCEPTION)
    return _Outcome(failed, slot, handover=handover)


def _shoot(slot: int, ball: Point, header: bool, phase: Phase, play: _Play) -> _Outcome:
    """A shot: a goal, a save, a miss that goes out for a goal kick, or a deflection for a corner.

    Only the corner leaves the ball with the shooting team.
    """
    rng, params = play.rng, play.params
    bodypart = BodyPart.HEAD if header else BodyPart.FOOT
    logit = (
        params.goal_intercept
        + params.goal_per_radian * goal_angle(ball)
        + params.goal_per_metre * distance_to_goal(ball)
    )
    on_target = Point(PITCH_LENGTH, PITCH_WIDTH / 2 + rng.uniform(-1, 1) * (GOAL_WIDTH / 2 - 0.3))

    def shot(result: Result, end: Point) -> Step:
        return Step(slot, ActionType.SHOT, result, bodypart, ball, end, params.shot_flight, phase)

    if _succeeds(1 / (1 + math.exp(-logit)), play):
        handover = kickoff(play.defence, delay=params.goal_restart_delay)
        return _Outcome(shot(Result.SUCCESS, on_target), slot, handover=handover)
    if rng.random() < params.save_share:
        save_at = Point(PITCH_LENGTH - 1, on_target.y)
        handover = Start(mirror(save_at), _keeper(play.defence.formation), ActionType.KEEPER_SAVE)
        return _Outcome(shot(Result.FAIL, on_target), slot, handover=handover)
    wide = rng.choice((-1.0, 1.0)) * rng.uniform(GOAL_WIDTH / 2 + 0.5, 12)
    missed = shot(Result.FAIL, Point(PITCH_LENGTH, PITCH_WIDTH / 2 + wide))
    if rng.random() < params.miss_out_for_corner:
        corner = _corner(play.attack, missed.end.y, params.corner_delay)
        return _Outcome(_wait(missed, corner.delay), slot, corner=corner)
    return _Outcome(missed, slot, handover=_goal_kick(play.defence, play))


def _goal_kick(side: Side, play: _Play) -> Start:
    """A goal kick for ``side``, from a random spot on the front of its six-yard box."""
    across = play.rng.uniform(-1, 1) * SIX_YARD_HALF_WIDTH
    return Start(
        Point(SIX_YARD_DEPTH, PITCH_WIDTH / 2 + across),
        _keeper(side.formation),
        restart=Restart.GOAL_KICK,
        delay=play.params.goal_kick_delay,
    )


def _corner(side: Side, y: float, delay: float) -> Start:
    """A corner for ``side`` from the flag on the same side of the pitch as ``y``."""
    flag = Point(PITCH_LENGTH, 0.0 if y < PITCH_WIDTH / 2 else PITCH_WIDTH)
    return Start(flag, _taker(side.formation, flag), restart=Restart.CORNER, delay=delay)


def _wait(step: Step, delay: float) -> Step:
    """The step, with dead-ball time added before the next action."""
    return replace(step, duration=step.duration + delay)


def _succeeds(probability: float, play: _Play) -> bool:
    """Scale the odds, not the probability, so a stronger side never goes past certainty."""
    odds = probability / (1 - probability) * play.strength_ratio**play.params.strength_exponent
    return play.rng.random() < odds / (1 + odds)


def _kick(
    ball: Point,
    length_mean: float,
    kappa: float,
    play: _Play,
    aim: float = 0.0,
    longest: float = math.inf,
) -> Point:
    """An end point a random length away, scattered around ``aim`` radians from straight at goal.

    Lengths over ``longest`` are drawn again. The point may be off the pitch.
    """
    shape = play.params.pass_length_shape
    length = play.rng.gamma(shape, length_mean / shape)
    while length > longest:
        length = play.rng.gamma(shape, length_mean / shape)
    angle = play.rng.vonmises(aim, kappa)
    return Point(ball.x + length * math.cos(angle), ball.y + length * math.sin(angle))


def _beyond(start: Point, target: Point, extra: float) -> Point:
    """The point ``extra`` metres further on along the line from ``start`` through ``target``."""
    length = distance(start, target)
    if length == 0:
        return target
    scale = (length + extra) / length
    return Point(start.x + scale * (target.x - start.x), start.y + scale * (target.y - start.y))


def _between(rng: Generator, bounds: tuple[float, float]) -> float:
    return rng.uniform(*bounds)


def _keeper(formation: Formation) -> int:
    return next(i for i, slot in enumerate(formation.slots) if slot.role is Role.GOALKEEPER)


def _taker(formation: Formation, ball: Point) -> int:
    """The outfield player nearest a restart, in the team's own direction."""
    return _nearest(formation, ball, in_possession=True, exclude=_keeper(formation))


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
