from functools import cache

import numpy as np
import pytest

from btl.concepts.base import match_context
from btl.concepts.counter_press import CounterPress
from btl.concepts.line_breaking import LineBreakingPass
from btl.league.league import Club, generate_league
from btl.plant import templates
from btl.plant.planter import QUIET_END, QUIET_START, Planter, simulate_with_moments
from btl.plant.spec import MomentSpec, PlantRequest, parse_plant
from btl.schema.match import Match
from btl.schema.vocab import ConceptId
from btl.sim.chain import Start
from btl.sim.engine import simulate_match
from btl.sim.params import DEFAULT_PARAMS
from btl.sim.shape import FOUR_FOUR_TWO, FOUR_THREE_THREE

ONE_TWO_THREE = parse_plant(["line_breaking_pass:1,2,3"])
SEEDS = range(6)


@cache
def clubs() -> tuple[Club, Club]:
    home, away = generate_league(np.random.default_rng(0)).clubs[:2]
    return home, away


@cache
def planted(seed: int) -> Match:
    # Odd seeds face a 4-3-3, whose midfield line has three players rather than four.
    away_formation = FOUR_THREE_THREE if seed % 2 else FOUR_FOUR_TWO
    return simulate_with_moments(*clubs(), seed, ONE_TWO_THREE, away_formation=away_formation)


@pytest.mark.parametrize("seed", SEEDS)
def test_every_planted_moment_is_found_by_the_detector_in_order_of_difficulty(
    seed: int,
) -> None:
    match = planted(seed)
    found = {tag.action_id: tag for tag in LineBreakingPass().detect(match_context(match))}

    detected: list[float] = []
    for moment in match.planted:
        difficulty = found[moment.answer_action_id].difficulty
        assert difficulty is not None
        detected.append(difficulty)

    assert [moment.difficulty for moment in match.planted] == [1, 2, 3]
    assert detected == sorted(detected) and len(set(detected)) == 3


@pytest.mark.parametrize("seed", SEEDS)
def test_moments_happen_in_order_and_hold_their_own_events(seed: int) -> None:
    match = planted(seed)
    answers = [moment.answer_action_id for moment in match.planted]

    assert answers == sorted(answers)
    for number, moment in enumerate(match.planted):
        marked = [e.action_id for e in match.events if e.planted_moment_id == number]
        assert moment.pause_action_id in marked and marked[-1] == moment.answer_action_id
        assert match.events[moment.answer_action_id].team_id == match.events[marked[0]].team_id


@pytest.mark.parametrize("seed", SEEDS)
def test_every_planted_counter_press_is_found_by_the_detector(seed: int) -> None:
    request = parse_plant(["counter_press:1,2,3", "line_breaking_pass:2"])
    match = simulate_with_moments(*clubs(), seed, request, with_snapshots=False)
    found = {tag.action_id for tag in CounterPress().detect(match_context(match))}

    presses = [m for m in match.planted if m.concept is ConceptId.COUNTER_PRESS]

    assert [moment.difficulty for moment in presses] == [1, 2, 3]
    assert all(moment.answer_action_id in found for moment in presses)
    for number, moment in enumerate(match.planted):
        marked = [e.action_id for e in match.events if e.planted_moment_id == number]
        assert marked[-1] == moment.answer_action_id


def test_play_before_the_first_moment_is_the_unplanted_match() -> None:
    match = planted(0)
    plain = simulate_match(*clubs(), 0)
    first = next(e.action_id for e in match.events if e.planted_moment_id is not None)

    assert match.events[:first] == plain.events[:first]
    assert match.positions is not None and plain.positions is not None
    assert np.array_equal(match.positions.xy[:first], plain.positions.xy[:first])
    assert match.events != plain.events


def test_the_same_seed_plants_the_same_match() -> None:
    again = simulate_with_moments(*clubs(), 0, ONE_TWO_THREE)

    assert again == planted(0)


def test_turning_off_snapshots_keeps_the_same_events() -> None:
    without = simulate_with_moments(*clubs(), 0, ONE_TWO_THREE, with_snapshots=False)

    assert without.positions is None
    assert without.events == planted(0).events
    assert without.planted == planted(0).planted


def test_targets_are_spread_over_both_halves_away_from_the_whistles() -> None:
    targets = Planter(parse_plant(["line_breaking_pass:1,1,2,2"])).targets

    assert [period for period, _ in targets] == [1, 1, 2, 2]
    last_allowed = DEFAULT_PARAMS.period_seconds - QUIET_END
    assert all(QUIET_START <= at <= last_allowed for _, at in targets)


def test_a_concept_without_a_template_cannot_be_planted() -> None:
    with pytest.raises(ValueError, match="can't be planted yet"):
        Planter(PlantRequest((MomentSpec(ConceptId.SWITCH_OF_PLAY, 1),)))


class NeverFits(templates.LineBreakingTemplate):
    def fits(self, start: Start) -> bool:
        return False


def test_says_so_when_a_moment_could_not_be_planted(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(templates.TEMPLATES, ConceptId.LINE_BREAKING_PASS, NeverFits())

    with pytest.raises(RuntimeError, match="0 of 3 moments"):
        simulate_with_moments(*clubs(), 0, ONE_TWO_THREE, with_snapshots=False)
