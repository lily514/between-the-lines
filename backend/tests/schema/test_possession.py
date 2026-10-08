from btl.schema.ids import ActionId, TeamId
from btl.schema.possession import Possession, changes_hands_in_open_play, split_possessions
from btl.schema.vocab import ActionType, Result
from tests.fixtures.matches import (
    AWAY,
    AWAY_MIDFIELDER,
    HOME,
    HOME_MIDFIELDER,
    make_event,
    six_event_match,
)


def spell(team_id: TeamId, period_id: int, first: int, last: int) -> Possession:
    return Possession(team_id, period_id, ActionId(first), ActionId(last))


def test_interception_starts_a_new_possession_and_a_failed_tackle_does_not() -> None:
    possessions = split_possessions(six_event_match().events)

    assert possessions == (spell(HOME, 1, 0, 2), spell(AWAY, 1, 3, 5))


def test_foul_by_the_defending_team_stays_in_the_current_possession() -> None:
    events = (
        make_event(0, HOME, HOME_MIDFIELDER, (40, 34), (60, 34)),
        make_event(1, AWAY, AWAY_MIDFIELDER, (60, 34), (60, 34), ActionType.FOUL, Result.FAIL),
        make_event(2, HOME, HOME_MIDFIELDER, (60, 34), (75, 30)),
    )

    assert split_possessions(events) == (spell(HOME, 1, 0, 2),)


def test_successful_tackle_wins_the_ball() -> None:
    events = (
        make_event(0, HOME, HOME_MIDFIELDER, (40, 34), (60, 34), ActionType.DRIBBLE),
        make_event(1, AWAY, AWAY_MIDFIELDER, (60, 34), (60, 34), ActionType.TACKLE),
    )

    assert split_possessions(events) == (spell(HOME, 1, 0, 0), spell(AWAY, 1, 1, 1))


def test_new_period_starts_a_new_possession_for_the_same_team() -> None:
    events = (
        make_event(0, HOME, HOME_MIDFIELDER, (40, 34), (60, 34)),
        make_event(1, HOME, HOME_MIDFIELDER, (52.5, 34), (40, 34), period_id=2),
    )

    assert split_possessions(events) == (spell(HOME, 1, 0, 0), spell(HOME, 2, 1, 1))


def test_no_events_means_no_possessions() -> None:
    assert split_possessions(()) == ()


def test_the_ball_changes_hands_in_open_play_when_won_from_the_other_team() -> None:
    lost = make_event(0, HOME, HOME_MIDFIELDER, (60, 30), (70, 30), result=Result.FAIL)
    won = make_event(1, AWAY, AWAY_MIDFIELDER, (70, 30), (70, 30), ActionType.INTERCEPTION)

    assert changes_hands_in_open_play(lost, won)


def test_a_set_piece_does_not_win_the_ball_in_open_play() -> None:
    out = make_event(0, HOME, HOME_MIDFIELDER, (60, 30), (70, 0), result=Result.FAIL)
    throw = make_event(1, AWAY, AWAY_MIDFIELDER, (70, 0), (65, 10), ActionType.THROW_IN)

    assert not changes_hands_in_open_play(out, throw)


def test_the_kickoff_after_a_goal_does_not_win_the_ball_in_open_play() -> None:
    goal = make_event(0, HOME, HOME_MIDFIELDER, (95, 34), (105, 34), ActionType.SHOT)
    kickoff = make_event(1, AWAY, AWAY_MIDFIELDER, (52.5, 34), (60, 30))

    assert not changes_hands_in_open_play(goal, kickoff)
