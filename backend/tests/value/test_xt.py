from collections.abc import Callable
from functools import cache

import numpy as np
import pytest

from btl.league.league import League, generate_league
from btl.sim.pitch import PITCH_LENGTH, PITCH_WIDTH
from btl.value.xt import (
    CELLS_ACROSS,
    CELLS_ALONG,
    FitInfo,
    ThreatModel,
    fit_on_simulated_matches,
    rate_match,
)
from tests.fixtures.matches import six_event_match

NO_FIT = FitInfo(matches=0, seed=0, league_seed=0, actions=0)


def grid_of(value: Callable[[int, int], float]) -> ThreatModel:
    """A hand-made model whose cell (row, column) holds ``value(row, column)``."""
    return ThreatModel(
        tuple(
            tuple(float(value(row, column)) for column in range(CELLS_ALONG))
            for row in range(CELLS_ACROSS)
        ),
        NO_FIT,
    )


RISING_TOWARDS_GOAL = grid_of(lambda row, column: column / 100)


@cache
def league() -> League:
    return generate_league(np.random.default_rng(0))


@cache
def fitted(n_matches: int) -> ThreatModel:
    return fit_on_simulated_matches(league(), 0, n_matches, seed=0)


def mean_over_third(model: ThreatModel, third: int) -> float:
    """Mean value over the cells whose centres are in a third: 0 own, 2 final."""
    values = [
        model.value_at(
            (column + 0.5) * PITCH_LENGTH / CELLS_ALONG, (row + 0.5) * PITCH_WIDTH / CELLS_ACROSS
        )
        for row in range(CELLS_ACROSS)
        for column in range(CELLS_ALONG)
        if int((column + 0.5) / CELLS_ALONG * 3) == third
    ]
    return sum(values) / len(values)


def test_value_at_finds_the_cell_with_the_top_touchline_in_row_zero() -> None:
    by_row = grid_of(lambda row, column: row)

    assert by_row.value_at(50, PITCH_WIDTH) == 0
    assert by_row.value_at(50, 0) == CELLS_ACROSS - 1
    assert RISING_TOWARDS_GOAL.value_at(0, 34) == 0
    assert RISING_TOWARDS_GOAL.value_at(PITCH_LENGTH, 34) == pytest.approx(0.15)


def test_only_successful_passes_crosses_and_dribbles_are_rated() -> None:
    ratings = rate_match(RISING_TOWARDS_GOAL, six_event_match())

    assert [rating is not None for rating in ratings] == [True, True, False, False, False, True]


def test_forward_moves_add_threat_for_both_teams() -> None:
    # Home attacks towards x = 105 and away towards x = 0, so both of these move forwards:
    # home's pass from x = 40 to 60 (column 6 to 9), and away's from x = 75 to 50 (seen
    # left to right, x = 30 to 55: column 4 to 8).
    ratings = rate_match(RISING_TOWARDS_GOAL, six_event_match())

    assert ratings[0] == pytest.approx(0.03)
    assert ratings[5] == pytest.approx(0.04)


def test_fitting_again_with_the_same_seeds_gives_the_same_model() -> None:
    again = fit_on_simulated_matches(league(), 0, 20, seed=0)

    assert again == fitted(20)
    assert fit_on_simulated_matches(league(), 0, 20, seed=1) != fitted(20)


def test_the_model_records_what_it_was_fitted_on() -> None:
    model = fitted(20)

    assert (model.fitted_on.matches, model.fitted_on.seed, model.fitted_on.league_seed) == (
        20,
        0,
        0,
    )
    assert model.fitted_on.actions > 20 * 1000
    assert len(model.grid) == CELLS_ACROSS
    assert all(len(row) == CELLS_ALONG for row in model.grid)


def test_threat_is_higher_in_the_final_third_than_in_your_own() -> None:
    model = fitted(20)

    assert mean_over_third(model, 2) > mean_over_third(model, 0)


@pytest.mark.slow
def test_a_full_fit_rises_towards_goal_and_peaks_in_front_of_it() -> None:
    model = fitted(200)

    assert mean_over_third(model, 0) < mean_over_third(model, 1) < mean_over_third(model, 2)
    highest = max(max(row) for row in model.grid)
    assert highest in (model.value_at(100, 34), model.value_at(100, 30), model.value_at(100, 38))
