"""Summary numbers for a match, used to check the simulator against real football."""

from collections import Counter
from dataclasses import dataclass

from btl.schema.match import Match
from btl.schema.vocab import ActionType, Result

SHOTS = frozenset({ActionType.SHOT, ActionType.SHOT_FREEKICK, ActionType.SHOT_PENALTY})
CORNERS = frozenset({ActionType.CORNER_CROSSED, ActionType.CORNER_SHORT})


@dataclass(frozen=True, slots=True)
class MatchStats:
    """Counts for both teams together.

    ``passes`` counts only SPADL ``pass`` actions (kickoffs included); crosses, throw-ins, goal
    kicks and corners are counted separately.
    """

    passes: int
    completed_passes: int
    shots: int
    goals: int
    throw_ins: int
    goal_kicks: int
    corners: int

    @property
    def pass_completion(self) -> float:
        """The share of passes that reached a teammate."""
        return self.completed_passes / self.passes if self.passes else 0.0


def match_stats(match: Match) -> MatchStats:
    """Count a match's passes, shots, goals and restarts."""
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
    )
