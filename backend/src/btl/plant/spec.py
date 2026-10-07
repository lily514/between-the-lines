"""What to plant: a request for teachable moments, as data, and its command-line form."""

from collections.abc import Sequence
from dataclasses import dataclass

from btl.schema.vocab import ConceptId

LEVELS = (1, 2, 3)


@dataclass(frozen=True, slots=True)
class MomentSpec:
    """One teachable moment to plant: which concept, and how hard, from 1 (easiest) to 3."""

    concept: ConceptId
    difficulty: int

    def __post_init__(self) -> None:
        """Reject a difficulty outside the known levels."""
        if self.difficulty not in LEVELS:
            raise ValueError(f"difficulty must be one of {LEVELS}, got {self.difficulty}")


@dataclass(frozen=True, slots=True)
class PlantRequest:
    """The moments a match should hold. They are played easiest first."""

    moments: tuple[MomentSpec, ...]

    @property
    def in_match_order(self) -> tuple[MomentSpec, ...]:
        """The moments in the order they happen: by difficulty, then as requested."""
        return tuple(sorted(self.moments, key=lambda moment: moment.difficulty))


def parse_plant(texts: Sequence[str]) -> PlantRequest:
    """Read moments written as ``concept:levels``, e.g. ``line_breaking_pass:1,2,3``.

    Raises:
        ValueError: If a text names no known concept or has a level that isn't a known one.
    """
    moments: list[MomentSpec] = []
    for text in texts:
        name, _, levels = text.partition(":")
        try:
            concept = ConceptId(name.strip())
        except ValueError:
            known = ", ".join(concept.value for concept in ConceptId)
            raise ValueError(f"no concept {name!r}; the concepts are {known}") from None
        for level in levels.split(","):
            if not level.strip().isdigit():
                raise ValueError(f"{text!r}: levels are whole numbers, e.g. {concept}:1,2,3")
            moments.append(MomentSpec(concept, int(level)))
    return PlantRequest(tuple(moments))
