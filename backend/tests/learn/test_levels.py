import pytest

from btl.learn.concept_map import Thresholds
from btl.learn.levels import Band, band_for, band_rose, level_word

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


@pytest.mark.parametrize(
    ("mastery", "band"),
    [(0.0, Band.GETTING_THERE), (0.39, Band.GETTING_THERE), (0.4, Band.SOLID), (0.7, Band.SHARP)],
)
def test_the_band_is_the_level_as_a_key_and_mastered_stays_sharp(
    mastery: float, band: Band
) -> None:
    assert band_for(mastery) is band
    assert band_for(0.99) is Band.SHARP
    assert [b.value for b in Band] == ["getting_there", "solid", "sharp"]


def test_a_level_up_is_a_band_rising_not_a_number_moving() -> None:
    assert band_rose(0.35, 0.62)
    assert band_rose(0.35, 0.76)
    assert not band_rose(0.41, 0.69)
    assert not band_rose(0.62, 0.35)
