from btl.learn.play_by_play import (
    Spell,
    Touch,
    Zone,
    play_by_play,
    zone_of,
)
from btl.schema.ids import PlayerId
from btl.schema.vocab import ActionType, Result
from tests.fixtures.matches import (
    AWAY,
    AWAY_MIDFIELDER,
    HOME,
    HOME_MIDFIELDER,
    HOME_WINGER,
    make_event,
    six_event_match,
)


def touch(
    player_id: PlayerId,
    action_id: int,
    zone: Zone,
    action_type: ActionType = ActionType.PASS,
    result: Result = Result.SUCCESS,
) -> Touch:
    return Touch(player_id, 1, action_id * 4.0, action_type, result, zone)


def test_from_kick_off_each_spell_lists_only_the_team_on_the_ball() -> None:
    spells = play_by_play(six_event_match(), None, (2, 0.0))

    assert spells == (
        Spell(
            HOME,
            (
                touch(HOME_MIDFIELDER, 0, Zone.MIDDLE_THIRD),
                touch(HOME_WINGER, 1, Zone.MIDDLE_THIRD, ActionType.DRIBBLE),
                touch(HOME_WINGER, 2, Zone.FINAL_THIRD, result=Result.FAIL),
            ),
        ),
        Spell(
            AWAY,
            (
                touch(AWAY_MIDFIELDER, 3, Zone.OWN_THIRD, ActionType.INTERCEPTION),
                touch(AWAY_MIDFIELDER, 5, Zone.OWN_THIRD),
            ),
        ),
    )


def test_it_starts_after_where_the_viewer_left_off_and_stops_before_the_moment() -> None:
    spells = play_by_play(six_event_match(), (1, 4.0), (1, 20.0))

    assert spells == (
        Spell(HOME, (touch(HOME_WINGER, 2, Zone.FINAL_THIRD, result=Result.FAIL),)),
        Spell(AWAY, (touch(AWAY_MIDFIELDER, 3, Zone.OWN_THIRD, ActionType.INTERCEPTION),)),
    )


def test_a_moment_straight_after_the_last_question_has_no_play_by_play() -> None:
    assert play_by_play(six_event_match(), (1, 8.0), (1, 12.0)) == ()


def test_the_zone_is_seen_by_the_team_making_the_action() -> None:
    def at(team: str, x: float, y: float = 34.0) -> Zone:
        team_id = HOME if team == "home" else AWAY
        return zone_of(make_event(0, team_id, HOME_MIDFIELDER, (x, y), (x, y)), HOME)

    assert [at("home", x) for x in (10, 40, 75, 95)] == [
        Zone.OWN_THIRD,
        Zone.MIDDLE_THIRD,
        Zone.FINAL_THIRD,
        Zone.BOX,
    ]
    assert at("away", 10) is Zone.BOX
    assert at("home", 95, 2) is Zone.FINAL_THIRD
