"""The viewer's level on a concept, in words: what the page shows instead of a level number.

The words follow the selector's levels (`level_for`), so the word a viewer reads is the level
they are asked at: below 40% "Getting there", up to 70% "Solid", then "Sharp". Past the
mastery threshold the concept is "Mastered".
"""

from btl.learn.concept_map import Thresholds
from btl.learn.selector import level_for

LEVEL_WORDS = {1: "Getting there", 2: "Solid", 3: "Sharp"}
MASTERED = "Mastered"


def level_word(mastery: float, thresholds: Thresholds) -> str:
    """The word for a viewer's mastery of a concept."""
    if mastery >= thresholds.mastery:
        return MASTERED
    return LEVEL_WORDS[level_for(mastery)]
