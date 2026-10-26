import pytest

from btl.learn.concept_map import Thresholds
from btl.learn.levels import level_word

THRESHOLDS = Thresholds(unlock=0.8, mastery=0.95)


@pytest.mark.parametrize(
    ("mastery", "word"),
    [
        (0.0, "Getting there"),
        (0.35, "Getting there"),
        (0.4, "Solid"),
        (0.69, "Solid"),
        (0.7, "Sharp"),
        (0.94, "Sharp"),
        (0.95, "Mastered"),
        (1.0, "Mastered"),
    ],
)
def test_the_word_follows_the_question_levels_then_mastery(mastery: float, word: str) -> None:
    assert level_word(mastery, THRESHOLDS) == word
