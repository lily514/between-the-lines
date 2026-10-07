"""Band tests: simulated matches look like real football in a few headline numbers.

These are the definition of done for calibrating ``SimParams``: once they pass, stop tuning.
Each band must hold on average over the seeds, and for most single matches.
"""

from collections.abc import Callable
from functools import cache
from statistics import mean

import numpy as np
import pytest

from btl.league.league import generate_league, season_fixtures
from btl.sim.engine import simulate_match
from btl.sim.stats import MatchStats, match_stats

SEEDS = range(50)
SINGLE_MATCH_SHARE = 0.9
# A long throw is one of 20 m or more. The longest in real matches are in the low 30s of metres;
# 40 m leaves room for a failed throw that runs on out of play.
LONG_THROW = 20.0
LONGEST_THROW = 40.0


@cache
def all_stats() -> tuple[MatchStats, ...]:
    league = generate_league(np.random.default_rng(0))
    fixtures = season_fixtures(league)
    return tuple(
        match_stats(
            simulate_match(league.club(home), league.club(away), seed, with_snapshots=False)
        )
        for seed, (home, away) in zip(SEEDS, fixtures, strict=False)
    )


MEASURES: dict[str, Callable[[MatchStats], float]] = {
    "passes": lambda stats: stats.passes,
    "pass completion": lambda stats: stats.pass_completion,
    "shots": lambda stats: stats.shots,
}


@pytest.mark.parametrize(
    ("name", "low", "high"),
    [("passes", 700, 1100), ("pass completion", 0.70, 0.88), ("shots", 15, 35)],
)
def test_matches_fall_in_the_band(name: str, low: float, high: float) -> None:
    values = [MEASURES[name](stats) for stats in all_stats()]

    assert low <= mean(values) <= high
    in_band = sum(low <= value <= high for value in values)
    assert in_band >= SINGLE_MATCH_SHARE * len(values)


def test_mean_goals_fall_in_the_band() -> None:
    assert 1.5 <= mean(stats.goals for stats in all_stats()) <= 4


def test_every_kind_of_restart_happens() -> None:
    stats = all_stats()

    assert all(each.throw_ins > 0 and each.goal_kicks > 0 for each in stats)
    assert sum(each.corners for each in stats) > 0


def test_throw_ins_are_mostly_short_with_a_few_long_ones() -> None:
    lengths = [length for stats in all_stats() for length in stats.throw_in_lengths]

    assert 8 <= mean(lengths) <= 20
    assert 0.02 <= sum(length >= LONG_THROW for length in lengths) / len(lengths) <= 0.15
    assert max(lengths) <= LONGEST_THROW
