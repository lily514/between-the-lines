"""The starting eleven: which squad members fill a formation's slots."""

from dataclasses import dataclass

from btl.league.league import Club, Player
from btl.sim.shape import Formation


@dataclass(frozen=True, slots=True)
class Lineup:
    """A club's starting eleven, one player per formation slot, in slot order."""

    club: Club
    formation: Formation
    players: tuple[Player, ...]


def pick_lineup(club: Club, formation: Formation) -> Lineup:
    """Fill each slot with the first unused squad member of the slot's role.

    Raises:
        ValueError: If the squad has too few players in a role for the formation.
    """
    remaining = {role: list(club.players(role)) for role in {slot.role for slot in formation.slots}}
    players: list[Player] = []
    for slot in formation.slots:
        if not remaining[slot.role]:
            raise ValueError(
                f"{club.name} has too few {slot.role.name.lower()}s for {formation.name}"
            )
        players.append(remaining[slot.role].pop(0))
    return Lineup(club=club, formation=formation, players=tuple(players))
