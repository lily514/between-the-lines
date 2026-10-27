from dataclasses import replace

from btl.learn.match_stats import SideStats, stats_timeline
from btl.schema.match import Match
from btl.schema.vocab import ActionType, Result
from tests.fixtures.matches import six_event_match


def side(possession: int, **counts: int) -> SideStats:
    names = ("goals", "attempts", "corners", "fouls", "yellow_cards", "red_cards")
    numbers = dict.fromkeys(names, 0)
    return SideStats(possession=possession, **(numbers | counts))


def eventful() -> Match:
    """Home shoots at 4 s and takes a corner at 8 s; away is booked for a foul at 16 s."""
    match = six_event_match()
    events = list(match.events)
    events[1] = replace(events[1], action_type=ActionType.SHOT, result=Result.FAIL)
    events[2] = replace(events[2], action_type=ActionType.CORNER_CROSSED)
    booked = Result.YELLOW_CARD
    events[4] = replace(
        events[4], team_id=match.away_team_id, action_type=ActionType.FOUL, result=booked
    )
    return replace(match, events=tuple(events))


def test_from_kick_off_an_entry_is_added_when_the_ball_changes_hands_or_a_number_changes() -> None:
    timeline = stats_timeline(eventful(), None, (2, 0.0))

    assert [(entry.time_seconds, entry.home, entry.away) for entry in timeline] == [
        (0.0, side(50), side(50)),
        (4.0, side(100, attempts=1), side(0)),
        (8.0, side(100, attempts=1, corners=1), side(0)),
        (12.0, side(100, attempts=1, corners=1), side(0)),
        (16.0, side(75, attempts=1, corners=1), side(25, fouls=1, yellow_cards=1)),
    ]


def test_possession_is_the_share_of_time_on_the_ball_and_moves_only_with_an_entry() -> None:
    timeline = stats_timeline(eventful(), None, (2, 0.0))

    # Home held it from 0 s to 12 s, away from 12 s; by the booking at 16 s that's 12 s to 4 s.
    assert [(entry.home.possession, entry.away.possession) for entry in timeline][-2:] == [
        (100, 0),
        (75, 25),
    ]
    # A failed tackle doesn't win the ball, so nothing changes after the interception at 12 s.
    assert stats_timeline(six_event_match(), None, (2, 0.0))[-1].time_seconds == 12.0


def test_it_opens_where_the_viewer_left_off_and_stops_before_the_moment() -> None:
    timeline = stats_timeline(eventful(), (1, 6.0), (1, 16.0))

    assert [(entry.time_seconds, entry.home.corners, entry.away.fouls) for entry in timeline] == [
        (6.0, 0, 0),
        (8.0, 1, 0),
        (12.0, 1, 0),
    ]
    assert timeline[0].home.attempts == 1


def test_a_viewer_who_left_off_after_the_moment_gets_the_numbers_from_just_before_it() -> None:
    timeline = stats_timeline(eventful(), (1, 20.0), (1, 6.0))

    assert len(timeline) == 1
    assert (timeline[0].time_seconds, timeline[0].home.attempts, timeline[0].home.corners) == (
        6.0,
        1,
        0,
    )
