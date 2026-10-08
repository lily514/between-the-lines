from functools import cache

import numpy as np
import pytest

from btl.concepts.base import ConceptTag, match_context
from btl.concepts.counter_attack import BOX_DEPTH, HALFWAY, CounterAttack
from btl.league.league import generate_league
from btl.schema import PITCH_LENGTH
from btl.schema.match import Match
from btl.schema.vocab import ActionType, ConceptId
from btl.sim.engine import simulate_match
from tests.fixtures.concepts import won_and_carried
from tests.fixtures.matches import AWAY, HOME

OWN_HALF = (30.0, 34.0)
OPPONENT_HALF = (60.0, 34.0)


@cache
def simulated(seed: int) -> Match:
    home, away = generate_league(np.random.default_rng(0)).clubs[:2]
    return simulate_match(home, away, seed, with_snapshots=False)


def detect(match: Match) -> tuple[ConceptTag, ...]:
    return CounterAttack().detect(match_context(match))


def test_winning_it_in_your_own_half_and_in_the_box_9_seconds_later_is_a_counter() -> None:
    (tag,) = detect(won_and_carried(9, OWN_HALF))

    assert tag.concept is ConceptId.COUNTER_ATTACK
    assert tag.action_id == 1
    assert tag.span == (1, 3)
    assert tag.evidence == {"seconds to the box": 9.0, "won (m from own goal)": 30.0}


def test_reaching_the_box_after_15_seconds_is_too_slow() -> None:
    assert detect(won_and_carried(15, OWN_HALF)) == ()


def test_winning_it_in_the_opponents_half_is_not_a_counter_attack() -> None:
    assert detect(won_and_carried(9, OPPONENT_HALF)) == ()


def test_the_away_team_counter_attacks_the_other_way() -> None:
    (tag,) = detect(won_and_carried(9, OWN_HALF, team=AWAY))

    assert tag.evidence["won (m from own goal)"] == 30.0
    assert detect(won_and_carried(9, OPPONENT_HALF, team=AWAY)) == ()


def test_the_time_allowed_is_a_setting() -> None:
    match = won_and_carried(15, OWN_HALF)

    assert [
        tag.action_id for tag in CounterAttack(max_seconds=16).detect(match_context(match))
    ] == [1]


def test_a_possession_starting_with_a_set_piece_is_not_a_counter_attack() -> None:
    assert detect(won_and_carried(9, OWN_HALF, won_with=ActionType.THROW_IN)) == ()


@pytest.mark.parametrize("seed", range(5))
def test_in_simulated_play_every_tag_goes_from_own_half_to_the_box_quickly(seed: int) -> None:
    played = simulated(seed)

    tags = detect(played)

    for tag in tags:
        win, in_box = played.events[tag.span[0]], played.events[tag.span[1]]
        assert win.team_id == in_box.team_id
        attacks_towards_105 = win.team_id == HOME
        assert (win.start_x < HALFWAY) == attacks_towards_105
        goal_x = PITCH_LENGTH if attacks_towards_105 else 0.0
        assert abs(in_box.start_x - goal_x) <= BOX_DEPTH
        assert 0 <= tag.evidence["seconds to the box"] <= 12
        assert in_box.period_id == win.period_id


def test_simulated_matches_have_some_counter_attacks() -> None:
    assert sum(len(detect(simulated(seed))) for seed in range(5)) > 0
