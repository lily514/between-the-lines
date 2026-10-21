"""Each player's numbers from the matches a viewer has already watched.

These are the numbers the team sheet shows from stage 3. They are counted only over matches
the viewer has finished, so they can't hint at anything in the match about to be watched.

- **Matches:** watched matches the player started.
- **Passes:** ordinary passes and crosses in play, completed and tried. Set pieces (throw-ins,
  free kicks, corners, goal kicks) don't count: every player would get some just for standing
  nearest when the ball went out.
- **Line-breaking passes:** passes the line-breaking detector finds, whether or not they were
  good enough to ask a question about.
- **Threat added:** the Expected Threat the player's actions added, summed.
"""

from collections import Counter, defaultdict
from collections.abc import Collection, Iterable, Mapping
from dataclasses import dataclass

from btl.concepts.base import MatchContext
from btl.concepts.line_breaking import LineBreakingPass
from btl.schema.ids import PlayerId, TeamId
from btl.schema.vocab import ActionType, Result

PASS_TYPES = frozenset({ActionType.PASS, ActionType.CROSS})


@dataclass(frozen=True, slots=True)
class PlayerStats:
    """One player's numbers over the watched matches they started."""

    matches: int
    passes_completed: int
    passes_tried: int
    line_breaking_passes: int
    threat_added: float


@dataclass(frozen=True, slots=True)
class WatchedNumbers:
    """Numbers from the watched matches: per player, and how many each club played."""

    players: Mapping[PlayerId, PlayerStats]
    team_matches: Mapping[TeamId, int]


NO_NUMBERS = WatchedNumbers({}, {})


def watched_numbers(watched: Iterable[tuple[MatchContext, Collection[PlayerId]]]) -> WatchedNumbers:
    """Count each player's numbers over the watched matches.

    Args:
        watched: Each finished match's context (with its threat ratings) and its starters.

    Raises:
        ValueError: If a match has no threat ratings.
    """
    matches: Counter[PlayerId] = Counter()
    team_matches: Counter[TeamId] = Counter()
    completed: Counter[PlayerId] = Counter()
    tried: Counter[PlayerId] = Counter()
    breaking: Counter[PlayerId] = Counter()
    threat: defaultdict[PlayerId, float] = defaultdict(float)
    detector = LineBreakingPass()
    for ctx, starters in watched:
        if ctx.threat is None:
            raise ValueError("watched numbers need the match's threat ratings")
        matches.update(starters)
        team_matches.update((ctx.match.home_team_id, ctx.match.away_team_id))
        for event, added in zip(ctx.events, ctx.threat, strict=True):
            if event.action_type in PASS_TYPES:
                tried[event.player_id] += 1
                completed[event.player_id] += event.result is Result.SUCCESS
            if added is not None:
                threat[event.player_id] += added
        for tag in detector.detect(ctx):
            breaking[ctx.events[tag.action_id].player_id] += 1
    players = {
        player: PlayerStats(
            matches=count,
            passes_completed=completed[player],
            passes_tried=tried[player],
            line_breaking_passes=breaking[player],
            threat_added=threat[player],
        )
        for player, count in matches.items()
    }
    return WatchedNumbers(players, dict(team_matches))
