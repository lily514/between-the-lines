from itertools import pairwise

import numpy as np
import pytest

from btl.concepts.base import ConceptTag, match_context
from btl.concepts.offside import CLEAR, EASIEST, HARDEST, NEAR_LINE, OffsidePass
from btl.league.league import generate_league
from btl.schema.match import Match
from btl.schema.vocab import ActionType, ConceptId, Result
from btl.sim.engine import simulate_match
from tests.fixtures.concepts import ATTACKER_ID, HOME_WINGER, pass_to


def detect(match: Match) -> tuple[ConceptTag, ...]:
    return OffsidePass().detect(match_context(match))


def test_a_flagged_pass_to_an_attacker_past_the_back_line_is_offside() -> None:
    (tag,) = detect(pass_to((83, 30), result=Result.OFFSIDE))

    assert tag.concept is ConceptId.OFFSIDE
    assert tag.action_id == 0
    assert tag.span == (0, 0)
    assert tag.evidence == {
        "offside": 1.0,
        "margin (m)": 3.0,
        "line (m)": 80.0,
        "player id": float(HOME_WINGER),
    }


def test_a_receiver_behind_the_back_line_is_onside() -> None:
    (tag,) = detect(pass_to((77, 30)))

    assert tag.span == (0, 1)
    assert tag.evidence["offside"] == 0.0
    assert tag.evidence["margin (m)"] == 3.0


def test_level_is_onside_and_the_hardest_call() -> None:
    (tag,) = detect(pass_to((80, 30)))

    assert tag.evidence["offside"] == 0.0
    assert tag.difficulty == HARDEST


def test_a_clear_margin_is_the_easiest_call() -> None:
    (tag,) = detect(pass_to((80 - CLEAR, 30)))

    assert tag.difficulty == EASIEST


def test_a_receiver_behind_the_ball_is_onside_even_past_the_defenders() -> None:
    (tag,) = detect(pass_to((85, 30), start=(88, 34), end=(95, 30)))

    assert tag.evidence["line (m)"] == 88.0
    assert tag.evidence["offside"] == 0.0


def test_a_receiver_in_their_own_half_is_onside_even_past_the_defenders() -> None:
    high_line = ((104, 34), (50, 15), (50, 28), (50, 40), (50, 53))

    (tag,) = detect(pass_to((52, 30), start=(40, 34), end=(60, 30), defence=high_line))

    assert tag.evidence["line (m)"] == 52.5
    assert tag.evidence["offside"] == 0.0


def test_a_receiver_far_from_the_line_is_not_worth_asking_about() -> None:
    assert detect(pass_to((80 - NEAR_LINE - 1, 30))) == ()


def test_a_throw_in_cannot_be_offside() -> None:
    assert detect(pass_to((83, 30), action=ActionType.THROW_IN)) == ()


def test_a_flagged_pass_goes_to_the_offside_attacker_nearest_its_end() -> None:
    match = pass_to((82, 50), end=(92, 31), result=Result.OFFSIDE, other_attacker=(84, 30))

    (tag,) = detect(match)

    assert tag.evidence["player id"] == float(ATTACKER_ID)
    assert tag.evidence["margin (m)"] == 4.0


def check_detector_agrees_with_the_flag(seeds: range) -> None:
    home, away = generate_league(np.random.default_rng(0)).clubs[:2]
    flagged = 0
    for seed in seeds:
        match = simulate_match(home, away, seed)
        tags = {tag.action_id: tag for tag in detect(match)}
        for event, after in pairwise(match.events):
            if event.action_type is not ActionType.PASS:
                continue
            tag = tags.get(event.action_id)
            if event.result is Result.OFFSIDE:
                flagged += 1
                assert tag is not None and tag.evidence["offside"] == 1.0
            elif tag is not None:
                assert tag.evidence["offside"] == 0.0
                assert after.team_id == event.team_id
    assert flagged > 0


def test_the_detector_agrees_with_the_referee_on_every_flag() -> None:
    check_detector_agrees_with_the_flag(range(10, 30))


@pytest.mark.slow
def test_the_detector_agrees_with_the_referee_over_many_matches() -> None:
    check_detector_agrees_with_the_flag(range(200))
