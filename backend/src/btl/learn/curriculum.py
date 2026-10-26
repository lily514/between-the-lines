"""The whole curriculum as the viewer's map: every concept, and where the viewer stands on it.

The map shows all of the concept map's concepts by strand and tier, with their prerequisites.
The concepts the app can ask about carry the viewer's mastery and level word; the others are
"coming later" and carry neither, since nothing has measured them.
"""

from dataclasses import dataclass

from btl.learn.concept_map import ConceptKey
from btl.learn.learner import LearnerState
from btl.learn.levels import level_word
from btl.learn.session import Course


@dataclass(frozen=True, slots=True)
class Strand:
    """A strand of the curriculum: its key, name and what it covers."""

    key: str
    name: str
    description: str


@dataclass(frozen=True, slots=True)
class MapConcept:
    """A concept on the map. ``mastery`` and ``level`` are None for one coming later."""

    key: ConceptKey
    name: str
    strand: str
    tier: int
    objective: str
    prerequisites: tuple[ConceptKey, ...]
    askable: bool
    mastery: float | None
    level: str | None


@dataclass(frozen=True, slots=True)
class Curriculum:
    """The map: strands, tier names, and every concept in the concept map's order."""

    strands: tuple[Strand, ...]
    tiers: tuple[str, ...]
    concepts: tuple[MapConcept, ...]


def strand_name(key: str) -> str:
    """A strand's name from its key, e.g. ``Game flow`` for ``game_flow``."""
    return key.replace("_", " ").capitalize()


def curriculum(course: Course, state: LearnerState | None) -> Curriculum:
    """The viewer's map of the whole curriculum, or the map alone, with no values, for no viewer."""
    concept_map = course.concept_map
    model = course.model
    replayed = None if state is None else state.model_state(model, course.active)
    concepts: list[MapConcept] = []
    for concept in concept_map.concepts:
        askable = concept.key in course.active
        mastery = None
        if askable and replayed is not None:
            mastery = model.mastery(replayed, concept.key)
        concepts.append(
            MapConcept(
                key=concept.key,
                name=concept.name,
                strand=concept.strand,
                tier=concept.tier,
                objective=concept.objective,
                prerequisites=concept.prerequisites,
                askable=askable,
                mastery=mastery,
                level=None if mastery is None else level_word(mastery, model.thresholds),
            )
        )
    return Curriculum(
        strands=tuple(
            Strand(key, strand_name(key), description)
            for key, description in concept_map.strands.items()
        ),
        tiers=tuple(concept_map.tiers[tier].name for tier in sorted(concept_map.tiers)),
        concepts=tuple(concepts),
    )
