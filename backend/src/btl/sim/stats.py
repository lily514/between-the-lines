"""Summary numbers for a match, used to check the simulator against real football."""

import math
from collections import Counter
from dataclasses import dataclass

from btl.schema.match import Match
from btl.schema.vocab import ActionType, Result
from btl.sim.pitch import PITCH_WIDTH

SHOTS = frozenset({ActionType.SHOT, ActionType.SHOT_FREEKICK, ActionType.SHOT_PENALTY})
CORNERS = frozenset({ActionType.CORNER_CROSSED, ActionType.CORNER_SHORT})
FREE_KICKS = frozenset(
    {
        ActionType.FREEKICK_SHORT,
        ActionType.FREEKICK_CROSSED,
        ActionType.SHOT_FREEKICK,
        ActionType.SHOT_PENALTY,
    }
)
# How close to a touchline an action has to start to count as on it.
TOUCHLINE_STRIP = 2.0


@dataclass(frozen=True, slots=True)
class MatchStats:
    """Counts for both teams together.

    ``passes`` counts only SPADL ``pass`` actions (kickoffs included); crosses, throw-ins, goal
    kicks, corners and free kicks are counted separately. ``free_kicks`` includes penalties.
    ``throw_in_lengths`` are in metres, from where each successful throw was taken to the
    teammate who got it. ``on_touchline`` counts actions that start within ``TOUCHLINE_STRIP``
    metres of either touchline, throw-ins included.
    """

    passes: int
    completed_passes: int
    shots: int
    goals: int
    throw_ins: int
    goal_kicks: int
    corners: int
    fouls: int
    yellow_cards: int
    free_kicks: int
    penalties: int
    throw_in_lengths: tuple[float, ...]
    actions: int
    on_touchline: int

    @property
    def pass_completion(self) -> float:
        """The share of passes that reached a teammate."""
        return self.completed_passes / self.passes if self.passes else 0.0


def match_stats(match: Match) -> MatchStats:
    """Count a match's passes, shots, goals and restarts, and measure its throw-ins."""
    counts = Counter(event.action_type for event in match.events)
    succeeded = Counter(
        event.action_type for event in match.events if event.result is Result.SUCCESS
    )
    return MatchStats(
        passes=counts[ActionType.PASS],
        completed_passes=succeeded[ActionType.PASS],
        shots=sum(counts[shot] for shot in SHOTS),
        goals=sum(succeeded[shot] for shot in SHOTS),
        throw_ins=counts[ActionType.THROW_IN],
        goal_kicks=counts[ActionType.GOALKICK],
        corners=sum(counts[corner] for corner in CORNERS),
        fouls=counts[ActionType.FOUL],
        yellow_cards=sum(
            event.action_type is ActionType.FOUL and event.result is Result.YELLOW_CARD
            for event in match.events
        ),
        free_kicks=sum(counts[kick] for kick in FREE_KICKS),
        penalties=counts[ActionType.SHOT_PENALTY],
        throw_in_lengths=tuple(
            math.hypot(event.end_x - event.start_x, event.end_y - event.start_y)
            for event in match.events
            if event.action_type is ActionType.THROW_IN and event.result is Result.SUCCESS
        ),
        actions=len(match.events),
        on_touchline=sum(
            min(event.start_y, PITCH_WIDTH - event.start_y) <= TOUCHLINE_STRIP
            for event in match.events
        ),
    )
