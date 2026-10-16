"""One possession: the actions a team makes from getting the ball until the other team has it.

Everything here is in the attacking direction of the team in possession (towards x = 105).
Each step picks an action from the ball's zone, an end point from a random kernel aimed at
goal, and success from a base rate adjusted by distance and the two teams' strengths. The
chain ends when the ball goes to the other team, and says how that team's possession starts,
in that team's own direction, so the engine can hand straight over.
"""

import math
from collections.abc import Sequence
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
    reflect_into_pitch,
    where_it_leaves,
    zone_of,
)
from btl.sim.shape import Formation, team_shape

CENTRE_SPOT = Point(PITCH_LENGTH / 2, PITCH_WIDTH / 2)
KEEPER_ACTIONS = frozenset(
    {ActionType.KEEPER_SAVE, ActionType.KEEPER_CLAIM, ActionType.KEEPER_PICK_UP}
)
CROSSES = frozenset({ActionType.CROSS, ActionType.CORNER_CROSSED})
# Passes and dribbles aimed off the pitch come back in at least this far inside the lines.
EDGE_MARGIN = 1.0
SIX_YARD_DEPTH = 5.5
# How far in front of the goal line a keeper picks up a ball running through.
KEEPER_PICK_UP_DEPTH = 2.0
SIX_YARD_HALF_WIDTH = 9.16
PENALTY_SPOT = Point(PITCH_LENGTH - 11.0, PITCH_WIDTH / 2)


class Restart(Enum):
    """The ways play starts again after it stops."""

    KICKOFF = "kickoff"
    THROW_IN = "throw_in"
    GOAL_KICK = "goal_kick"
    CORNER = "corner"
    FREE_KICK_SHORT = "free_kick_short"
    FREE_KICK_LONG = "free_kick_long"
    FREE_KICK_SHOT = "free_kick_shot"
    PENALTY = "penalty"


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

    ``duration`` is the time until the next action starts. ``by_defence`` marks an action by the
    team without the ball, such as a foul: ``slot`` is then in the defending team's formation,
    while positions stay in the attacking team's direction like every other step.
    ``receiver`` is the teammate's slot a completed pass reaches, or the one a pass flagged
    offside was meant for.
    """

    slot: int
    action_type: ActionType
    result: Result
    bodypart: BodyPart
    start: Point
    end: Point
    duration: float
    phase: Phase
    by_defence: bool = False
    receiver: int | None = None


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

    Play goes on with ``receiver`` on the ball, unless ``set_piece`` gives the same team a
    corner or a free kick, or ``handover`` says how the other team's possession starts.
    """

    step: Step
    receiver: int
    set_piece: Start | None = None
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
    if start.won_with is not None:
        bodypart = BodyPart.OTHER if start.won_with in KEEPER_ACTIONS else BodyPart.FOOT
        duration = _between(rng, params.reaction_time)
        steps.append(
            Step(
                start.slot,
                start.won_with,
                Result.SUCCESS,
                bodypart,
                start.ball,
                start.ball,
                duration,
                Phase.TRANSITION,
            )
        )
    won_the_ball = start.won_with is not None
    return _play_from(steps, start.ball, start.slot, start.restart, won_the_ball, play)


def play_on(
    attack: Side,
    defence: Side,
    opening: Sequence[Step],
    ball: Point,
    slot: int,
    in_transition: bool,
    rng: Generator,
    params: SimParams,
) -> Chain:
    """Carry on a possession whose first actions were written elsewhere.

    Args:
        attack: The team in possession.
        defence: The other team.
        opening: The possession's actions so far.
        ball: Where the ball is now.
        slot: Who has it now.
        in_transition: Whether the possession began by winning the ball in open play.
        rng: The engine's random stream.
        params: The simulator's knobs.

    Returns:
        The whole possession, ``opening`` first, and how the other team's possession starts.
    """
    play = _Play(attack, defence, attack.strength / defence.strength, rng, params)
    return _play_from(list(opening), ball, slot, None, in_transition, play)


