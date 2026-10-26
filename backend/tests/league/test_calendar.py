from datetime import date

import pytest

from btl.league.calendar import KICK_OFF, SEASON_START, matchday


def test_the_first_match_is_on_the_season_s_first_saturday() -> None:
    first = matchday(1)

    assert first.day == SEASON_START
    assert first.day.weekday() == 5
    assert first.kick_off == KICK_OFF
    assert first.label == "Sat 24 Oct"


def test_each_match_is_a_week_after_the_last() -> None:
    days = [matchday(n).day for n in (1, 2, 3)]

    assert days == [date(2026, 10, 24), date(2026, 10, 31), date(2026, 11, 7)]
    assert matchday(3).label == "Sat 7 Nov"


def test_match_numbers_count_from_one() -> None:
    with pytest.raises(ValueError, match="from 1"):
        matchday(0)
