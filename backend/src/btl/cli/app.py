"""The `btl` command and its subcommands."""

from pathlib import Path
from typing import Annotated

import numpy as np
import typer
from rich.console import Console

from btl.cli.render import events_table, scoreline
from btl.io import MatchInfo, load_match, save_match
from btl.league.league import Club, League, generate_league, season_fixtures
from btl.sim.engine import simulate_match
from btl.sim.shape import FOUR_FOUR_TWO

app = typer.Typer(
    name="btl",
    help="Generate synthetic football matches and inspect their events, values, and concept tags.",
    no_args_is_help=True,
)
console = Console()


@app.callback()
def main() -> None:
    """Between the Lines data engine."""


def _league(league_seed: int) -> League:
    return generate_league(np.random.default_rng(league_seed))


def _club(league: League, short_name: str) -> Club:
    for club in league.clubs:
        if club.short_name == short_name.upper():
            return club
    known = ", ".join(club.short_name for club in league.clubs)
    raise typer.BadParameter(f"no club {short_name!r}; the clubs are {known}")


@app.command()
def simulate(
    seed: Annotated[int, typer.Option(help="The same seed always gives the same match.")],
    out: Annotated[Path, typer.Option(help="Folder to save the match in.")] = Path("data/matches"),
    league_seed: Annotated[int, typer.Option(help="Which fictional league to use.")] = 0,
    home: Annotated[str | None, typer.Option(help="Home club's short name, e.g. KEN.")] = None,
    away: Annotated[str | None, typer.Option(help="Away club's short name.")] = None,
) -> None:
    """Simulate a match and save it.

    Without --home and --away, the clubs come from the league's season fixtures, picked by seed.
    """
    league = _league(league_seed)
    if (home is None) != (away is None):
        raise typer.BadParameter("give both --home and --away, or neither")
    if home is not None and away is not None:
        home_club, away_club = _club(league, home), _club(league, away)
    else:
        fixtures = season_fixtures(league)
        home_id, away_id = fixtures[seed % len(fixtures)]
        home_club, away_club = league.club(home_id), league.club(away_id)
    if home_club == away_club:
        raise typer.BadParameter(f"{home_club.name} can't play itself")

    match = simulate_match(home_club, away_club, seed)
    info = MatchInfo(
        seed=seed,
        league_seed=league_seed,
        home_formation=FOUR_FOUR_TWO.name,
        away_formation=FOUR_FOUR_TWO.name,
    )
    directory = save_match(match, info, out)
    console.print(scoreline(match, league))
    console.print(f"{len(match.events):,} events · seed {seed} · saved to {directory}")


@app.command()
def events(
    match_dir: Annotated[Path, typer.Argument(help="A folder saved by `btl simulate`.")],
    start: Annotated[int, typer.Option(help="First event to show.", min=0)] = 0,
    count: Annotated[int, typer.Option(help="How many events to show.", min=1)] = 50,
) -> None:
    """Show a saved match's events as a table."""
    try:
        match, info = load_match(match_dir)
    except FileNotFoundError:
        raise typer.BadParameter(f"no saved match in {match_dir}") from None
    league = _league(info.league_seed)
    total = len(match.events)
    shown = min(count, max(total - start, 0))

    console.print(scoreline(match, league))
    console.print(events_table(match, league, start, count))
    console.print(
        f"Events {start} to {start + shown - 1} of {total:,}. Use --start and --count for others."
        if shown
        else f"No events from {start}; the match has {total:,}."
    )
