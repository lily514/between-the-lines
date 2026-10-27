"""Where the players and the ball were between two questions, for the page to move the pitch.

A match records where every tracked player stood at the start of each action, so the track is
one keyframe per action and the page blends between them as the match clock runs. The ball has
two points an action: at its start, and at its end once its flight is over, with the flight
capped as `btl replay` caps it. Like the play-by-play (`btl.learn.play_by_play`), the track stops
at the moment the question is about: its last keyframe is that action's start, which is the
question's picture, so it shows nothing of how the play turned out.

Functions here take the match already oriented for watching, usually with
`btl.schema.frames.seen_by`, and never flip coordinates themselves.
"""

import bisect
from dataclasses import dataclass

import numpy as np

from btl.replay import flight_seconds
from btl.schema.ids import ActionId, PlayerId
from btl.schema.match import Match
from btl.schema.snapshot import PlayerSlot


@dataclass(frozen=True, slots=True)
class TrackFrame:
    """Every tracked player at the start of one action, and the player making it.

    ``positions`` has one entry per slot of the track, None where the position is unknown.
    ``time_seconds`` is since the start of the period, as on events.
    """

    action_id: ActionId
    period_id: int
    time_seconds: float
    positions: tuple[tuple[float, float] | None, ...]
    on_ball: PlayerId


@dataclass(frozen=True, slots=True)
class BallPoint:
    """Where the ball was at one instant."""

    period_id: int
    time_seconds: float
    x: float
    y: float


@dataclass(frozen=True, slots=True)
class Track:
    """The play between two points in the match, as keyframes in match order.

    The page blends between neighbouring keyframes of the same period, never across a period
    change.
    """

    slots: tuple[PlayerSlot, ...]
    frames: tuple[TrackFrame, ...]
    ball: tuple[BallPoint, ...]


def track_between(
    match: Match, after: tuple[int, float] | None, before: tuple[int, float]
) -> Track:
    """The keyframes for the actions strictly between two points, then the one at ``before``.

    Args:
        match: The match, oriented for watching.
        after: Where the viewer left off, as (period, seconds into it); None for kick-off.
        before: The moment the next question is about. Its action's start closes the track,
            without its flight. When ``after`` is at or past it, the track is empty.

    Raises:
        ValueError: If the match has no player positions.
    """
    if match.positions is None:
        raise ValueError("the match has no player positions to track")
    if after is not None and after >= before:
        # The viewer left off after the moment, at the stoppage a saved question waited for.
        return Track(match.positions.slots, (), ())
    starts = [(event.period_id, event.time_seconds) for event in match.events]
    first = 0 if after is None else bisect.bisect_right(starts, after)
    # The moment's own action closes the track; with none at or after it, play runs to the end.
    last = min(bisect.bisect_left(starts, before), len(starts) - 1)
    window = match.positions.xy[first : last + 1]
    known = ~np.isnan(window).any(axis=2)
    points = window.tolist()
    frames: list[TrackFrame] = []
    ball: list[BallPoint] = []
    for offset, event in enumerate(match.events[first : last + 1]):
        frames.append(
            TrackFrame(
                action_id=event.action_id,
                period_id=event.period_id,
                time_seconds=event.time_seconds,
                positions=tuple(
                    (point[0], point[1]) if seen else None
                    for point, seen in zip(points[offset], known[offset], strict=True)
                ),
                on_ball=event.player_id,
            )
        )
        ball.append(BallPoint(event.period_id, event.time_seconds, event.start_x, event.start_y))
        flight = flight_seconds(match, event.action_id)
        if starts[event.action_id] < before and flight > 0:
            ball.append(
                BallPoint(event.period_id, event.time_seconds + flight, event.end_x, event.end_y)
            )
    return Track(match.positions.slots, tuple(frames), tuple(ball))
