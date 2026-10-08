"""Phase of play: whether play is settled, in transition, stopped, or at a break.

The learning loop never asks a question during a transition, so it needs to know the phase at
every moment of a match. This reads it from the events alone, using the shared definition of
possession, so it would work unchanged on real data. It never trusts the simulator's own
``phase`` field.

- **Transition**: from a turnover in open play until the team that won the ball completes
  ``TRANSITION_PASSES`` passes, ``TRANSITION_SECONDS`` pass, or the ball goes dead. Both teams
  are out of shape: one is attacking before the other has recovered.
- **Settled**: every other action in play.
- **Dead ball**: from an action after which play stops to the restart (a set piece, or the
  kickoff after a goal). A window shorter than ``MIN_QUESTION_WINDOW`` is too short to ask
  a question in.
- **Half-time** and **full time**: after each period's last action.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

from btl.schema.event import Event
from btl.schema.ids import ActionId
from btl.schema.match import Match
from btl.schema.possession import (
    RESTARTS,
    SHOTS,
    changes_hands_in_open_play,
    split_possessions,
)
from btl.schema.vocab import ActionType, Result

TRANSITION_PASSES = 4
TRANSITION_SECONDS = 12.0
MIN_QUESTION_WINDOW = 15.0
COMPLETED_PASSES = frozenset({ActionType.PASS, ActionType.CROSS})


class PhaseOfPlay(StrEnum):
    """The phase of play a stretch of the match is in."""

    SETTLED = "settled"
    TRANSITION = "transition"
    DEAD_BALL = "dead ball"
    HALF_TIME = "half-time"
    FULL_TIME = "full time"

    @property
    def in_play(self) -> bool:
        """Whether the ball is in play."""
        return self in (PhaseOfPlay.SETTLED, PhaseOfPlay.TRANSITION)


@dataclass(frozen=True, slots=True)
class Segment:
    """A stretch of one period in a single phase, from ``start`` up to ``end`` seconds.

    In play, ``first`` and ``last`` are the segment's first and last actions. For a dead ball,
    ``first`` is the action after which play stopped and ``last`` the restart. A break has no
    length; both are the period's last action.
    """

    phase: PhaseOfPlay
    period_id: int
    start: float
    end: float
    first: ActionId
    last: ActionId

    @property
    def seconds(self) -> float:
        """How long the segment lasts."""
        return self.end - self.start

    @property
    def long_enough_to_ask(self) -> bool:
        """Whether a question fits: any break, or a dead ball of ``MIN_QUESTION_WINDOW``."""
        if self.phase in (PhaseOfPlay.HALF_TIME, PhaseOfPlay.FULL_TIME):
            return True
        return self.phase is PhaseOfPlay.DEAD_BALL and self.seconds >= MIN_QUESTION_WINDOW


@dataclass(frozen=True, slots=True)
class PhaseTimeline:
    """A whole match divided into phases.

    ``segments`` run in match order and, within each period, cover the time from its first
    action to its last with no gaps or overlaps; each period ends with its break.
    ``action_phases`` holds each action's own phase: settled or transition.
    """

    segments: tuple[Segment, ...]
    action_phases: tuple[PhaseOfPlay, ...]

    def phase_of(self, action_id: ActionId) -> PhaseOfPlay:
        """The phase an action happened in: settled or transition."""
        return self.action_phases[action_id]


def phase_timeline(match: Match) -> PhaseTimeline:
    """Divide a match into phases of play."""
    events = match.events
    action_phases = _action_phases(events)
    segments: list[Segment] = []

    def add(phase: PhaseOfPlay, first: Event, last: Event, start: float, end: float) -> None:
        previous = segments[-1] if segments else None
        if (
            previous is not None
            and phase.in_play
            and previous.phase is phase
            and previous.period_id == first.period_id
            and previous.end == start
        ):
            segments[-1] = Segment(
                phase, first.period_id, previous.start, end, previous.first, last.action_id
            )
        else:
            segments.append(
                Segment(phase, first.period_id, start, end, first.action_id, last.action_id)
            )

    for index, event in enumerate(events):
        following = events[index + 1] if index + 1 < len(events) else None
        later = following if following and following.period_id == event.period_id else None
        stops = later is not None and _restarts_play(event, later)
        # An action's stretch of play runs to the next action, unless play stops after it.
        in_play_until = later.time_seconds if later is not None and not stops else None
        now = event.time_seconds
        add(action_phases[index], event, event, now, in_play_until or now)
        if later is not None and stops:
            add(PhaseOfPlay.DEAD_BALL, event, later, now, later.time_seconds)
        if later is None:
            kind = PhaseOfPlay.FULL_TIME if following is None else PhaseOfPlay.HALF_TIME
            add(kind, event, event, now, now)
    return PhaseTimeline(tuple(segments), action_phases)


def _action_phases(events: Sequence[Event]) -> tuple[PhaseOfPlay, ...]:
    phases = [PhaseOfPlay.SETTLED] * len(events)
    possessions = split_possessions(events)
    for before, possession in zip((None, *possessions), possessions, strict=False):
        won_in_open_play = (
            before is not None
            and before.period_id == possession.period_id
            and changes_hands_in_open_play(events[before.last], events[possession.first])
        )
        if not won_in_open_play:
            continue
        won_at = events[possession.first].time_seconds
        passes = 0
        for action in range(possession.first, possession.last + 1):
            event = events[action]
            if passes >= TRANSITION_PASSES or event.time_seconds - won_at >= TRANSITION_SECONDS:
                break
            phases[action] = PhaseOfPlay.TRANSITION
            if event.action_type in COMPLETED_PASSES and event.result is Result.SUCCESS:
                passes += 1
            if action + 1 < len(events) and _restarts_play(event, events[action + 1]):
                break
    return tuple(phases)


def _restarts_play(event: Event, later: Event) -> bool:
    """Whether play stops after ``event`` and ``later`` restarts it."""
    scored = event.result is Result.OWNGOAL or (
        event.action_type in SHOTS and event.result is Result.SUCCESS
    )
    return later.action_type in RESTARTS or scored
