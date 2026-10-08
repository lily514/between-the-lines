from dataclasses import replace

import numpy as np
import pytest

from btl.league.league import Club, Role, generate_league
from btl.sim.lineup import pick_lineup
from btl.sim.shape import FORMATIONS, FOUR_THREE_THREE, Formation


def club() -> Club:
    return generate_league(np.random.default_rng(0)).clubs[0]


@pytest.mark.parametrize("formation", FORMATIONS.values(), ids=FORMATIONS.keys())
def test_every_slot_gets_a_different_player_of_its_role(formation: Formation) -> None:
    lineup = pick_lineup(club(), formation)

    assert len(set(lineup.players)) == 11
    for slot, player in zip(formation.slots, lineup.players, strict=True):
        assert player.role is slot.role


def test_a_squad_short_of_forwards_is_rejected() -> None:
    squad = club().squad
    forwards = [player for player in squad if player.role is Role.FORWARD]
    others = [player for player in squad if player.role is not Role.FORWARD]
    short_of_forwards = replace(club(), squad=(*others, *forwards[:2]))

    with pytest.raises(ValueError, match="too few forwards"):
        pick_lineup(short_of_forwards, FOUR_THREE_THREE)
