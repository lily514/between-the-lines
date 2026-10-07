import pytest

from btl.plant.spec import MomentSpec, PlantRequest, parse_plant
from btl.schema.vocab import ConceptId

LINE_BREAK = ConceptId.LINE_BREAKING_PASS


def test_reads_a_concept_with_its_levels() -> None:
    request = parse_plant(["line_breaking_pass:1,2,3"])

    assert request.moments == tuple(MomentSpec(LINE_BREAK, level) for level in (1, 2, 3))


def test_reads_several_concepts() -> None:
    request = parse_plant(["line_breaking_pass:2", "switch_of_play:1"])

    assert request.moments == (
        MomentSpec(LINE_BREAK, 2),
        MomentSpec(ConceptId.SWITCH_OF_PLAY, 1),
    )


def test_moments_happen_easiest_first() -> None:
    request = PlantRequest((MomentSpec(LINE_BREAK, 3), MomentSpec(LINE_BREAK, 1)))

    assert [moment.difficulty for moment in request.in_match_order] == [1, 3]


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("nutmeg:1", "no concept 'nutmeg'"),
        ("line_breaking_pass", "levels are whole numbers"),
        ("line_breaking_pass:1,two", "levels are whole numbers"),
        ("line_breaking_pass:4", "difficulty must be one of"),
    ],
)
def test_explains_what_it_cannot_read(text: str, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        parse_plant([text])
