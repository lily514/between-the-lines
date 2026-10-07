# pyright: basic
# pandas and socceraction are only partially typed; see CLAUDE.md on edge modules.
"""Expected Threat: how likely a team is to score soon with the ball in each part of the pitch.

A thin layer over socceraction's ``ExpectedThreat``. The pitch is split into a grid of cells,
16 along it and 12 across, and each cell's value is learned from matches with every action seen
as if its team attacks towards x = 105. A successful pass, cross or dribble is worth the value
where it ends minus the value where it starts. Every other action, restarts included, gets no
value.
"""

import contextlib
import io
from collections.abc import Iterable, Iterator
from dataclasses import dataclass

import numpy as np
import pandas as pd
from pandera.typing import DataFrame
from socceraction.spadl import SPADLSchema
from socceraction.xthreat import ExpectedThreat

from btl.league.league import League, season_fixtures
from btl.schema.frames import to_spadl_frame
from btl.schema.ids import GameId
from btl.schema.match import Match
from btl.sim.engine import simulate_match
from btl.sim.pitch import PITCH_LENGTH, PITCH_WIDTH

CELLS_ALONG = 16
CELLS_ACROSS = 12

Grid = tuple[tuple[float, ...], ...]


@dataclass(frozen=True, slots=True)
class FitInfo:
    """What a model was fitted on: enough to fit it again exactly."""

    matches: int
    seed: int
    league_seed: int
    actions: int


@dataclass(frozen=True, slots=True)
class ThreatModel:
    """A fitted Expected Threat grid.

    ``grid[row][column]`` is the chance of scoring soon with the ball in that cell, for a team
    attacking towards x = 105. Columns run along the pitch from x = 0. Rows run across it from
    the top touchline (y = 68) down, which is socceraction's layout.
    """

    grid: Grid
    fitted_on: FitInfo

    def value_at(self, x: float, y: float) -> float:
        """The grid value at a point, for a team attacking towards x = 105."""
        column = min(int(x / PITCH_LENGTH * CELLS_ALONG), CELLS_ALONG - 1)
        from_bottom = min(int(y / PITCH_WIDTH * CELLS_ACROSS), CELLS_ACROSS - 1)
        return self.grid[CELLS_ACROSS - 1 - from_bottom][column]


def fit_grid(matches: Iterable[Match]) -> tuple[Grid, int]:
    """Learn the grid from matches.

    Returns:
        The grid, and how many actions it was learned from.
    """
    actions = DataFrame[SPADLSchema](
        pd.concat(
            [to_spadl_frame(match, left_to_right=True) for match in matches], ignore_index=True
        )
    )
    # socceraction prints its iteration count; keep it out of the CLI's output.
    with contextlib.redirect_stdout(io.StringIO()):
        model = ExpectedThreat(l=CELLS_ALONG, w=CELLS_ACROSS).fit(actions)
    grid = tuple(tuple(float(value) for value in row) for row in model.xT)
    return grid, len(actions)


def training_matches(league: League, n_matches: int, seed: int) -> Iterator[Match]:
    """Simulated matches to fit on: the season's fixtures in order, each with its own seed.

    Snapshots are skipped; fitting never reads them.
    """
    fixtures = season_fixtures(league)
    match_seeds = np.random.default_rng(seed).integers(0, 2**31, size=n_matches)
    for index, match_seed in enumerate(match_seeds):
        home, away = fixtures[index % len(fixtures)]
        yield simulate_match(
            league.club(home),
            league.club(away),
            int(match_seed),
            game_id=GameId(index),
            with_snapshots=False,
        )


def fit_on_simulated_matches(
    league: League, league_seed: int, n_matches: int, seed: int
) -> ThreatModel:
    """Simulate matches in ``league`` and fit a model on them.

    The same arguments always give the same model.
    """
    grid, n_actions = fit_grid(training_matches(league, n_matches, seed))
    return ThreatModel(grid, FitInfo(n_matches, seed, league_seed, n_actions))


def rate_match(model: ThreatModel, match: Match) -> tuple[float | None, ...]:
    """The threat each event adds, in event order; ``None`` for events with no value."""
    if not match.events:
        return ()
    rater = ExpectedThreat(l=CELLS_ALONG, w=CELLS_ACROSS)
    rater.xT = np.array(model.grid)
    ratings = rater.rate(DataFrame[SPADLSchema](to_spadl_frame(match, left_to_right=True)))
    return tuple(None if np.isnan(rating) else float(rating) for rating in ratings)
