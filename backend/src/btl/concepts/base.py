"""What every concept detector shares: the tag it produces, the match it reads, its interface."""

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from btl.schema.event import Event
from btl.schema.frames import to_left_to_right
from btl.schema.ids import ActionId, GameId
from btl.schema.match import Match
from btl.schema.possession import Possession, split_possessions
from btl.schema.snapshot import Snapshot


class ConceptId(StrEnum):
    """The football concepts the detectors know. Each has exactly one detector."""

    SWITCH_OF_PLAY = "switch_of_play"
    LINE_BREAKING_PASS = "line_breaking_pass"
    COUNTER_PRESS = "counter_press"

    @property
    def label(self) -> str:
        """The concept's name for display, e.g. "switch of play"."""
        return self.value.replace("_", " ")


@dataclass(frozen=True, slots=True)
class ConceptTag:
    """One occurrence of a concept in a match.

    ``action_id`` is the key action, and ``span`` the first and last actions involved.
    ``difficulty`` runs from 0 (easy to spot) to 1, where a detector defines it. ``evidence``
    holds the measurements behind the tag, e.g. ``{"across (m)": 41.2}``, and is read-only by
    convention.
    """

    concept: ConceptId
    game_id: GameId
    action_id: ActionId
    span: tuple[ActionId, ActionId]
    difficulty: float | None
    evidence: Mapping[str, float]


@dataclass(frozen=True, slots=True)
class MatchContext:
    """A match as detectors see it: every action, and its snapshot, attacking left to right.

    Possessions come from `split_possessions`, never from the simulator's own ``possession_id``.
    ``threat`` holds the Expected Threat each event added, when a model is available.
    """

    match: Match
    possessions: tuple[Possession, ...]
    threat: tuple[float | None, ...] | None = None

    @property
    def events(self) -> tuple[Event, ...]:
        """The match's events, each seen as if its team attacks towards x = 105."""
        return self.match.events

    @property
    def has_snapshots(self) -> bool:
        """Whether any player positions are known."""
        return self.match.positions is not None

    def snapshot(self, action_id: ActionId) -> Snapshot | None:
        """Player positions at the start of an action, in that action's team's direction."""
        return self.match.snapshot(action_id)


def match_context(match: Match, threat: tuple[float | None, ...] | None = None) -> MatchContext:
    """Prepare a stored match for the detectors.

    Args:
        match: The match, in the stored direction.
        threat: The threat each event added, from `btl.value.xt.rate_match`, if available.
    """
    return MatchContext(to_left_to_right(match), split_possessions(match.events), threat)


class Detector(Protocol):
    """Finds every occurrence of one concept in a match."""

    @property
    def concept(self) -> ConceptId:
        """The concept this detector finds."""
        ...

    @property
    def needs_snapshots(self) -> bool:
        """Whether it needs player positions; without them it is skipped."""
        ...

    def detect(self, ctx: MatchContext) -> tuple[ConceptTag, ...]:
        """Every occurrence of the concept, in event order."""
        ...
