from btl.learn.play_by_play import Spell, Touch, play_by_play
from btl.schema.ids import PlayerId
from tests.fixtures.matches import (
    AWAY,
    AWAY_MIDFIELDER,
    HOME,
    HOME_MIDFIELDER,
    HOME_WINGER,
    six_event_match,
)


def touch(player_id: PlayerId, action_id: int) -> Touch:
    return Touch(player_id, 1, action_id * 4.0)


def test_from_kick_off_each_spell_lists_only_the_team_on_the_ball() -> None:
    spells = play_by_play(six_event_match(), None, (2, 0.0))

    assert spells == (
        Spell(HOME, (touch(HOME_MIDFIELDER, 0), touch(HOME_WINGER, 1), touch(HOME_WINGER, 2))),
        Spell(AWAY, (touch(AWAY_MIDFIELDER, 3), touch(AWAY_MIDFIELDER, 5))),
    )


def test_it_starts_after_where_the_viewer_left_off_and_stops_before_the_moment() -> None:
    spells = play_by_play(six_event_match(), (1, 4.0), (1, 20.0))

    assert spells == (
        Spell(HOME, (touch(HOME_WINGER, 2),)),
        Spell(AWAY, (touch(AWAY_MIDFIELDER, 3),)),
    )


def test_a_moment_straight_after_the_last_question_has_no_play_by_play() -> None:
    assert play_by_play(six_event_match(), (1, 8.0), (1, 12.0)) == ()
