"""The match's running numbers, for the commentary: goals, possession, shots, corners, fouls, cards.

The numbers are kept as a timeline, one entry each time one of them changes, from where the
viewer left off up to just before the moment the next question is about, so the page can show
them as the match clock runs on without saying anything about how that moment turned out.
"""

from dataclasses import dataclass

from btl.schema.event import Event
from btl.schema.match import Match
from btl.schema.possession import SHOTS, split_possessions
from btl.schema.vocab import ActionType, Result

CORNERS = frozenset({ActionType.CORNER_CROSSED, ActionType.CORNER_SHORT})


@dataclass(frozen=True, slots=True)
class SideStats:
    """One team's numbers so far. ``possession`` is its share of the time on the ball, in %."""

    goals: int
    possession: int
    attempts: int
    corners: int
    fouls: int
    yellow_cards: int
    red_cards: int


@dataclass(frozen=True, slots=True)
class StatsAt:
    """Both teams' numbers as they stand from a point in the match."""

    period_id: int
    time_seconds: float
    home: SideStats
    away: SideStats


@dataclass(slots=True)
class _Tally:
    seconds_on_ball: float = 0.0
    goals: int = 0
    attempts: int = 0
    corners: int = 0
    fouls: int = 0
    yellow_cards: int = 0
    red_cards: int = 0

    def add(self, event: Event) -> bool:
        """Count one of the team's own actions; whether any number changed."""
        before = self.numbers()
        self.goals += event.action_type in SHOTS and event.result is Result.SUCCESS
        self.attempts += event.action_type in SHOTS
        self.corners += event.action_type in CORNERS
        self.fouls += event.action_type is ActionType.FOUL
        self.yellow_cards += event.result is Result.YELLOW_CARD
        self.red_cards += event.result is Result.RED_CARD
        return before != self.numbers()

    def numbers(self) -> tuple[int, ...]:
        counts = (self.attempts, self.corners, self.fouls, self.yellow_cards, self.red_cards)
        return (self.goals, *counts)


def stats_timeline(
    match: Match, after: tuple[int, float] | None, before: tuple[int, float]
) -> tuple[StatsAt, ...]:
    """The numbers where the viewer left off, then again at each change before the moment.

    Possession is the share of time on the ball: the team in possession at an action holds it
    until the next action in the same period. Goals count own goals for the other team. An entry
    is added whenever the ball changes hands, a number is counted or a half starts.

    Args:
        match: The match.
        after: Where the viewer left off, as (period, seconds into it); None for kick-off.
        before: The moment the next question is about. When the viewer left off after it, the
            only entry is from just before the moment.
    """
    home, away = _Tally(), _Tally()
    tallies = {match.home_team_id: home, match.away_team_id: away}
    holder = {
        action_id: possession.team_id
        for possession in split_possessions(match.events)
        for action_id in range(possession.first, possession.last + 1)
    }
    start = (1, 0.0) if after is None else min(after, before)
    timeline: list[StatsAt] = []
    previous: Event | None = None
    for event in match.events:
        at = (event.period_id, event.time_seconds)
        if at >= before:
            break
        if not timeline and at > start:
            timeline.append(_stats_at(start, home, away))
        if previous is not None and previous.period_id == event.period_id:
            tallies[holder[previous.action_id]].seconds_on_ball += (
                event.time_seconds - previous.time_seconds
            )
        counted = tallies[event.team_id].add(event)
        if event.result is Result.OWNGOAL:
            other = away if event.team_id == match.home_team_id else home
            other.goals += 1
            counted = True
        changes_hands = previous is None or holder[previous.action_id] != holder[event.action_id]
        new_half = previous is not None and previous.period_id != event.period_id
        previous = event
        if timeline and (counted or changes_hands or new_half):
            timeline.append(_stats_at(at, home, away))
    if not timeline:
        timeline.append(_stats_at(start, home, away))
    return tuple(timeline)


def _stats_at(at: tuple[int, float], home: _Tally, away: _Tally) -> StatsAt:
    total = home.seconds_on_ball + away.seconds_on_ball
    home_share = 50 if total == 0 else round(100 * home.seconds_on_ball / total)
    return StatsAt(*at, _side(home, home_share), _side(away, 100 - home_share))


def _side(tally: _Tally, possession: int) -> SideStats:
    return SideStats(
        goals=tally.goals,
        possession=possession,
        attempts=tally.attempts,
        corners=tally.corners,
        fouls=tally.fouls,
        yellow_cards=tally.yellow_cards,
        red_cards=tally.red_cards,
    )
