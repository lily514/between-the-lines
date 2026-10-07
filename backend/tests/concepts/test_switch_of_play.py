from functools import cache

import numpy as np
import pytest

from btl.concepts.base import ConceptId, match_context
from btl.concepts.switch_of_play import FLANK_WIDTH, SwitchOfPlay
from btl.league.league import generate_league
from btl.schema import PITCH_WIDTH
from btl.schema.match import Match
from btl.schema.vocab import ActionType, Result
from btl.sim.engine import simulate_match
from tests.fixtures.concepts import switches_match


@cache
def simulated(seed: int) -> Match:
    home, away = generate_league(np.random.default_rng(0)).clubs[:2]
    return simulate_match(home, away, seed, with_snapshots=False)


def test_finds_a_switch_by_each_team_and_nothing_that_nearly_qualifies() -> None:
    tags = SwitchOfPlay().detect(match_context(switches_match()))

    assert [tag.action_id for tag in tags] == [0, 6]
    assert all(tag.concept is ConceptId.SWITCH_OF_PLAY for tag in tags)
    assert [tag.span for tag in tags] == [(0, 0), (6, 6)]
    assert [tag.evidence["across (m)"] for tag in tags] == [45.0, 52.0]


def test_the_distance_across_is_a_setting() -> None:
    tags = SwitchOfPlay(min_across=50).detect(match_context(switches_match()))

    assert [tag.action_id for tag in tags] == [6]


@pytest.mark.parametrize("seed", range(3))
def test_in_simulated_play_it_finds_exactly_the_passes_that_fit_the_rule(seed: int) -> None:
    # The rule restated in stored coordinates. Distance across and "far flank" don't depend on
    # which way a team attacks, so the detector, which sees play left to right, must agree.
    played = simulated(seed)

    found = {tag.action_id for tag in SwitchOfPlay().detect(match_context(played))}

    expected = {
        event.action_id
        for event in played.events
        if event.action_type in (ActionType.PASS, ActionType.CROSS)
        and event.result is Result.SUCCESS
        and abs(event.end_y - event.start_y) >= 30
        and min(event.end_y, PITCH_WIDTH - event.end_y) <= FLANK_WIDTH
        and (event.end_y > PITCH_WIDTH / 2) != (event.start_y > PITCH_WIDTH / 2)
    }
    assert found == expected
    assert found
