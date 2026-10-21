"""The `btl` command and its subcommands."""

import json
import time
from collections import Counter
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import numpy as np
import typer
import uvicorn
from rich.console import Console
from rich.live import Live
from rich.rule import Rule
from rich.text import Text

from btl.api.app import create_app
from btl.cli.render import (
    counted,
    events_table,
    match_clock,
    matches_table,
    pitch_picture,
    replay_picture,
    scoreline,
    summary_table,
    tags_table,
    threat_grid,
)
from btl.cli.viewer import (
    TerminalViewer,
    progress_bars,
    show_feedback,
    show_match_start,
    show_question,
)
from btl.concepts.base import ConceptTag, match_context
from btl.concepts.registry import detect_all
from btl.io import (
    MatchInfo,
    load_match,
    load_threat_model,
    save_match,
    save_threat_model,
    saved_match_directories,
)
from btl.league.league import Club, League, generate_league, season_fixtures
from btl.learn.learner import MATCHES_PER_SESSION
from btl.learn.session import (
    LEAGUE_SEED,
    Asked,
    ClubLockedError,
    Course,
    DemoViewer,
    PreparedMatch,
    choose_club,
    prepare_match,
    seed_for_viewer,
    start_session,
    watch_match,
)
from btl.learn.team_sheet import viewer_sheet
from btl.plant.planter import simulate_with_moments
from btl.plant.spec import parse_plant
from btl.replay import DEFAULT_FPS, answer_frames, frame_at, lead_up_frames, question_action
from btl.schema.event import Event
from btl.schema.frames import seen_by
from btl.schema.ids import ActionId, TeamId
from btl.schema.match import Match
from btl.schema.moment import PlantedMoment
from btl.schema.vocab import ConceptId
from btl.sim.engine import simulate_match
from btl.sim.shape import FOUR_FOUR_TWO
from btl.store.base import Stored, check_viewer_id
from btl.store.json_files import JsonLearnerStore
from btl.store.memory import MemoryLearnerStore
from btl.tutor.templates import TemplateTutor
from btl.value.xt import ThreatModel, fit_on_simulated_matches, rate_match

EXAMPLES = (
    ("btl simulate --seed 7 --plant counter_press:1", "saves data/matches/match-0007"),
    ("btl matches", "lists the saved matches"),
    ("btl inspect data/matches/match-0007", "events, tags, moments too"),
    ("btl moments examples/match-0007", "the sample match in the repo"),
    ("btl replay examples/match-0007 --moment 3", "watch a moment play out"),
    ("btl learn --viewer lily", "watch your next match and answer questions"),
    ("btl demo-viewer", "a scripted viewer improving over three matches"),
    ("btl serve", "the learning loop in the browser"),
)


def _examples_help() -> str:
    # Rich joins single line breaks, so each example is its own paragraph.
    width = max(len(command) for command, _ in EXAMPLES)
    lines = [f"{command.ljust(width)}   [dim]{note}[/dim]" for command, note in EXAMPLES]
    return "\n\n".join(["[bold]Examples[/bold]", *lines])


app = typer.Typer(
    name="btl",
    help="Generate synthetic football matches and inspect their events, values, and concept tags.",
    epilog=_examples_help(),
    rich_markup_mode="rich",
    no_args_is_help=True,
)
console = Console()
DEFAULT_MODEL = Path("data/models/expected-threat.json")
DEFAULT_MATCHES = Path("data/matches")
DEFAULT_LEARNERS = Path("data/learners")
DEFAULT_FRONTEND = Path("../frontend/dist")
DEFAULT_PORT = 8000
ModelPath = Annotated[
    Path,
    typer.Option(
        "--model",
        help="The threat model file; fitted on 200 simulated matches and saved if missing.",
    ),
]
MatchDir = Annotated[
    Path,
    typer.Argument(
        metavar="MATCH",
        help="A saved match's folder, e.g. examples/match-0007 or data/matches/match-0007."
        " `btl matches` lists the saved ones.",
        show_default=False,
    ),
]


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
    out: Annotated[Path, typer.Option(help="Folder to save the match in.")] = DEFAULT_MATCHES,
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
        except (ValueError, RuntimeError) as error:
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
    console.print(f"{counted(len(match.events), 'event')} · seed {seed} · saved to {directory}")
    if match.planted:
        console.print(
            f"{counted(len(match.planted), 'planted moment')};"
            f" `btl moments {directory}` shows them."
        )


