"""How often the viewer wants questions: the Preferences setting the selector's caps follow.

Normal is the selector's usual 2 to 4 questions in play, plus up to 2 at each break. Rarely is
at most 1 in play, breaks as usual. Off asks nothing, so the match is captions and reports only.
"""

from dataclasses import dataclass
from enum import StrEnum


class Pace(StrEnum):
    """How often questions come."""

    NORMAL = "normal"
    RARELY = "rarely"
    OFF = "off"


@dataclass(frozen=True, slots=True)
class Caps:
    """The most questions in play, the most at each break, and the fewest a match should have."""

    in_play: int
    per_break: int
    minimum: int