def _play_from(
    steps: list[Step],
    ball: Point,
    slot: int,
    restart: Restart | None,
    in_transition: bool,
    play: _Play,
) -> Chain:
    after_cross = False
    while True:
        if restart is not None:
            in_transition = False
            outcome = _restart(restart, slot, ball, play)
        else:
            elapsed = sum(step.duration for step in steps)
            transition = in_transition and elapsed < play.params.transition_seconds
            # After advantage the fouled team plays on; it isn't fouled again on the spot.
            can_foul = not (steps and steps[-1].action_type is ActionType.FOUL)
            outcome = _open_play(slot, ball, after_cross, play, transition, can_foul)
        steps.append(outcome.step)
        if outcome.handover is not None:
            return Chain(tuple(steps), outcome.handover)
        if outcome.set_piece is not None:
            set_piece = outcome.set_piece
            ball, slot, restart = set_piece.ball, set_piece.slot, set_piece.restart
            after_cross = False
        else:
            ball, slot, restart = outcome.step.end, outcome.receiver, None
            after_cross = outcome.step.action_type in CROSSES


def _open_play(
    slot: int, ball: Point, after_cross: bool, play: _Play, transition: bool, can_foul: bool
) -> _Outcome:
    rng, params = play.rng, play.params
    phase = Phase.TRANSITION if transition else Phase.OPEN_PLAY
    is_keeper = play.attack.formation.slots[slot].role is Role.GOALKEEPER
    foul_share = (
        params.foul_share_in_box
        if in_penalty_area(ball)
        else params.foul_share.of(zone_of(ball).third)
    )
    if can_foul and not is_keeper and rng.random() < foul_share:
        return _fouled(slot, ball, phase, play)
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
    if restart is Restart.FREE_KICK_SHORT:
        target = _kick(ball, params.free_kick_short_length_mean, params.pass_kappa.middle, play)
        return _pass(slot, ball, target, phase, play, ActionType.FREEKICK_SHORT)
    if restart is Restart.FREE_KICK_LONG:
        if zone_of(ball).third is Third.ATTACKING:
            return _cross(
                slot, ball, phase, play, ActionType.FREEKICK_CROSSED, params.corner_success
            )
        target = _kick(ball, params.free_kick_long_length_mean, params.keeper_pass_kappa, play)
        return _pass(slot, ball, target, phase, play, ActionType.FREEKICK_CROSSED)
    if restart is Restart.FREE_KICK_SHOT:
        return _shoot(slot, ball, False, phase, play, ActionType.SHOT_FREEKICK)
    if restart is Restart.PENALTY:
        return _penalty(slot, phase, play)
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

    A ``target`` off the pitch is reflected back in: nobody aims a pass out of play. A failed
    pass may still run on past its target and go out.
    """
    end = reflect_into_pitch(target, EDGE_MARGIN)
    length = distance(ball, end)
    params = play.params
    if _flagged_offside(action, ball, end, phase, play):
        return _offside(slot, action, bodypart, ball, end, phase, play)
    success = params.pass_success.of(zone_of(end).third) * math.exp(
        -max(0.0, length - params.long_pass_from) / params.long_pass_falloff
    )
    if not _succeeds(success, play):
        run_on = _beyond(ball, end, _between(play.rng, params.run_on))
        if not on_pitch(run_on):
            return _out_of_play(slot, action, bodypart, ball, run_on, phase, play)
        return _lose(slot, action, bodypart, ball, end, params.pass_speed, phase, play)
    duration = length / params.pass_speed + _between(play.rng, params.control_time)
    receiver = _nearest(play.attack.formation, end, in_possession=True, exclude=slot)
    return _Outcome(
        Step(slot, action, Result.SUCCESS, bodypart, ball, end, duration, phase, receiver=receiver),
        receiver,
    )


def _flagged_offside(
    action: ActionType, ball: Point, end: Point, phase: Phase, play: _Play
) -> bool:
    """Whether the referee flags a pass offside.

    Only a pass in open play, going clearly forward into the attacking third, can be. The
    simulator's events never depend on where players stand, so the flag is a chance, not a
    check of the receiver against the last defender.
    """
    params = play.params
    forward_into_attack = (
        action is ActionType.PASS
        and phase is not Phase.SET_PIECE
        and zone_of(end).third is Third.ATTACKING
        and end.x - ball.x >= params.offside_forward
    )
    return forward_into_attack and play.rng.random() < params.offside_share


def _offside(
    slot: int,
    action: ActionType,
    bodypart: BodyPart,
    ball: Point,
    end: Point,
    phase: Phase,
    play: _Play,
) -> _Outcome:
    """An offside pass: the other team takes a free kick where it was headed."""
    flight = distance(ball, end) / play.params.pass_speed
    kind, spot, delay = _free_kick(mirror(end), play)
    taker = _taker(play.defence.formation, spot)
    meant_for = _nearest(play.attack.formation, end, in_possession=True, exclude=slot)
    return _Outcome(
        Step(slot, action, Result.OFFSIDE, bodypart, ball, end, flight, phase, receiver=meant_for),
        slot,
        handover=Start(spot, taker, restart=kind, delay=delay),
    )


def _dribble(slot: int, ball: Point, phase: Phase, play: _Play) -> _Outcome:
    params = play.params
    end = reflect_into_pitch(
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
    """A pass or dribble that the nearest opponent gets to, somewhere in its second half.

    Sometimes the opponent only blocks it, out of play: see `_blocked_out`.
    """
    fraction = play.rng.uniform(0.4, 1.0)
    lost_at = Point(ball.x + fraction * (end.x - ball.x), ball.y + fraction * (end.y - ball.y))
    duration = distance(ball, lost_at) / speed + _between(play.rng, play.params.reaction_time)
    if play.rng.random() < play.params.deflected_out_share:
        failed = Step(slot, action, Result.FAIL, bodypart, ball, lost_at, duration, phase)
        return _blocked_out(failed, lost_at, play)
    winner = _nearest(play.defence.formation, mirror(lost_at), in_possession=False)
    won_with = ActionType.TACKLE if action is ActionType.DRIBBLE else ActionType.INTERCEPTION
    return _Outcome(
        Step(slot, action, Result.FAIL, bodypart, ball, lost_at, duration, phase),
        slot,
        handover=Start(mirror(lost_at), winner, won_with),
    )


def _blocked_out(failed: Step, at: Point, play: _Play) -> _Outcome:
    """An opponent blocks the ball out over the nearest line, so the team that had it restarts.

    The block isn't an event of its own, as in real event data. Over a touchline it's a
    throw-in level with the block; over the opponent's goal line, a corner; over the team's
    own goal line, a goal kick.
    """
    params = play.params
    lines = {
        "right touchline": at.y,
        "left touchline": PITCH_WIDTH - at.y,
        "their goal line": PITCH_LENGTH - at.x,
        "own goal line": at.x,
    }
    nearest = min(lines, key=lambda line: lines[line])
    if nearest == "their goal line":
        restart = _corner(play.attack, at.y, params.corner_delay)
    elif nearest == "own goal line":
        restart = _goal_kick(play.attack, play)
    else:
        spot = Point(at.x, 0.0 if nearest == "right touchline" else PITCH_WIDTH)
        restart = Start(
            spot,
            _taker(play.attack.formation, spot),
            restart=Restart.THROW_IN,
            delay=params.throw_in_delay,
        )
    return _Outcome(_wait(failed, restart.delay), failed.slot, set_piece=restart)


def _out_of_play(
    slot: int,
    action: ActionType,
    bodypart: BodyPart,
    ball: Point,
    beyond: Point,
    phase: Phase,
    play: _Play,
) -> _Outcome:
    """A pass heading out of play, and how the other team gets the ball.

    Over the touchline it's their throw-in where it went out; over the passer's own goal line,
    their corner. Over the goal line being attacked it's their goal kick, unless it's running
    through in front of goal, where their keeper often picks it up just before the line.
    """
    params = play.params
    out = where_it_leaves(ball, beyond)
    in_front_of_goal = in_penalty_area(Point(PITCH_LENGTH, out.y))
    if (
        out.x == PITCH_LENGTH
        and in_front_of_goal
        and play.rng.random() < params.keeper_pick_up_share
    ):
        picked_up = Point(PITCH_LENGTH - KEEPER_PICK_UP_DEPTH, out.y)
        flight = distance(ball, picked_up) / params.pass_speed
        handover = Start(
            mirror(picked_up), _keeper(play.defence.formation), ActionType.KEEPER_PICK_UP
        )
        return _Outcome(
            Step(slot, action, Result.FAIL, bodypart, ball, picked_up, flight, phase),
            slot,
            handover=handover,
        )
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
        return _Outcome(_wait(failed, corner.delay), slot, set_piece=corner)
    if rng.random() < params.keeper_claim_share:
        handover = Start(mirror(end), _keeper(play.defence.formation), ActionType.KEEPER_CLAIM)
    else:
        winner = _nearest(play.defence.formation, mirror(end), in_possession=False)
        handover = Start(mirror(end), winner, ActionType.INTERCEPTION)
    return _Outcome(failed, slot, handover=handover)


def _shoot(
    slot: int,
    ball: Point,
    header: bool,
    phase: Phase,
    play: _Play,
    action: ActionType = ActionType.SHOT,
) -> _Outcome:
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
        return Step(slot, action, result, bodypart, ball, end, params.shot_flight, phase)

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
        return _Outcome(_wait(missed, corner.delay), slot, set_piece=corner)
    return _Outcome(missed, slot, handover=_goal_kick(play.defence, play))


def _fouled(slot: int, ball: Point, phase: Phase, play: _Play) -> _Outcome:
    """The nearest defender fouls the player on the ball.

    Play usually stops for a free kick to the fouled team where the foul happened: a penalty in
    the box, sometimes a shot at goal within range, otherwise played long or short. After a
    share of fouls the referee lets play go on (advantage). A share are booked: many more when
    the foul stops a promising attack, one of the Laws' reasons for a caution.
    """
    rng, params = play.rng, play.params
    fouler = _nearest(play.defence.formation, mirror(ball), in_possession=False)
    promising = phase is Phase.TRANSITION and zone_of(ball).third is not Third.DEFENSIVE
    booking_share = params.booking_share_promising if promising else params.booking_share_other
    result = Result.YELLOW_CARD if rng.random() < booking_share else Result.FAIL

    def foul(duration: float) -> Step:
        return Step(
            fouler, ActionType.FOUL, result, BodyPart.FOOT, ball, ball, duration, phase, True
        )

    if rng.random() < params.advantage_share:
        return _Outcome(foul(_between(rng, params.reaction_time)), slot)
    kind, spot, delay = _free_kick(ball, play)
    return _Outcome(foul(delay), slot, set_piece=Start(spot, slot, restart=kind, delay=delay))


def _free_kick(ball: Point, play: _Play) -> tuple[Restart, Point, float]:
    """Which kind of free kick a foul at ``ball`` gives, where it is taken, and the wait."""
    rng, params = play.rng, play.params
    if in_penalty_area(ball):
        return Restart.PENALTY, PENALTY_SPOT, params.penalty_delay
    in_range = distance_to_goal(ball) <= params.shot_range and zone_of(ball).lane is Lane.CENTRE
    if in_range and rng.random() < params.free_kick_shot_share:
        return Restart.FREE_KICK_SHOT, ball, params.free_kick_shot_delay
    if rng.random() < params.free_kick_long_share:
        return Restart.FREE_KICK_LONG, ball, _between(rng, params.free_kick_long_delay)
    return Restart.FREE_KICK_SHORT, ball, _between(rng, params.free_kick_short_delay)


def _penalty(slot: int, phase: Phase, play: _Play) -> _Outcome:
    """A penalty: scored, saved by the keeper, or missed for a goal kick."""
    rng, params = play.rng, play.params
    on_target = Point(PITCH_LENGTH, PITCH_WIDTH / 2 + rng.uniform(-1, 1) * (GOAL_WIDTH / 2 - 0.3))

    def kick(result: Result, end: Point) -> Step:
        return Step(
            slot,
            ActionType.SHOT_PENALTY,
            result,
            BodyPart.FOOT,
            PENALTY_SPOT,
            end,
            params.shot_flight,
            phase,
        )

    if rng.random() < params.penalty_conversion:
        handover = kickoff(play.defence, delay=params.goal_restart_delay)
        return _Outcome(kick(Result.SUCCESS, on_target), slot, handover=handover)
    if rng.random() < params.penalty_save_share:
        save_at = Point(PITCH_LENGTH - 1, on_target.y)
        handover = Start(mirror(save_at), _keeper(play.defence.formation), ActionType.KEEPER_SAVE)
        return _Outcome(kick(Result.FAIL, on_target), slot, handover=handover)
    wide = rng.choice((-1.0, 1.0)) * rng.uniform(GOAL_WIDTH / 2 + 0.5, 6)
    missed = kick(Result.FAIL, Point(PITCH_LENGTH, PITCH_WIDTH / 2 + wide))
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
