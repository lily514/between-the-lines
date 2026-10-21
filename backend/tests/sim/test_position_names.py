import pytest

from btl.sim.position_names import GOALKEEPER, position_names
from btl.sim.shape import FORMATIONS, FOUR_FOUR_TWO, FOUR_THREE_THREE, Formation


@pytest.mark.parametrize("formation", FORMATIONS.values(), ids=FORMATIONS.keys())
def test_every_slot_has_a_position_with_a_plain_description(formation: Formation) -> None:
    positions = position_names(formation)

    assert len(positions) == len(formation.slots)
    assert positions.count(GOALKEEPER) == 1
    for position in positions:
        assert position.name and position.description.endswith(".")
        assert position.short.isupper() and len(position.short) == 2


def test_a_four_four_two_has_full_backs_wide_midfielders_and_two_strikers() -> None:
    shorts = [position.short for position in position_names(FOUR_FOUR_TWO)]

    # Slots run from the right touchline to the left.
    assert shorts == ["GK", "RB", "CB", "CB", "LB", "RM", "CM", "CM", "LM", "ST", "ST"]


def test_a_front_three_has_two_wingers_and_a_midfield_three_plays_centrally() -> None:
    shorts = [position.short for position in position_names(FOUR_THREE_THREE)]

    assert shorts[5:] == ["CM", "CM", "CM", "RW", "ST", "LW"]
