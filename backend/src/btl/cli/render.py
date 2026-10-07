"""How the CLI shows things: the scoreline, events, concept tags, threat grid, and the pitch."""

from collections.abc import Sequence

from rich.table import Table
from rich.text import Text

from btl.concepts.base import ConceptTag
from btl.league.league import League
from btl.schema import PITCH_LENGTH, PITCH_WIDTH
from btl.schema.event import Event
from btl.schema.ids import ActionId, TeamId
from btl.schema.match import Match
from btl.schema.vocab import ActionType, Result
from btl.value.xt import ThreatModel

PERIOD_MINUTES = 45
SHOTS = frozenset({ActionType.SHOT, ActionType.SHOT_FREEKICK, ActionType.SHOT_PENALTY})
HOME_STYLE = "cyan"
AWAY_STYLE = "magenta"


def match_clock(event: Event) -> str:
    """Time on the match clock, e.g. ``68:12`` for 23 min 12 s into the second half."""
    seconds = int(event.time_seconds) + (event.period_id - 1) * PERIOD_MINUTES * 60
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def goals(match: Match) -> dict[TeamId, int]:
    """Goals per team, counting own goals for the other team."""
    home, away = match.home_team_id, match.away_team_id
    scored = {home: 0, away: 0}
    for event in match.events:
        if event.action_type in SHOTS and event.result is Result.SUCCESS:
            scored[event.team_id] += 1
        elif event.result is Result.OWNGOAL:
            scored[away if event.team_id == home else home] += 1
    return scored


def scoreline(match: Match, league: League) -> Text:
    """The two clubs and the score, e.g. "Home Club 2-1 Away Club", each club in its colour."""
    score = goals(match)
    return Text.assemble(
        (league.club(match.home_team_id).name, HOME_STYLE),
        f" {score[match.home_team_id]}-{score[match.away_team_id]} ",
        (league.club(match.away_team_id).name, AWAY_STYLE),
    )


def events_table(
    match: Match,
    league: League,
    start: int,
    count: int,
    threat: Sequence[float | None] | None = None,
) -> Table:
    """A table of ``count`` events from action id ``start``.

    Coordinates are in metres, in the stored direction: the home team attacks towards x = 105.
    With ``threat`` (one value per event), a column shows how much threat each event added.
    """
    table = Table(header_style="bold")
    table.add_column("#", justify="right")
    table.add_column("time", justify="right")
    table.add_column("team")
    table.add_column("player")
    table.add_column("action")
    table.add_column("result")
    table.add_column("from → to")
    if threat is not None:
        table.add_column("threat", justify="right")
    table.add_column("phase")
    for event in match.events[start : start + count]:
        club = league.club(event.team_id)
        player = league.player(event.player_id)
        style = HOME_STYLE if event.team_id == match.home_team_id else AWAY_STYLE
        failed = event.result is not Result.SUCCESS
        table.add_row(
            str(event.action_id),
            match_clock(event),
            Text(club.name, style=style),
            f"#{player.shirt_number} {player.full_name}",
            event.action_type.spadl_name,
            Text(event.result.spadl_name, style="red" if failed else ""),
            f"({event.start_x:.0f},{event.start_y:.0f}) → ({event.end_x:.0f},{event.end_y:.0f})",
            *([] if threat is None else [threat_text(threat[event.action_id])]),
            event.phase.value.replace("_", " "),
        )
    return table


def threat_text(value: float | None) -> Text:
    """A threat value with its sign, green when it adds threat and red when it gives it up.

    Values that round to zero show as a plain ``0.000``.
    """
    if value is None:
        return Text("")
    shown = f"{value:+.3f}"
    if float(shown) == 0:
        return Text("0.000")
    return Text(shown, style="green" if value > 0 else "red")


def threat_grid(model: ThreatModel) -> Table:
    """The grid as a heat map, attacking left to right, with values in percent."""
    table = Table(show_header=False, box=None, padding=(0, 0, 0, 1))
    highest = max(max(row) for row in model.grid)
    for _ in model.grid[0]:
        table.add_column(justify="right", min_width=4, no_wrap=True)
    for row in model.grid:
        cells: list[Text] = []
        for value in row:
            # Square root, so the gentle rise outside the box still shows next to its peak.
            heat = int(255 * (value / highest) ** 0.5) if highest > 0 else 0
            cells.append(
                Text(f"{value * 100:.1f}", style=f"black on rgb(255,{255 - heat},{255 - heat})")
            )
        table.add_row(*cells)
    return table


