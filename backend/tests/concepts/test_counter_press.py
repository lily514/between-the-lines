from dataclasses import replace
from functools import cache

import numpy as np
import pytest

from btl.concepts.base import ConceptId, ConceptTag, match_context
from btl.concepts.counter_press import HALFWAY, CounterPress
from btl.league.league import generate_league
from btl.schema.ids import ActionId
from btl.schema.match import Match
from btl.schema.vocab import ActionType, Result
from btl.sim.engine import simulate_match
from tests.fixtures.concepts import lost_and_won_back
from tests.fixtures.matches import AWAY, HOME

OPPONENT_HALF = (70.0, 30.0)
OWN_HALF = (40.0, 30.0)


@cache
def simulated(seed: int) -> Match:
    home, away = generate_league(np.random.default_rng(0)).clubs[:2]
    return simulate_match(home, away, seed, with_snapshots=False)


def detect(match: Match) -> tuple[ConceptTag, ...]:
    return CounterPress().detect(match_context(match))


def test_winning_it_back_in_4_seconds_in_the_opponents_half_is_a_counter_press() -> None:
    (tag,) = detect(lost_and_won_back(4, OPPONENT_HALF))

    assert tag.concept is ConceptId.COUNTER_PRESS
    assert tag.action_id == 4
    assert tag.span == (1, 4)
    assert tag.evidence == {"seconds to win back": 4.0, "metres from goal": 35.0}


def test_winning_it_back_after_7_seconds_is_too_slow() -> None:
    assert detect(lost_and_won_back(7, OPPONENT_HALF)) == ()


def test_winning_it_back_in_your_own_half_is_not_a_counter_press() -> None:
    assert detect(lost_and_won_back(4, OWN_HALF)) == ()


def test_the_away_team_counter_presses_attacking_the_other_way() -> None:
    (tag,) = detect(lost_and_won_back(4, OPPONENT_HALF, team=AWAY))

    assert tag.action_id == 4
    assert tag.evidence["metres from goal"] == 35.0
    assert detect(lost_and_won_back(4, OWN_HALF, team=AWAY)) == ()


def test_the_time_allowed_is_a_setting() -> None:
    match = lost_and_won_back(7, OPPONENT_HALF)

    assert [tag.action_id for tag in CounterPress(max_seconds=8).detect(match_context(match))] == [
        4
    ]


def test_winning_the_ball_from_a_set_piece_is_not_a_counter_press() -> None:
    assert detect(lost_and_won_back(4, OPPONENT_HALF, won_with=ActionType.THROW_IN)) == ()


def test_losing_the_ball_to_a_set_piece_is_not_losing_it_in_open_play() -> None:
    assert detect(lost_and_won_back(4, OPPONENT_HALF, lost_with=ActionType.GOALKICK)) == ()


def test_winning_the_ball_straight_after_scoring_is_not_a_counter_press() -> None:
    match = lost_and_won_back(4, OPPONENT_HALF)
    passed, failed_pass, interception, *rest = match.events
    scored = (
        passed,
        replace(failed_pass, action_type=ActionType.SHOT, result=Result.SUCCESS),
        replace(interception, action_type=ActionType.PASS, start_x=52.5, start_y=34),
        *rest,
    )

    assert detect(replace(match, events=scored)) == ()


def test_a_new_half_starts_afresh() -> None:
    match = lost_and_won_back(4, OPPONENT_HALF)
    second_half = tuple(
        replace(event, period_id=2) if event.action_id >= 4 else event for event in match.events
    )

    assert detect(replace(match, events=second_half)) == ()


@pytest.mark.parametrize("seed", range(3))
def test_in_simulated_play_every_tag_is_a_quick_regain_in_the_opponents_half(seed: int) -> None:
    played = simulated(seed)
    events = {event.action_id: event for event in played.events}

    tags = detect(played)

    assert tags
    for tag in tags:
        lost_touch, regain = events[tag.span[0]], events[tag.action_id]
        assert lost_touch.team_id == regain.team_id
        attacks_towards_105 = regain.team_id == HOME
        assert (regain.start_x > HALFWAY) == attacks_towards_105
        assert 0 <= tag.evidence["seconds to win back"] <= 5
        between = [events[ActionId(i)] for i in range(tag.span[0] + 1, tag.action_id)]
        assert any(event.team_id != regain.team_id for event in between)
