from dataclasses import replace

import pytest

from btl.learn.track import BallPoint, Track, track_between
from btl.replay import LONGEST_ACTION
from btl.schema.ids import ActionId
from tests.fixtures.learning import designed_with_candidates
from tests.fixtures.matches import AWAY_MIDFIELDER, HOME_MIDFIELDER, HOME_WINGER, six_event_match


def action_ids(track: Track) -> list[int]:
    return [frame.action_id for frame in track.frames]


def test_it_starts_after_where_the_viewer_left_off_and_closes_on_the_moment() -> None:
    track = track_between(six_event_match(), (1, 4.0), (1, 12.0))

    assert action_ids(track) == [2, 3]


def test_from_kick_off_it_starts_at_the_first_action() -> None:
    track = track_between(six_event_match(), None, (1, 8.0))

    assert action_ids(track) == [0, 1, 2]


def test_the_moment_closes_the_track_without_its_flight() -> None:
    match = six_event_match()

    track = track_between(match, None, (1, 8.0))

    assert track.ball[-1] == BallPoint(1, 8.0, 70, 30)
    assert all(point.time_seconds <= 8.0 for point in track.ball)


def test_each_frame_holds_every_slot_and_the_player_on_the_ball() -> None:
    match = six_event_match()

    frame = track_between(match, None, (1, 0.0)).frames[0]

    assert frame.positions == ((5, 34), (40, 34), (100, 34), (55, 36))
    assert frame.on_ball == HOME_MIDFIELDER
    assert track_between(match, None, (1, 20.0)).frames[-1].on_ball == AWAY_MIDFIELDER


def test_the_player_on_the_ball_need_not_be_tracked() -> None:
    frame = track_between(six_event_match(), (1, 0.0), (1, 4.0)).frames[0]

    assert frame.on_ball == HOME_WINGER


def test_unknown_positions_stay_unknown() -> None:
    frame = track_between(six_event_match(), (1, 12.0), (1, 16.0)).frames[0]

    assert frame.positions == (None, None, None, None)


def test_the_ball_reaches_the_end_of_an_action_once_its_capped_flight_is_over() -> None:
    track = track_between(six_event_match(), None, (1, 4.0))  # an action every 4 s

    assert track.ball == (
        BallPoint(1, 0.0, 40, 34),
        BallPoint(1, LONGEST_ACTION, 60, 30),
        BallPoint(1, 4.0, 60, 30),
    )


def test_an_action_with_no_time_before_the_next_has_no_flight() -> None:
    match = six_event_match()
    events = tuple(
        replace(event, time_seconds=0.0) if event.action_id == 1 else event
        for event in match.events
    )

    track = track_between(replace(match, events=events), None, (1, 4.0))

    assert track.ball[:2] == (BallPoint(1, 0.0, 40, 34), BallPoint(1, 0.0, 60, 30))


def test_frames_keep_their_period_so_a_half_time_is_a_cut() -> None:
    match = six_event_match()
    events = tuple(
        replace(event, period_id=2, time_seconds=event.time_seconds - 12)
        if event.action_id >= 3
        else event
        for event in match.events
    )

    track = track_between(replace(match, events=events), (1, 4.0), (2, 4.0))

    assert [(frame.period_id, frame.time_seconds) for frame in track.frames] == [
        (1, 8.0),
        (2, 0.0),
        (2, 4.0),
    ]


def test_leaving_off_at_or_past_the_moment_leaves_nothing_to_track() -> None:
    match = six_event_match()
    assert match.positions is not None

    assert track_between(match, (1, 12.0), (1, 12.0)) == Track(match.positions.slots, (), ())
    assert track_between(match, (1, 16.0), (1, 12.0)).frames == ()
    assert track_between(match, (1, 14.0), (1, 13.0)).frames == ()


def test_a_match_without_positions_has_no_track() -> None:
    with pytest.raises(ValueError, match="no player positions"):
        track_between(replace(six_event_match(), positions=None), None, (1, 4.0))


def test_every_candidate_closes_its_track_on_its_picture_and_nothing_after() -> None:
    match, _, candidates = designed_with_candidates(0)
    assert match.positions is not None
    previous: tuple[int, float] | None = None
    for candidate in candidates:
        before = (candidate.period_id, candidate.time_seconds)

        track = track_between(match, previous, before)

        if previous == before:
            assert track.frames == ()
            continue
        last = track.frames[-1]
        picture = match.events[candidate.tag.action_id]
        assert (last.period_id, last.time_seconds) == before
        assert match.events[last.action_id].start_x == picture.start_x
        assert match.snapshot(last.action_id) == match.snapshot(ActionId(candidate.tag.action_id))
        assert track.ball[-1] == BallPoint(*before, picture.start_x, picture.start_y)
        assert all((point.period_id, point.time_seconds) <= before for point in track.ball)
        assert all((frame.period_id, frame.time_seconds) < before for frame in track.frames[:-1])
        previous = before
