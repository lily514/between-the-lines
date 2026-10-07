"""Scripted play: how code outside the simulator writes the opening of a possession.

The engine asks a `Director` before every possession whether it wants to write it. The planter
in `btl.plant` is the director that writes teachable moments; the simulator itself knows
nothing about concepts beyond carrying the moment's description through to the match.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

from numpy.random import Generator

from btl.schema.vocab import ConceptId
from btl.sim.chain import Side, Start, Step
from btl.sim.pitch import Point

Shape = tuple[tuple[Point, ...], tuple[Point, ...]]


@dataclass(frozen=True, slots=True)
class Script:
    """The opening of a possession, written instead of simulated, and the moment it holds.

    Everything is in the attacking team's direction. Play carries on from ``ball`` with
    ``slot`` on it. ``shapes`` replaces the shape model's positions for some steps, by index:
    the attacking team's, then the defending team's, each in formation slot order. ``pause``
    and ``answer`` are indexes into ``steps``.
    """

    steps: tuple[Step, ...]
    ball: Point
    slot: int
    shapes: Mapping[int, Shape]
    concept: ConceptId
    difficulty: int
    pause: int
    answer: int


class Director(Protocol):
    """Decides, before each possession, whether to write it instead of simulating it."""

    def script(
        self,
        planted: int,
        period_id: int,
        clock: float,
        attack: Side,
        defence: Side,
        start: Start,
        rng: Generator,
    ) -> Script | None:
        """The possession's opening, or None to let the simulator play it.

        Args:
            planted: How many moments the match holds so far.
            period_id: The current period.
            clock: Seconds since the period began.
            attack: The team about to have the ball.
            defence: The other team.
            start: How the possession would start, in the attacking team's direction.
            rng: The director's own random stream.
        """
        ...