def tags_table(match: Match, league: League, tags: Sequence[ConceptTag]) -> Table:
    """A table of concept tags, one row per tag, showing its key action.

    Coordinates are in the stored direction, as in `events_table`.
    """
    table = Table(header_style="bold")
    table.add_column("#", justify="right")
    table.add_column("time", justify="right")
    table.add_column("team")
    table.add_column("player")
    table.add_column("concept")
    table.add_column("action")
    table.add_column("from → to")
    table.add_column("difficulty", justify="right")
    table.add_column("evidence")
    for tag in tags:
        event = match.events[tag.action_id]
        player = league.player(event.player_id)
        style = HOME_STYLE if event.team_id == match.home_team_id else AWAY_STYLE
        table.add_row(
            str(tag.action_id),
            match_clock(event),
            Text(league.club(event.team_id).name, style=style),
            f"#{player.shirt_number} {player.full_name}",
            tag.concept.label,
            event.action_type.spadl_name,
            f"({event.start_x:.0f},{event.start_y:.0f}) → ({event.end_x:.0f},{event.end_y:.0f})",
            "" if tag.difficulty is None else f"{tag.difficulty:.2f}",
            " · ".join(f"{name} {value:g}" for name, value in tag.evidence.items()),
        )
    return table


PITCH_COLUMNS = 53
PITCH_ROWS = 17
PITCH_STYLE = "green"
PASS_STYLE = "yellow"
# By (on the ball's team, goalkeeper).
PLAYER_MARKS = {(True, False): "o", (True, True): "G", (False, False): "x", (False, True): "K"}
PITCH_LEGEND = (
    "@ on the ball · o teammates · G their keeper · x opponents · K opponents' keeper"
    " · * pass target"
)


def pitch_picture(match: Match, action_id: ActionId) -> Text:
    """The pitch at the start of an action, as text, with the actor's team attacking left to right.

    ``match`` must already be in that direction (see `btl.schema.frames.to_left_to_right`). The
    actor is ``@`` and the action's path a dotted line to ``*``. The actor's teammates are ``o``
    and opponents ``x``; the keepers are ``G`` and ``K``. Each team has its usual colour, and a
    legend under the pitch explains the marks.

    Raises:
        ValueError: If the action has no snapshot.
    """
    snapshot = match.snapshot(action_id)
    if snapshot is None:
        raise ValueError(f"no player positions for action {action_id}")
    event = match.events[action_id]
    cells = [[(" ", "")] * PITCH_COLUMNS for _ in range(PITCH_ROWS)]

    def put(x: float, y: float, mark: str, style: str) -> None:
        column = min(int(x / PITCH_LENGTH * PITCH_COLUMNS), PITCH_COLUMNS - 1)
        row = min(int((PITCH_WIDTH - y) / PITCH_WIDTH * PITCH_ROWS), PITCH_ROWS - 1)
        cells[row][column] = (mark, style)

    for row in cells:
        row[PITCH_COLUMNS // 2] = (":", PITCH_STYLE)
    for step in range(1, PITCH_COLUMNS):
        along = step / PITCH_COLUMNS
        put(
            event.start_x + along * (event.end_x - event.start_x),
            event.start_y + along * (event.end_y - event.start_y),
            "·",
            PASS_STYLE,
        )
    for player in snapshot.positions:
        style = HOME_STYLE if player.team_id == match.home_team_id else AWAY_STYLE
        mark = PLAYER_MARKS[player.team_id == event.team_id, player.is_goalkeeper]
        put(player.x, player.y, mark, style)
    put(event.end_x, event.end_y, "*", f"bold {PASS_STYLE}")
    actor_style = HOME_STYLE if event.team_id == match.home_team_id else AWAY_STYLE
    put(event.start_x, event.start_y, "@", f"bold {actor_style}")

    edge = "+" + "-" * PITCH_COLUMNS + "+"
    picture = Text(edge + "\n", style=PITCH_STYLE)
    for row in cells:
        picture.append("|", style=PITCH_STYLE)
        for mark, style in row:
            picture.append(mark, style=style)
        picture.append("|\n", style=PITCH_STYLE)
    picture.append(edge + "\n", style=PITCH_STYLE)
    picture.append(PITCH_LEGEND, style="dim")
    return picture
