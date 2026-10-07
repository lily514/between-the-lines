import pytest
from socceraction.spadl import config

from btl.schema.vocab import ActionType, BodyPart, Result


@pytest.mark.parametrize(
    ("enum", "spadl_names"),
    [
        (ActionType, config.actiontypes),
        (Result, config.results),
        (BodyPart, config.bodyparts),
    ],
)
def test_enum_matches_socceraction_names_and_ids(
    enum: type[ActionType] | type[Result] | type[BodyPart], spadl_names: list[str]
) -> None:
    ours = [(member.value, member.spadl_name) for member in enum]

    assert ours == list(enumerate(spadl_names))
