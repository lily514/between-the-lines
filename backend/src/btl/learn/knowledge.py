"""Knowledge models: how sure we are that the viewer understands each concept.

A knowledge model turns the viewer's answers into a mastery estimate from 0 to 1 per concept.
Bayesian Knowledge Tracing (`btl.learn.bkt`) is the one in use. Everything else in the loop
(the selector, questions, feedback, progress bars) only asks a model for ``mastery`` and its
``thresholds``, so another model, such as Performance Factors Analysis, can replace it.

The viewer's answers are the source of truth. A model's state is always what `replay` gives
for the answers so far, so changing the model or its parameters never needs a data migration.
"""

from collections.abc import Collection, Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol, TypeVar

from btl.learn.concept_map import ConceptKey, Thresholds

LEVELS = (1, 2, 3)


class Delivery(StrEnum):
    """When a question was asked: as the play happened, or later, at a stoppage or break."""

    LIVE = "live"
    DEFERRED = "deferred"


@dataclass(frozen=True, slots=True)
class Observation:
    """One answer, with everything a knowledge model might weigh.

    ``concepts`` are the concepts the question gives evidence for; today always one.
    ``options`` is how many answers were offered, ``difficulty`` the moment's difficulty from
    its detector (0 to 1), and ``level`` the question's level (1 to 3). Each model uses what
    it needs and ignores the rest.
    """

    concepts: tuple[ConceptKey, ...]
    correct: bool
    options: int
    difficulty: float
    level: int
    delivery: Delivery

    def __post_init__(self) -> None:
        """Reject an observation no question could produce."""
        if not self.concepts:
            raise ValueError("an observation needs at least one concept")
        if self.options < 2:
            raise ValueError(f"a question needs at least 2 options, got {self.options}")
        if not 0 <= self.difficulty <= 1:
            raise ValueError(f"difficulty runs from 0 to 1, got {self.difficulty}")
        if self.level not in LEVELS:
            raise ValueError(f"level must be one of {LEVELS}, got {self.level}")


@dataclass(frozen=True, slots=True)
class ConceptChange:
    """How one answer moved one concept's mastery.

    ``details`` holds the model's own intermediate numbers, for its explanation; read-only by
    convention.
    """

    concept: ConceptKey
    before: float
    after: float
    details: Mapping[str, float]


@dataclass(frozen=True, slots=True)
class Update:
    """What one answer did: the observation, and each concept's change."""

    observation: Observation
    changes: tuple[ConceptChange, ...]


StateT = TypeVar("StateT")


class KnowledgeModel(Protocol[StateT]):
    """Estimates mastery from answers. Pure: the same answers always give the same state."""

    @property
    def name(self) -> str:
        """The model's name, as in the concept map's ``learner_models``."""
        ...

    @property
    def version(self) -> int:
        """Bumped whenever the same answers would give different numbers."""
        ...

    @property
    def thresholds(self) -> Thresholds:
        """When a concept unlocks those that need it, and when it counts as mastered."""
        ...

    def initial_state(self, concepts: Collection[ConceptKey]) -> StateT:
        """The state before any answer, for these concepts."""
        ...

    def update(self, state: StateT, observation: Observation) -> tuple[StateT, Update]:
        """The state after one more answer, and what changed."""
        ...

    def mastery(self, state: StateT, concept: ConceptKey) -> float:
        """How sure the model is that the viewer understands the concept, from 0 to 1."""
        ...

    def explain(self, update: Update) -> str:
        """One plain sentence per concept saying why its mastery moved, quoting the numbers."""
        ...


def replay(
    model: KnowledgeModel[StateT],
    concepts: Collection[ConceptKey],
    observations: Iterable[Observation],
) -> StateT:
    """The state after every observation, in order, starting from the initial state."""
    state = model.initial_state(concepts)
    for observation in observations:
        state, _ = model.update(state, observation)
    return state
