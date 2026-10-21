"""Names for the positions in a formation, in plain words for someone new to football.

A position is named from its formation slot: its role, and where it sits across its line. The
two ends of a wide enough line play out wide (a back four has a right back and a left back);
everyone else plays in the centre. Right and left are the team's own, facing the goal it
attacks.
"""

from dataclasses import dataclass

from btl.league.league import Role
from btl.sim.shape import Formation, Slot

# How many players a line needs before its two ends count as wide players. Two strikers are
# both strikers; a front three has two wingers.
WIDE_FROM: dict[Role, int] = {Role.DEFENDER: 4, Role.MIDFIELDER: 4, Role.FORWARD: 3}


@dataclass(frozen=True, slots=True)
class Position:
    """A position: its usual abbreviation, its name, and what the player there does."""

    short: str
    name: str
    description: str


GOALKEEPER = Position(
    "GK",
    "Goalkeeper",
    "Stops shots, and is the only player allowed to handle the ball, inside their own box.",
)
# Keyed by role and side: "right", "centre" or "left".
OUTFIELD: dict[tuple[Role, str], Position] = {
    (Role.DEFENDER, "right"): Position(
        "RB", "Right back", "Defends the right side, and joins attacks down it."
    ),
    (Role.DEFENDER, "centre"): Position(
        "CB", "Centre back", "Defends the middle in front of goal: wins headers, blocks shots."
    ),
    (Role.DEFENDER, "left"): Position(
        "LB", "Left back", "Defends the left side, and joins attacks down it."
    ),
    (Role.MIDFIELDER, "right"): Position(
        "RM", "Right midfielder", "Covers the right side of midfield, and crosses from it."
    ),
    (Role.MIDFIELDER, "centre"): Position(
        "CM", "Centre midfielder", "Links defence and attack in the middle: passes, tackles, runs."
    ),
    (Role.MIDFIELDER, "left"): Position(
        "LM", "Left midfielder", "Covers the left side of midfield, and crosses from it."
    ),
    (Role.FORWARD, "right"): Position(
        "RW", "Right winger", "Attacks down the right, to cross or cut inside and shoot."
    ),
    (Role.FORWARD, "centre"): Position(
        "ST", "Striker", "Plays furthest forward, closest to goal: there to score."
    ),
    (Role.FORWARD, "left"): Position(
        "LW", "Left winger", "Attacks down the left, to cross or cut inside and shoot."
    ),
}


def position_names(formation: Formation) -> tuple[Position, ...]:
    """Each slot's position, in slot order."""
    return tuple(_position(formation, slot) for slot in formation.slots)


def _position(formation: Formation, slot: Slot) -> Position:
    if slot.role is Role.GOALKEEPER:
        return GOALKEEPER
    line = sorted(
        other.across
        for other in formation.slots
        if other.role is slot.role and other.depth == slot.depth
    )
    wide = len(line) >= WIDE_FROM[slot.role] and slot.across in (line[0], line[-1])
    # Slots run across from the right touchline (0) to the left (1).
    side = "centre" if not wide else ("right" if slot.across < 0.5 else "left")
    return OUTFIELD[slot.role, side]
