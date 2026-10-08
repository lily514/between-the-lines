"""The scoreboard: the match clock and the score, as a viewer would read them."""

from btl.schema.event import Event
from btl.schema.ids import ActionId, TeamId
from btl.schema.match import Match
from btl.schema.possession import SHOTS
from btl.schema.vocab import Result

PERIOD_MINUTES = 45


def clock(period_id: int, time_seconds: float) -> str:
    """Time on the match clock, e.g. ``68:12`` for 23 min 12 s into the second half."""
    seconds = int(time_seconds) + (period_id - 1) * PERIOD_MINUTES * 60
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def match_clock(event: Event) -> str:
    """The match clock when an action starts."""
    return clock(event.period_id, event.time_seconds)


def goals(match: Match, before: ActionId | None = None) -> dict[TeamId, int]:
    """Goals per team, counting own goals for the other team.

    Args:
        match: The match.
        before: Count only goals from actions before this one; all goals if None.
    """
    home, away = match.home_team_id, match.away_team_id
    scored = {home: 0, away: 0}
    events = match.events if before is None else match.events[:before]
    for event in events:
        if event.action_type in SHOTS and event.result is Result.SUCCESS:
            scored[event.team_id] += 1
        elif event.result is Result.OWNGOAL:
            scored[away if event.team_id == home else home] += 1
    return scored
