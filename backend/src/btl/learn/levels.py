"""The viewer's level on a concept, in words and as a band: what the page shows, never a cut-off.

The words follow the selector's levels (`level_for`), so the word a viewer reads is the level
they are asked at: below 40% "Getting there", up to 70% "Solid", then "Sharp". Past the
mastery threshold the concept is "Mastered". The band is the same level as a key the page can
switch on (`getting_there`, `solid`, `sharp`); Mastered is the Sharp band with the Mastered word.
"""

from enum import StrEnum

from btl.learn.concept_map import Thresholds
from btl.learn.selector import level_for

LEVEL_WORDS = {1: "Getting there", 2: "Solid", 3: "Sharp"}
MASTERED = "Mastered"


class Band(StrEnum):
    """A viewer's level on a concept, as the page keys its scenes and icons."""

    GETTING_THERE = "getting_there"
    SOLID = "solid"
    SHARP = "sharp"


BANDS = {1: Band.GETTING_THERE, 2: Band.SOLID, 3: Band.SHARP}


def level_word(mastery: float, thresholds: Thresholds) -> str:
    """The word for a viewer's mastery of a concept."""
    if mastery >= thresholds.mastery:
        return MASTERED
    return LEVEL_WORDS[level_for(mastery)]


def band_for(mastery: float) -> Band:
    """The band for a viewer's mastery of a concept."""
    return BANDS[level_for(mastery)]


def band_rose(before: float, after: float) -> bool:
    """Whether mastery moved up a band: what a Level-up step is shown for."""
    return level_for(after) > level_for(before)
