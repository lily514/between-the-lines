import pytest

from btl.concepts.base import match_context
from btl.learn.player_stats import PlayerStats, watched_numbers
from btl.schema.ids import PlayerId
from tests.fixtures.concepts import BACK_LINE, MIDFIELD_LINE, one_pass
from tests.fixtures.matches import (
    AWAY,
    AWAY_KEEPER,
    AWAY_MIDFIELDER,
    HOME,
    HOME_MIDFIELDER,
    HOME_WINGER,
    six_event_match,
)

# Six events: a completed pass, a dribble, a failed pass, an interception, a failed tackle and
# a completed pass. Ratings stand in for an xT model's.
SIX_THREAT = (0.02, 0.01, None, None, None, -0.01)


def numbers() -> dict[PlayerId, PlayerStats]:
    through_the_lines = one_pass((40, 34), (85, 34), MIDFIELD_LINE + BACK_LINE)
    watched = [
        (match_context(through_the_lines, (0.08,)), [HOME_MIDFIELDER, AWAY_KEEPER]),
        (
            match_context(six_event_match(), SIX_THREAT),
            [HOME_MIDFIELDER, HOME_WINGER, AWAY_MIDFIELDER, AWAY_KEEPER],
        ),
    ]
    return dict(watched_numbers(watched).players)


def test_passes_line_breaks_and_threat_are_counted_per_player() -> None:
    counted = numbers()

    def counts(player: PlayerId) -> tuple[int, int, int, int]:
        stats = counted[player]
        return (
            stats.matches,
            stats.passes_completed,
            stats.passes_tried,
            stats.line_breaking_passes,
        )

    assert counts(HOME_MIDFIELDER) == (2, 2, 2, 1)
    assert counts(HOME_WINGER) == (1, 0, 1, 0)
    assert counts(AWAY_MIDFIELDER) == (1, 1, 1, 0)
    assert counted[HOME_MIDFIELDER].threat_added == pytest.approx(0.10)
    assert counted[HOME_WINGER].threat_added == pytest.approx(0.01)
    assert counted[AWAY_MIDFIELDER].threat_added == pytest.approx(-0.01)


def test_a_starter_who_never_touched_the_ball_has_real_zeros() -> None:
    assert numbers()[AWAY_KEEPER] == PlayerStats(2, 0, 0, 0, 0.0)


def test_each_club_counts_the_matches_it_played() -> None:
    match = match_context(six_event_match(), SIX_THREAT)

    counted = watched_numbers([(match, []), (match, [])])

    assert counted.team_matches == {HOME: 2, AWAY: 2}


def test_numbers_need_threat_ratings() -> None:
    with pytest.raises(ValueError, match="threat ratings"):
        watched_numbers([(match_context(six_event_match()), [])])
