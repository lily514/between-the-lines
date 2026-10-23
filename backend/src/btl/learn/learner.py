"""The learner's record: who they are, how far they've got, and every answer they've given.

The answers are the source of truth. Mastery is never stored here; it is always what the
knowledge model gives when it replays the answers, so a new model or new parameters apply to
everything a viewer has done.
"""

from collections.abc import Collection
from dataclasses import dataclass, field, replace
from typing import TypeVar

from btl.learn.concept_map import ConceptKey
from btl.learn.knowledge import Delivery, KnowledgeModel, Observation, replay
from btl.learn.questions import Asks, Form
from btl.schema.ids import TeamId

LEARNER_VERSION = 3
MATCHES_PER_SESSION = 3

StateT = TypeVar("StateT")


@dataclass(frozen=True, slots=True)
class Attempt:
    """One answered question, with enough to replay it and to show it again.

    ``answered_at`` is an ISO 8601 timestamp supplied by the caller; nothing here reads the
    clock. ``asked_in`` is the period the question was asked in, which for a review can be later
    than the moment; None in records written before it was kept.
    """

    match_number: int
    action_id: int
    concept: ConceptKey
    form: Form
    asks: Asks
    level: int
    delivery: Delivery
    difficulty: float
    options: int
    chosen: str
    correct: bool
    pack_id: str
    answered_at: str
    asked_in: int | None = None

    def observation(self) -> Observation:
        """The answer as a knowledge model sees it."""
        return Observation(
            concepts=(self.concept,),
            correct=self.correct,
            options=self.options,
            difficulty=self.difficulty,
            level=self.level,
            delivery=self.delivery,
        )


@dataclass(frozen=True, slots=True)
class LearnerState:
    """One viewer's record. ``match_number`` counts from 1; it is the match being watched.

    ``seed`` fixes the viewer's three matches, so a session can always be rebuilt. ``club`` is
    the team the viewer supports; their matches are its fixtures. Without one, the seed alone
    chooses the fixtures.
    """

    viewer_id: str
    seed: int
    match_number: int = 1
    attempts: tuple[Attempt, ...] = field(default=())
    club: TeamId | None = None
    version: int = LEARNER_VERSION

    @property
    def finished(self) -> bool:
        """Whether every match in the session has been watched."""
        return self.match_number > MATCHES_PER_SESSION

    @property
    def can_choose_club(self) -> bool:
        """Whether the club can still change: nothing answered and no match finished yet."""
        return not self.attempts and self.match_number == 1

    def answered(self, attempt: Attempt) -> "LearnerState":
        """The record with one more answer."""
        return replace(self, attempts=(*self.attempts, attempt))

    def next_match(self) -> "LearnerState":
        """The record after finishing the current match."""
        return replace(self, match_number=self.match_number + 1)

    def asked_in(self, match_number: int) -> frozenset[tuple[ConceptKey, int]]:
        """The moments already asked about in a match, as (concept, action id)."""
        return frozenset(
            (a.concept, a.action_id) for a in self.attempts if a.match_number == match_number
        )

    def model_state(
        self, model: KnowledgeModel[StateT], concepts: Collection[ConceptKey]
    ) -> StateT:
        """The knowledge model's state after every answer, by replaying them."""
        return replay(model, concepts, (a.observation() for a in self.attempts))
