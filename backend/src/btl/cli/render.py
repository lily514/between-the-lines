"""How the CLI shows things: matches, summaries, events, tags, threat, the pitch, replays."""

from collections import Counter
from collections.abc import Sequence
from pathlib import Path

from rich.table import Table
from rich.text import Text

from btl.concepts.base import ConceptTag
from btl.io import MatchInfo
from btl.league.league import League
from btl.replay import ReplayFrame
from btl.schema import PITCH_LENGTH, PITCH_WIDTH
from btl.schema.event import Event
from btl.schema.ids import ActionId, TeamId
from btl.schema.match import Match
from btl.schema.possession import split_possessions
from btl.schema.scoreboard import clock, goals, match_clock
from btl.schema.snapshot import PlayerPosition
from btl.schema.vocab import ActionType, ConceptId, Result
from btl.value.xt import ThreatModel

SHOTS = frozenset({ActionType.SHOT, ActionType.SHOT_FREEKICK, ActionType.SHOT_PENALTY})
HOME_STYLE = "cyan"
AWAY_STYLE = "magenta"


def counted(count: int, noun: str, plural: str | None = None) -> str:
    """A count with its noun, plural unless the count is one, e.g. "1 tag" or "1,203 tags".

    ``plural`` is for nouns that don't just add an "s".
    """
    return f"{count:,} {noun if count == 1 else plural or noun + 's'}"


def scoreline(match: Match, league: League) -> Text:
    """The two clubs and the score, e.g. "Home Club 2-1 Away Club", each club in its colour."""
    score = goals(match)
    return Text.assemble(
        (league.club(match.home_team_id).name, HOME_STYLE),
        f" {score[match.home_team_id]}-{score[match.away_team_id]} ",
        (league.club(match.away_team_id).name, AWAY_STYLE),
    )


def matches_table(saved: Sequence[tuple[Path, Match, MatchInfo, League]]) -> Table:
    """One row per saved match: its folder's name, clubs and score, seed, and what it holds."""
    table = Table(header_style="bold")
    table.add_column("match")
    table.add_column("home", justify="right")
    table.add_column("score", justify="center")
    table.add_column("away")
    table.add_column("seed", justify="right")
    table.add_column("events", justify="right")
    table.add_column("planted moments")
    for directory, match, info, league in saved:
        score = goals(match)
        planted = Counter(moment.concept for moment in match.planted)
        table.add_row(
            directory.name,
            Text(league.club(match.home_team_id).name, style=HOME_STYLE),
            f"{score[match.home_team_id]}-{score[match.away_team_id]}",
            Text(league.club(match.away_team_id).name, style=AWAY_STYLE),
            str(info.seed),
            f"{len(match.events):,}",
            ", ".join(f"{concept.label} {count}" for concept, count in planted.items()),
        )
    return table


