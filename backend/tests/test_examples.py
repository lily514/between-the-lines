"""The committed sample match, which the README walks through."""

from pathlib import Path

from btl.concepts.base import match_context
from btl.concepts.registry import detect_all
from btl.io import load_match

SAMPLE = Path(__file__).parents[1] / "examples" / "match-0007"


def test_the_sample_match_loads_and_its_planted_moments_are_detected() -> None:
    match, info = load_match(SAMPLE)

    assert info.seed == 7
    assert len(match.planted) == 6
    found = {(tag.concept, tag.action_id) for tag in detect_all(match_context(match))}
    for moment in match.planted:
        assert (moment.concept, moment.answer_action_id) in found
