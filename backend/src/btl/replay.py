"""Frames for replaying the play around a planted moment, one instant at a time.

A match only records where the players stood at the start of each action. Between two
actions, players move in a straight line from one snapshot to the next, and the ball moves
from the action's start to its end. Frames come in two clips: the lead-up, which ends on the
question picture (the start of the action after the pause), and the answer, which plays on
from there to the end of the answer action.

Functions here take the match already oriented for watching, usually with
`btl.schema.frames.seen_by`, and never flip coordinates themselves.
"""

import bisect
from dataclasses import dataclass

import numpy as np

from btl.schema.ids import ActionId
from btl.schema.match import Match
from btl.schema.moment import PlantedMoment
from btl.schema.snapshot import PlayerPosition

# An action's end is the next action's start, but a ball doesn't take the whole dead-ball
# time before a restart to travel, so its flight is capped at this many seconds.
LONGEST_ACTION = 3.0
DEFAULT_FPS = 10


@dataclass(frozen=True, slots=True)
class ReplayFrame:
    """The pitch at one instant: where the ball and players are, and which action is under way.

    ``time_seconds`` is since the start of the period, as on events.
    """

    time_seconds: float
    action_id: ActionId
    ball: tuple[float, float]
    players: tuple[PlayerPosition, ...]


def question_action(moment: PlantedMoment) -> ActionId:
    """The action whose start is the learner's question picture: the one after the pause."""
    return ActionId(moment.pause_action_id + 1)


def frame_at(match: Match, action_id: ActionId) -> ReplayFrame:
    """The instant an action begins: the players at its snapshot and the ball at its start.

    Raises:
        ValueError: If the match has no player positions.
    """
    return _frame(match, match.events[action_id].time_seconds, action_id, action_id)


def lead_up_frames(
    match: Match, moment: PlantedMoment, *, seconds: float = 15.0, fps: int = DEFAULT_FPS
) -> tuple[ReplayFrame, ...]:
    """The play before a moment, ending exactly on its question picture.

    The clip starts at the last action at least ``seconds`` before the question, or at the
    period's first action if there is none.

    Raises:
        ValueError: If the match has no player positions.
    """
    last = question_action(moment)
    period = match.events[last].period_id
    end = match.events[last].time_seconds
    first = last
    while (
        first > 0
        and match.events[first - 1].period_id == period
        and end - match.events[first].time_seconds < seconds
    ):
        first = ActionId(first - 1)
    return _clip(match, first, last, end, fps)


def answer_frames(
    match: Match, moment: PlantedMoment, *, fps: int = DEFAULT_FPS
) -> tuple[ReplayFrame, ...]:
    """The play from the question picture to the end of the answer action.

    The question picture itself is left out, since the lead-up ends on it.

    Raises:
        ValueError: If the match has no player positions.
    """
    first, last = question_action(moment), moment.answer_action_id
    end = match.events[last].time_seconds + _flight(match, last)
    return _clip(match, first, last, end, fps)[1:]


def _clip(
    match: Match, first: ActionId, last: ActionId, end: float, fps: int
) -> tuple[ReplayFrame, ...]:
    start = match.events[first].time_seconds
    steps = int((end - start) * fps)
    times = [start + step / fps for step in range(steps) if start + step / fps < end]
    return tuple(_frame(match, time, first, last) for time in [*times, end])


def _flight(match: Match, action_id: ActionId) -> float:
    if action_id + 1 >= len(match.events):
        return LONGEST_ACTION
    gap = match.events[action_id + 1].time_seconds - match.events[action_id].time_seconds
    return min(max(gap, 0.0), LONGEST_ACTION)


def _frame(match: Match, time: float, first: ActionId, last: ActionId) -> ReplayFrame:
    if match.positions is None:
        raise ValueError("the match has no player positions to replay")
    starts = [match.events[action].time_seconds for action in range(first, last + 1)]
    current = ActionId(first + max(bisect.bisect_right(starts, time) - 1, 0))
    event = match.events[current]
    since = time - event.time_seconds

    flight = _flight(match, current)
    along = min(since / flight, 1.0) if flight > 0 else 1.0
    ball = (
        event.start_x + along * (event.end_x - event.start_x),
        event.start_y + along * (event.end_y - event.start_y),
    )

    xy = match.positions.xy[current]
    if current + 1 < len(match.events):
        gap = match.events[current + 1].time_seconds - event.time_seconds
        if gap > 0:
            after = match.positions.xy[current + 1]
            share = min(since / gap, 1.0)
            # Where the next position is unknown, the player stays put.
            xy = np.where(np.isnan(after), xy, xy + share * (after - xy))
    players = tuple(
        PlayerPosition(
            player_id=slot.player_id,
            team_id=slot.team_id,
            x=float(xy[index, 0]),
            y=float(xy[index, 1]),
            is_actor=slot.player_id == event.player_id,
            is_goalkeeper=slot.is_goalkeeper,
        )
        for index, slot in enumerate(match.positions.slots)
        if not np.isnan(xy[index]).any()
    )
    return ReplayFrame(time_seconds=time, action_id=current, ball=ball, players=players)
