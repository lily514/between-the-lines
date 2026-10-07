"""Band tests: simulated matches look like real football in a few headline numbers.

These are the definition of done for calibrating ``SimParams``: once they pass, stop tuning.
Each band must hold on average over the seeds, and for most single matches. "Real" figures in
the comments are per-match means over 40 matches of a real top-flight season's event data;
see the implementation notes for the source.
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
LONG_THROW = 20.0
LONGEST_THROW = 45.0


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
    "throw-ins": lambda stats: stats.throw_ins,
    "goal kicks": lambda stats: stats.goal_kicks,
    "share of actions on a touchline": lambda stats: stats.on_touchline / stats.actions,
}


@pytest.mark.parametrize(
    ("name", "low", "high"),
    [
        # Real: 717, completed 79%, from a season when teams passed less than today.
        ("passes", 700, 1100),
        ("pass completion", 0.70, 0.88),
        # Real: 25.
        ("shots", 15, 35),
        # Real: 48; reported elsewhere as about 39 in recent seasons.
        ("throw-ins", 25, 55),
        # Real: 17.
        ("goal kicks", 10, 25),
        # Real: 6%, and 4 to 9% in single matches.
        ("share of actions on a touchline", 0, 0.10),
    ],
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
    # Real successful throws: mean 15.6 m, 24% of 20 m or more, 1 in 100 of 39 m or more.
    lengths = [length for stats in all_stats() for length in stats.throw_in_lengths]

    assert 10 <= mean(lengths) <= 20
    assert 0.15 <= sum(length >= LONG_THROW for length in lengths) / len(lengths) <= 0.35
    assert max(lengths) <= LONGEST_THROW
