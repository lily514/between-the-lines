"""How the CLI shows a match: the scoreline and a rich table of its events."""

from rich.table import Table
from rich.text import Text

from btl.league.league import League
from btl.schema.event import Event
from btl.schema.ids import TeamId
from btl.schema.match import Match
from btl.schema.vocab import ActionType, Result

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


def events_table(match: Match, league: League, start: int, count: int) -> Table:
    """A table of ``count`` events from action id ``start``.

    Coordinates are in metres, in the stored direction: the home team attacks towards x = 105.
    """
    table = Table(header_style="bold")
    table.add_column("#", justify="right")
    table.add_column("time", justify="right")
    table.add_column("team")
    table.add_column("player")
    table.add_column("action")
    table.add_column("result")
    table.add_column("from → to")
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
            event.phase.value.replace("_", " "),
        )
    return table
