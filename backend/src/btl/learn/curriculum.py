"""The whole curriculum as the viewer's map: every concept, and where the viewer stands on it.

The map shows all of the concept map's concepts by strand and tier, with their prerequisites.
The concepts the app can ask about carry the viewer's mastery, level word and band; the others
are "coming later" and carry none, since nothing has measured them. An askable concept also
says which askable prerequisites it still waits for: those the viewer hasn't unlocked yet, by
the knowledge model's threshold. Without a viewer, a new viewer's priors stand in.
"""

from dataclasses import dataclass

from btl.learn.bkt import BktState
from btl.learn.concept_map import ConceptKey
from btl.learn.learner import LearnerState
from btl.learn.levels import Band, band_for, level_word
from btl.learn.session import Course


@dataclass(frozen=True, slots=True)
class Strand:
    """A strand of the curriculum: its key, name and what it covers."""

    key: str
    name: str
    description: str


@dataclass(frozen=True, slots=True)
class MapConcept:
    """A concept on the map. ``mastery``, ``level`` and ``band`` are None for one coming later.

    ``waits_for`` names the askable prerequisites the viewer hasn't unlocked yet; empty when
    the concept is open to them, and always empty for one coming later.
    """

    key: ConceptKey
    name: str
    strand: str
    tier: int
    objective: str
    prerequisites: tuple[ConceptKey, ...]
    askable: bool
    mastery: float | None
    level: str | None
    band: Band | None
    waits_for: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Curriculum:
    """The map: strands, tier names, and every concept in the concept map's order."""

    strands: tuple[Strand, ...]
    tiers: tuple[str, ...]
    concepts: tuple[MapConcept, ...]


def strand_name(key: str) -> str:
    """A strand's name from its key, e.g. ``Game flow`` for ``game_flow``."""
    return key.replace("_", " ").capitalize()


def waits_on(course: Course, known: BktState, key: ConceptKey) -> tuple[ConceptKey, ...]:
    """The askable prerequisites of a concept the viewer hasn't unlocked yet, in map order."""
    model = course.model
    in_force = course.concept_map.prerequisites_in_force(key, course.active)
    return tuple(
        concept.key
        for concept in course.concept_map.concepts
        if concept.key in in_force and model.mastery(known, concept.key) < model.thresholds.unlock
    )


def curriculum(course: Course, state: LearnerState | None) -> Curriculum:
    """The viewer's map of the whole curriculum, or the map alone, with no values, for no viewer."""
    concept_map = course.concept_map
    model = course.model
    replayed = None if state is None else state.model_state(model, course.active)
    known = model.initial_state(course.active) if replayed is None else replayed
    concepts: list[MapConcept] = []
    for concept in concept_map.concepts:
        askable = concept.key in course.active
        mastery = None
        if askable and replayed is not None:
            mastery = model.mastery(replayed, concept.key)
        waits_for = ()
        if askable:
            waits_for = tuple(
                concept_map.concept(key).name for key in waits_on(course, known, concept.key)
            )
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
                band=None if mastery is None else band_for(mastery),
                waits_for=waits_for,
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
