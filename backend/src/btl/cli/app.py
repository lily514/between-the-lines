"""The `btl` command and its subcommands."""

from collections import Counter
from pathlib import Path
from typing import Annotated

import numpy as np
import typer
from rich.console import Console

from btl.cli.render import (
    events_table,
    match_clock,
    pitch_picture,
    scoreline,
    tags_table,
    threat_grid,
)
from btl.concepts.base import match_context
from btl.concepts.registry import detect_all
from btl.io import MatchInfo, load_match, load_threat_model, save_match, save_threat_model
from btl.league.league import Club, League, generate_league, season_fixtures
from btl.plant.planter import simulate_with_moments
from btl.plant.spec import parse_plant
from btl.schema.ids import ActionId
from btl.schema.match import Match
from btl.schema.vocab import ConceptId
from btl.sim.engine import simulate_match
from btl.sim.shape import FOUR_FOUR_TWO
from btl.value.xt import fit_on_simulated_matches, rate_match

app = typer.Typer(
    name="btl",
    help="Generate synthetic football matches and inspect their events, values, and concept tags.",
    no_args_is_help=True,
)
console = Console()
DEFAULT_MODEL = Path("data/models/expected-threat.json")


@app.callback()
def main() -> None:
    """Between the Lines data engine."""


def _league(league_seed: int) -> League:
    return generate_league(np.random.default_rng(league_seed))


def _load(match_dir: Path) -> tuple[Match, MatchInfo]:
    try:
        return load_match(match_dir)
    except FileNotFoundError:
        raise typer.BadParameter(f"no saved match in {match_dir}") from None


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
    plant: Annotated[
        list[str] | None,
        typer.Option(
            help="Teachable moments to plant, as concept:levels, e.g. line_breaking_pass:1,2,3."
            " Repeat for more concepts."
        ),
    ] = None,
) -> None:
    """Simulate a match and save it.

    Without --home and --away, the clubs come from the league's season fixtures, picked by seed.
    Planted moments happen easiest first.
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

    if plant:
        try:
            request = parse_plant(plant)
            match = simulate_with_moments(home_club, away_club, seed, request)
        except ValueError as error:
            raise typer.BadParameter(str(error), param_hint="--plant") from None
    else:
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
    if match.planted:
        console.print(
            f"{len(match.planted)} planted moments; `btl moments {directory}` shows them."
        )


@app.command()
def events(
    match_dir: Annotated[Path, typer.Argument(help="A folder saved by `btl simulate`.")],
    start: Annotated[int, typer.Option(help="First event to show.", min=0)] = 0,
    count: Annotated[int, typer.Option(help="How many events to show.", min=1)] = 50,
    model: Annotated[
        Path, typer.Option(help="Expected Threat model from `btl fit-xt`, for the threat column.")
    ] = DEFAULT_MODEL,
) -> None:
    """Show a saved match's events as a table, with threat values once a model is fitted."""
    match, info = _load(match_dir)
    league = _league(info.league_seed)
    total = len(match.events)
    shown = min(count, max(total - start, 0))

    threat = rate_match(load_threat_model(model), match) if model.exists() else None

    console.print(scoreline(match, league))
    console.print(events_table(match, league, start, count, threat))
    console.print(
        f"Events {start} to {start + shown - 1} of {total:,}. Use --start and --count for others."
        if shown
        else f"No events from {start}; the match has {total:,}."
    )
    if threat is None:
        console.print(f"No threat model at {model}; run `btl fit-xt` to add a threat column.")


@app.command()
def tags(
    match_dir: Annotated[Path, typer.Argument(help="A folder saved by `btl simulate`.")],
    concept: Annotated[
        ConceptId | None, typer.Option(help="Show only this concept.", case_sensitive=False)
    ] = None,
) -> None:
    """List the football concepts the detectors find in a saved match."""
    match, info = _load(match_dir)
    league = _league(info.league_seed)
    found = detect_all(match_context(match))
    if concept is not None:
        found = tuple(tag for tag in found if tag.concept is concept)

    console.print(scoreline(match, league))
    console.print(tags_table(match, league, found))
    counts = Counter(tag.concept for tag in found)
    summary = ", ".join(f"{count} {concept.label}" for concept, count in sorted(counts.items()))
    console.print(f"{len(found)} tags" + (f": {summary}" if summary else ""))


@app.command()
def moments(
    match_dir: Annotated[Path, typer.Argument(help="A folder saved by `btl simulate --plant`.")],
) -> None:
    """Show a saved match's planted moments: the play leading up to each, and the pitch at it."""
    match, info = _load(match_dir)
    league = _league(info.league_seed)
    console.print(scoreline(match, league))
    if not match.planted:
        console.print("No planted moments. Plant some with `btl simulate --plant`.")
        return
    ctx = match_context(match)
    found = {(tag.concept, tag.action_id): tag for tag in detect_all(ctx)}
    for number, moment in enumerate(match.planted, start=1):
        answer = match.events[moment.answer_action_id]
        first = next(
            event.action_id for event in match.events if event.planted_moment_id == number - 1
        )
        console.rule(
            f"Moment {number} · {moment.concept.label} · level {moment.difficulty}"
            f" · {match_clock(answer)}"
        )
        console.print(events_table(match, league, first, moment.answer_action_id - first + 1))
        paused_at = ActionId(moment.pause_action_id + 1)
        console.print(
            f"Play pauses after #{moment.pause_action_id}; the pitch at #{paused_at},"
            f" attacking left to right. The answer is #{moment.answer_action_id}."
        )
        console.print(pitch_picture(ctx.match, paused_at))
        tag = found.get((moment.concept, moment.answer_action_id))
        if tag is None:
            console.print("Not found by the detector.")
            continue
        details = [f"difficulty {tag.difficulty}"] if tag.difficulty is not None else []
        details += [f"{name} {value:g}" for name, value in tag.evidence.items()]
        console.print(f"Detector: {tag.concept.label} · " + " · ".join(details))


@app.command("fit-xt")
def fit_xt(
    matches: Annotated[int, typer.Option(help="How many matches to simulate.", min=1)] = 200,
    seed: Annotated[int, typer.Option(help="The same seed always gives the same model.")] = 0,
    league_seed: Annotated[int, typer.Option(help="Which fictional league to use.")] = 0,
    out: Annotated[Path, typer.Option(help="File to save the model in.")] = DEFAULT_MODEL,
) -> None:
    """Simulate matches and learn the Expected Threat grid from them."""
    with console.status(f"Simulating {matches:,} matches and fitting the grid…"):
        fitted = fit_on_simulated_matches(_league(league_seed), league_seed, matches, seed)
    save_threat_model(fitted, out)
    console.print("Chance of scoring soon from each cell (%), attacking left to right:")
    console.print(threat_grid(fitted))
    console.print(
        f"Fitted on {matches:,} matches ({fitted.fitted_on.actions:,} actions) · seed {seed}"
        f" · saved to {out}"
    )