@app.command("matches")
def list_matches(
    folder: Annotated[
        Path, typer.Argument(help="Folder to look in, as given to `btl simulate --out`.")
    ] = DEFAULT_MATCHES,
) -> None:
    """List the matches saved in a folder."""
    saved: list[tuple[Path, Match, MatchInfo, League]] = []
    unreadable: list[str] = []
    for directory in saved_match_directories(folder):
        try:
            match, info = load_match(directory)
        except ValueError as error:
            unreadable.append(str(error))
            continue
        saved.append((directory, match, info, _league(info.league_seed)))
    if not saved and not unreadable:
        console.print(f"No saved matches in {folder}. Make one with `btl simulate`.")
        return
    if saved:
        console.print(matches_table(saved))
    console.print(f"{counted(len(saved), 'match', 'matches')} in {folder}")
    for problem in unreadable:
        console.print(f"{problem}; simulate it again to update it.", style="yellow")


@app.command()
def events(
    match_dir: MatchDir,
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
    console.print(events_table(match, league, match.events[start : start + count], threat))
    console.print(
        f"Events {start} to {start + shown - 1} of {total:,}. Use --start and --count for others."
        if shown
        else f"No events from {start}; the match has {total:,}."
    )
    if threat is None:
        console.print(f"No threat model at {model}; run `btl fit-xt` to add a threat column.")


@app.command()
def tags(
    match_dir: MatchDir,
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
    summary = ", ".join(f"{concept.label} {count}" for concept, count in sorted(counts.items()))
    console.print(counted(len(found), "tag") + (f": {summary}" if summary else ""))


@app.command()
def inspect(
    match_dir: MatchDir,
    start: Annotated[int, typer.Option(help="First event to show.", min=0)] = 0,
    count: Annotated[int, typer.Option(help="How many events to show.", min=1)] = 50,
    concept: Annotated[
        ConceptId | None,
        typer.Option(help="Show only events where this concept happens.", case_sensitive=False),
    ] = None,
    model: Annotated[
        Path, typer.Option(help="Expected Threat model from `btl fit-xt`, for the threat column.")
    ] = DEFAULT_MODEL,
) -> None:
    """Show a saved match's summary, then its events with their threat and concepts."""
    match, info = _load(match_dir)
    league = _league(info.league_seed)
    threat = rate_match(load_threat_model(model), match) if model.exists() else None
    found = detect_all(match_context(match, threat))

    console.print(scoreline(match, league))
    console.print(summary_table(match, league, found, threat))
    if match.planted:
        console.print(f"{counted(len(match.planted), 'planted moment')}; `btl moments` shows them.")

    if concept is None:
        shown = match.events[start : start + count]
    else:
        tagged = sorted({tag.action_id for tag in found if tag.concept is concept})
        shown = [match.events[action] for action in tagged if action >= start][:count]
    console.print(events_table(match, league, shown, threat, found))
    if not shown:
        console.print(f"No events to show from #{start}.")
    elif concept is None:
        console.print(
            f"Events {start} to {shown[-1].action_id} of {len(match.events):,}."
            " Use --start and --count for others, or --concept to pick out one concept."
        )
    else:
        console.print(
            f"{counted(len(shown), f'{concept.label} event')} from #{start}. Use --count for more."
        )
    if threat is None:
        console.print(f"No threat model at {model}; run `btl fit-xt` to add a threat column.")


@app.command()
def moments(
    match_dir: MatchDir,
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
        _moment_rule(number, moment, answer)
        lead_up = match.events[first : moment.answer_action_id + 1]
        console.print(events_table(match, league, lead_up))
        paused_at = ActionId(moment.pause_action_id + 1)
        console.print(
            f"Play pauses after #{moment.pause_action_id}; the pitch at #{paused_at},"
            f" attacking left to right. The answer is #{moment.answer_action_id}."
        )
        console.print(pitch_picture(ctx.match, paused_at))
        console.print(_detector_line(found.get((moment.concept, moment.answer_action_id))))


def _moment_rule(number: int, moment: PlantedMoment, answer: Event) -> None:
    console.rule(
        f"Moment {number} · {moment.concept.label} · level {moment.difficulty}"
        f" · {match_clock(answer)}"
    )


def _detector_line(tag: ConceptTag | None) -> str:
    if tag is None:
        return "Not found by the detector."
    details = [f"difficulty {tag.difficulty}"] if tag.difficulty is not None else []
    details += [f"{name} {value:g}" for name, value in tag.evidence.items()]
    return f"Detector: {tag.concept.label} · " + " · ".join(details)


@app.command()
def replay(
    match_dir: MatchDir,
    moment: Annotated[
        int, typer.Option(help="Which planted moment, numbered as in `btl moments`.", min=1)
    ],
    seconds: Annotated[
        float, typer.Option(help="How many seconds of play to show before it.", min=1)
    ] = 15.0,
    speed: Annotated[float, typer.Option(help="2 plays twice as fast.", min=0.1)] = 1.0,
    reveal: Annotated[
        bool, typer.Option(help="After the pause, wait for Enter and play the answer.")
    ] = True,
) -> None:
    """Play the seconds before a planted moment on the pitch, pause on it, then show the answer.

    The team on the ball at the pause attacks left to right throughout. When the output isn't a
    terminal, it shows only the picture at the pause.
    """
    match, info = _load(match_dir)
    league = _league(info.league_seed)
    if moment > len(match.planted):
        raise typer.BadParameter(
            f"the match has {counted(len(match.planted), 'planted moment')}",
            param_hint="--moment",
        )
    if match.positions is None:
        raise typer.BadParameter("the match has no player positions to replay")
    planted = match.planted[moment - 1]
    question = question_action(planted)
    team = match.events[question].team_id
    seen = seen_by(match, team)
    animate = console.is_terminal

    console.print(scoreline(match, league))
    _moment_rule(moment, planted, match.events[planted.answer_action_id])
    lead_up = lead_up_frames(seen, planted, seconds=seconds)
    pictures = [replay_picture(seen, frame, team) for frame in lead_up]
    if animate:
        _play(pictures, speed)
    else:
        console.print(pictures[-1])
    console.print(f"Play pauses after #{planted.pause_action_id}. What happens next?")
    if not (reveal and animate):
        return

    console.input("Press Enter to see.")
    answer = planted.answer_action_id
    pictures = [replay_picture(seen, frame, team) for frame in answer_frames(seen, planted)]
    pictures.append(replay_picture(seen, frame_at(seen, answer), team, show_target=True))
    _play(pictures, speed)
    console.print(f"The answer is #{answer}:")
    console.print(events_table(match, league, match.events[question : answer + 1]))
    found = {(tag.concept, tag.action_id): tag for tag in detect_all(match_context(match))}
    console.print(_detector_line(found.get((planted.concept, answer))))


def _play(pictures: Sequence[Text], speed: float) -> None:
    with Live(console=console, auto_refresh=False) as live:
        for index, picture in enumerate(pictures):
            live.update(picture, refresh=True)
            if index < len(pictures) - 1:
                time.sleep(1 / (DEFAULT_FPS * speed))


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


def _threat_model_or_fit(path: Path) -> ThreatModel:
    if path.exists():
        return load_threat_model(path)
    with console.status("No threat model yet: simulating 200 matches and fitting one…"):
        fitted = fit_on_simulated_matches(_league(LEAGUE_SEED), LEAGUE_SEED, 200, 0)
    save_threat_model(fitted, path)
    console.print(f"Saved the threat model to {path}.")
    return fitted


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


@app.command()
def learn(
    viewer: Annotated[str, typer.Option(help="Your viewer name: lower-case letters and digits.")],
    seed: Annotated[
        int | None, typer.Option(help="Which three matches; by default chosen from your name.")
    ] = None,
    learners: Annotated[Path, typer.Option(help="Folder for learner records.")] = DEFAULT_LEARNERS,
    model: ModelPath = DEFAULT_MODEL,
    reset: Annotated[bool, typer.Option(help="Forget this viewer and start again.")] = False,
    club: Annotated[
        str | None,
        typer.Option(help='The team you support, e.g. "HEX"; your matches are its fixtures.'),
    ] = None,
) -> None:
    """Watch your next match. Play pauses for questions; your answers shape the next ones.

    Each run plays one match of three. Quit at any time with Ctrl+C: answers are saved as you
    go, and the next run carries on where you stopped.
    """
    try:
        check_viewer_id(viewer)
    except ValueError as error:
        raise typer.BadParameter(str(error), param_hint="--viewer") from None
    store = JsonLearnerStore(learners)
    if reset:
        (learners / f"{viewer}.json").unlink(missing_ok=True)
    stored = start_session(store, viewer, seed_for_viewer(viewer) if seed is None else seed)
    course = Course(_threat_model_or_fit(model), TemplateTutor())
    if club is not None:
        stored = _choose_club(course, store, viewer, club)
    if stored.state.club is not None:
        console.print(f"Your team: {course.league.club(stored.state.club).name}")
    if stored.state.finished:
        console.print(f"{viewer} has watched all three matches. `--reset` starts again.")
        console.print(progress_bars(course.bars(stored.state)))
        return
    state = stored.state
    current = state.match_number
    prepared = prepare_match(course, state.seed, current, state.club)

    def prepare(seed: int, match_number: int, club: TeamId | None) -> PreparedMatch:
        if match_number == current:
            return prepared
        return prepare_match(course, seed, match_number, club)

    sheet = viewer_sheet(course, state, prepare)
    terminal = TerminalViewer(console, lambda prompt: typer.prompt(prompt), sheet)

    state = watch_match(course, store, viewer, terminal, _now, prepare)
    if state.finished:
        console.print("That was your last match. `--reset` starts again.")
    else:
        console.print(f"Run `btl learn --viewer {viewer}` again for match {state.match_number}.")


def _choose_club(course: Course, store: JsonLearnerStore, viewer: str, name: str) -> Stored:
    try:
        team_id = course.league.find_club(name).team_id
    except KeyError:
        codes = ", ".join(club.short_name for club in course.league.clubs)
        raise typer.BadParameter(f"no club called {name!r}; try one of {codes}") from None
    try:
        return choose_club(course, store, viewer, team_id)
    except ClubLockedError:
        raise typer.BadParameter(
            f"{viewer} has started watching, so their team can't change; `--reset` starts again",
            param_hint="--club",
        ) from None


@app.command(name="demo-viewer")
def demo_viewer(
    seed: Annotated[int, typer.Option(help="Which three matches.")] = 7,
    model: ModelPath = DEFAULT_MODEL,
) -> None:
    """A scripted viewer watches three matches and gets better as they go.

    It answers one question in three correctly in the first match, one in two in the second,
    and all of them in the third. Each question shows why it is asked now, the viewer's
    answer, the feedback, and how the progress bars move.
    """
    course = Course(_threat_model_or_fit(model), TemplateTutor())
    store = MemoryLearnerStore()
    start_session(store, "demo", seed)

    def show_answer(asked: Asked, key: str) -> None:
        show_question(console, asked)
        console.print(f"The demo viewer picks [bold]{key}[/bold].")

    viewer = DemoViewer(
        on_begin=lambda start: show_match_start(console, start),
        on_ask=show_answer,
        on_tell=lambda told: show_feedback(console, told),
    )
    for _ in range(MATCHES_PER_SESSION):
        watch_match(course, store, "demo", viewer, lambda: "2026-10-08T12:00:00+00:00")
    console.print(Rule("After three matches"))
    console.print(progress_bars(viewer.seen[-1].mastery))


@app.command()
def serve(
    host: Annotated[str, typer.Option(help="Address to listen on.")] = "127.0.0.1",
    port: Annotated[int, typer.Option(help="Port to listen on.")] = DEFAULT_PORT,
    learners: Annotated[Path, typer.Option(help="Folder for learner records.")] = DEFAULT_LEARNERS,
    model: ModelPath = DEFAULT_MODEL,
    frontend: Annotated[
        Path, typer.Option(help="The built web page, served outside /api if it exists.")
    ] = DEFAULT_FRONTEND,
) -> None:
    """Serve the learning loop to the web page: the API, and the built page if there is one.

    Learner records are the same files `btl learn` uses, so a viewer can carry on in either.
    """
    course = Course(_threat_model_or_fit(model), TemplateTutor())
    page = frontend if (frontend / "index.html").is_file() else None
    if page is None:
        console.print(
            f"No built page in {frontend}: serving the API only. "
            "Build it with `npm run build` in frontend/, or use `npm run dev` there."
        )
    api = create_app(lambda: course, JsonLearnerStore(learners), _now, page)
    console.print(f"Serving on http://{host}:{port} (API under /api). Ctrl+C stops it.")
    uvicorn.run(api, host=host, port=port, log_level="warning")


@app.command()
def openapi(
    out: Annotated[Path | None, typer.Option(help="File to write; printed if not given.")] = None,
) -> None:
    """Write the web API's OpenAPI schema, from which the page's TypeScript types are made."""
    schema = create_app(_no_course, MemoryLearnerStore(), _now).openapi()
    text = json.dumps(schema, indent=2, sort_keys=True) + "\n"
    if out is None:
        typer.echo(text, nl=False)
    else:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text)
        console.print(f"Wrote the OpenAPI schema to {out}.")


def _no_course() -> Course:
    raise RuntimeError("the schema needs no course")