def events_table(
    match: Match,
    league: League,
    events: Sequence[Event],
    threat: Sequence[float | None] | None = None,
    tags: Sequence[ConceptTag] | None = None,
) -> Table:
    """A table of some of a match's events.

    Coordinates are in metres, in the stored direction: the home team attacks towards x = 105.
    With ``threat`` (one value per event in the match), a column shows how much threat each event
    added. With ``tags``, a column names the concepts whose key action each event is, marking
    those planted as teachable moments.
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
    concepts = _concepts_by_action(match, tags or ())
    if tags is not None:
        table.add_column("concepts")
    for event in events:
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
            *([] if tags is None else [", ".join(concepts.get(event.action_id, ()))]),
        )
    return table


def _concepts_by_action(match: Match, tags: Sequence[ConceptTag]) -> dict[ActionId, list[str]]:
    planted = {(moment.concept, moment.answer_action_id) for moment in match.planted}
    concepts: dict[ActionId, list[str]] = {}
    for tag in tags:
        label = tag.concept.label
        if (tag.concept, tag.action_id) in planted:
            label += " (planted)"
        concepts.setdefault(tag.action_id, []).append(label)
    return concepts


def summary_table(
    match: Match,
    league: League,
    tags: Sequence[ConceptTag],
    threat: Sequence[float | None] | None = None,
) -> Table:
    """Each team's main numbers side by side: goals, shots, passes, possessions, and concepts.

    With ``threat`` (one value per event), a row adds up the threat each team's actions added.
    """
    teams = (match.home_team_id, match.away_team_id)
    table = Table(header_style="bold")
    table.add_column("")
    for team, style in zip(teams, (HOME_STYLE, AWAY_STYLE), strict=True):
        table.add_column(Text(league.club(team).name, style=style), justify="right")

    score = goals(match)
    shots = Counter(event.team_id for event in match.events if event.action_type in SHOTS)
    passes = Counter(
        event.team_id for event in match.events if event.action_type is ActionType.PASS
    )
    completed = Counter(
        event.team_id
        for event in match.events
        if event.action_type is ActionType.PASS and event.result is Result.SUCCESS
    )
    possessions = Counter(possession.team_id for possession in split_possessions(match.events))
    table.add_row("goals", *(str(score[team]) for team in teams))
    table.add_row("shots", *(str(shots[team]) for team in teams))
    table.add_row(
        "passes (completed)",
        *(
            f"{passes[team]} ({completed[team] / passes[team]:.0%})" if passes[team] else "0"
            for team in teams
        ),
    )
    table.add_row("possessions", *(str(possessions[team]) for team in teams))
    if threat is not None:
        added = dict.fromkeys(teams, 0.0)
        for event, value in zip(match.events, threat, strict=True):
            if value is not None:
                added[event.team_id] += value
        table.add_row("threat added", *(f"{added[team]:+.2f}" for team in teams))
    found = Counter((tag.concept, match.events[tag.action_id].team_id) for tag in tags)
    for concept in ConceptId:
        table.add_row(concept.label, *(str(found[concept, team]) for team in teams))
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
REPLAY_LEGEND = (
    "@ ball · o attackers · G their keeper · x defenders · K their keeper · * where the ball went"
)


class _Pitch:
    """A grid of marks, one character for each 2 m by 4 m of pitch, with the halfway line."""

    def __init__(self) -> None:
        self.cells = [[(" ", "")] * PITCH_COLUMNS for _ in range(PITCH_ROWS)]
        for row in self.cells:
            row[PITCH_COLUMNS // 2] = (":", PITCH_STYLE)

    def put(self, x: float, y: float, mark: str, style: str) -> None:
        column = min(int(x / PITCH_LENGTH * PITCH_COLUMNS), PITCH_COLUMNS - 1)
        row = min(int((PITCH_WIDTH - y) / PITCH_WIDTH * PITCH_ROWS), PITCH_ROWS - 1)
        self.cells[row][column] = (mark, style)

    def dot_path(self, start: tuple[float, float], end: tuple[float, float]) -> None:
        (start_x, start_y), (end_x, end_y) = start, end
        for step in range(1, PITCH_COLUMNS):
            along = step / PITCH_COLUMNS
            self.put(
                start_x + along * (end_x - start_x),
                start_y + along * (end_y - start_y),
                "·",
                PASS_STYLE,
            )

    def put_players(self, players: Sequence[PlayerPosition], team_id: TeamId, home: TeamId) -> None:
        for player in players:
            style = HOME_STYLE if player.team_id == home else AWAY_STYLE
            mark = PLAYER_MARKS[player.team_id == team_id, player.is_goalkeeper]
            self.put(player.x, player.y, mark, style)

    def text(self, legend: str) -> Text:
        edge = "+" + "-" * PITCH_COLUMNS + "+"
        picture = Text(edge + "\n", style=PITCH_STYLE)
        for row in self.cells:
            picture.append("|", style=PITCH_STYLE)
            for mark, style in row:
                picture.append(mark, style=style)
            picture.append("|\n", style=PITCH_STYLE)
        picture.append(edge + "\n", style=PITCH_STYLE)
        picture.append(legend, style="dim")
        return picture


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
    start, end = (event.start_x, event.start_y), (event.end_x, event.end_y)
    pitch = _Pitch()
    pitch.dot_path(start, end)
    pitch.put_players(snapshot.positions, event.team_id, match.home_team_id)
    pitch.put(*end, "*", f"bold {PASS_STYLE}")
    pitch.put(*start, "@", f"bold {_team_style(match, event.team_id)}")
    return pitch.text(PITCH_LEGEND)


def replay_picture(
    match: Match, frame: ReplayFrame, team_id: TeamId, *, show_target: bool = False
) -> Text:
    """One frame of a replay as text, with the clock above the pitch.

    ``match`` must be seen from ``team_id``'s side (see `btl.schema.frames.seen_by`), and its
    players are ``o`` and ``G`` throughout, the other team's ``x`` and ``K``. The ball is ``@``,
    in the colour of the team whose action is under way, trailing a dotted path from where the
    action started. With ``show_target``, the action's whole path is drawn, ending in ``*``.
    """
    event = match.events[frame.action_id]
    start, end = (event.start_x, event.start_y), (event.end_x, event.end_y)
    pitch = _Pitch()
    pitch.dot_path(start, end if show_target else frame.ball)
    pitch.put_players(frame.players, team_id, match.home_team_id)
    if show_target:
        pitch.put(*end, "*", f"bold {PASS_STYLE}")
    pitch.put(*frame.ball, "@", f"bold {_team_style(match, event.team_id)}")
    time = Text(clock(event.period_id, frame.time_seconds) + "\n", style="bold")
    return Text.assemble(time, pitch.text(REPLAY_LEGEND))


def _team_style(match: Match, team_id: TeamId) -> str:
    return HOME_STYLE if team_id == match.home_team_id else AWAY_STYLE
