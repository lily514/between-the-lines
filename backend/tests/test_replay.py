from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from btl.io import load_match
from btl.replay import ReplayFrame, answer_frames, frame_at, lead_up_frames, question_action
from btl.schema import PITCH_LENGTH, PITCH_WIDTH
from btl.schema.frames import seen_by, to_left_to_right
from btl.schema.ids import ActionId
from btl.schema.match import Match
from btl.schema.moment import PlantedMoment
from btl.schema.vocab import ConceptId
from tests.fixtures.matches import HOME_KEEPER, six_event_match

SAMPLE = Path(__file__).parents[1] / "examples" / "match-0007"
# In the six-event match, play pauses after the dribble; the question is the failed pass, #2.
PASS_MOMENT = PlantedMoment(ConceptId.LINE_BREAKING_PASS, 1, ActionId(1), ActionId(2))


def keeper(frame: ReplayFrame) -> tuple[float, float]:
    (position,) = [player for player in frame.players if player.player_id == HOME_KEEPER]
    return (position.x, position.y)


def test_the_lead_up_starts_at_the_last_action_far_enough_before_the_question() -> None:
    match = six_event_match()  # an action every 4 s

    assert lead_up_frames(match, PASS_MOMENT, seconds=4, fps=2)[0].time_seconds == 4
    assert lead_up_frames(match, PASS_MOMENT, seconds=5, fps=2)[0].time_seconds == 0


def test_the_lead_up_never_reaches_back_into_the_previous_period() -> None:
    match = six_event_match()
    events = tuple(
        replace(event, period_id=2) if event.action_id >= 3 else event for event in match.events
    )
    match = replace(match, events=events)
    moment = PlantedMoment(ConceptId.COUNTER_PRESS, 1, ActionId(4), ActionId(5))

    assert lead_up_frames(match, moment, seconds=100)[0].action_id == 3


def test_lead_up_frames_are_evenly_spaced_and_end_exactly_on_the_question() -> None:
    match = six_event_match()

    frames = lead_up_frames(match, PASS_MOMENT, seconds=8, fps=2)

    assert [frame.time_seconds for frame in frames] == [step / 2 for step in range(17)]
    assert frames[-1] == frame_at(match, ActionId(2))
    assert frames[-1].ball == (70, 30)


def test_players_move_in_a_straight_line_between_snapshots() -> None:
    match = six_event_match()

    frames = lead_up_frames(match, PASS_MOMENT, seconds=8, fps=2)

    assert keeper(frames[0]) == (5, 34)
    assert keeper(frames[4]) == (5.5, 34)  # 2 s of the 4 s to the next snapshot
    assert keeper(frames[8]) == (6, 34)


def test_the_ball_flies_along_the_action_then_waits_at_its_end() -> None:
    match = six_event_match()  # pass #0 goes from (40, 34) to (60, 30)

    frames = lead_up_frames(match, PASS_MOMENT, seconds=8, fps=2)

    assert frames[2].ball == pytest.approx((40 + 20 / 3, 34 - 4 / 3))  # 1 s of a 3 s flight
    assert frames[6].ball == (60, 30)
    assert frames[7].ball == (60, 30)


def test_players_with_unknown_positions_are_left_out() -> None:
    match = six_event_match()  # no positions for action 4

    frame = frame_at(match, ActionId(4))

    assert frame.players == ()


def test_the_answer_plays_on_to_the_end_of_the_answer_action() -> None:
    match = six_event_match()

    frames = answer_frames(match, PASS_MOMENT, fps=2)

    assert frames[0].time_seconds == 8.5
    assert frames[-1].time_seconds == 11  # the pass at 8 s, plus a 3 s flight
    assert frames[-1].ball == (85, 40)


def test_the_replay_needs_player_positions() -> None:
    match = replace(six_event_match(), positions=None)

    with pytest.raises(ValueError, match="no player positions"):
        frame_at(match, ActionId(0))


def sample() -> Match:
    return load_match(SAMPLE)[0]


@pytest.mark.parametrize("number", range(6))
def test_every_sample_moment_replays_on_the_pitch_and_freezes_on_its_picture(number: int) -> None:
    match = sample()
    moment = match.planted[number]
    question = question_action(moment)
    seen = seen_by(match, match.events[question].team_id)

    frames = (*lead_up_frames(seen, moment), *answer_frames(seen, moment))

    times = [frame.time_seconds for frame in frames]
    assert times == sorted(times)
    for frame in frames:
        xy = np.array([(p.x, p.y) for p in frame.players] + [frame.ball])
        assert (xy >= 0).all() and (xy[:, 0] <= PITCH_LENGTH).all()
        assert (xy[:, 1] <= PITCH_WIDTH).all()
    # The pause looks the same as the picture `btl moments` shows.
    picture = to_left_to_right(match).snapshot(question)
    assert picture is not None
    assert frame_at(seen, question).players == picture.positions
