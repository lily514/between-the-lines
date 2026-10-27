"""Who had the ball between two questions, for a viewer following the match like a radio listener.

The page runs the match clock from where the viewer left off to the next question and says which
team and player are on the ball as it goes. The play-by-play stops just before the moment the
question is about, so it says nothing about how that play turned out.
"""

from dataclasses import dataclass

from btl.schema.ids import PlayerId, TeamId
from btl.schema.match import Match
from btl.schema.possession import split_possessions


@dataclass(frozen=True, slots=True)
class Touch:
    """One action by the team on the ball, and when it started."""

    player_id: PlayerId
    period_id: int
    time_seconds: float


@dataclass(frozen=True, slots=True)
class Spell:
    """One team's spell on the ball, cut to the part the play-by-play covers."""

    team_id: TeamId
    touches: tuple[Touch, ...]


def play_by_play(
    match: Match, after: tuple[int, float] | None, before: tuple[int, float]
) -> tuple[Spell, ...]:
    """The spells on the ball strictly between two points in the match.

    A defender's touch that doesn't win the ball stays inside the other team's spell, as
    `btl.schema.possession` defines it, but it isn't one of the spell's touches: the spell lists
    only the team on the ball.

    Args:
        match: The match.
        after: Where the viewer left off, as (period, seconds into it); None for kick-off.
        before: The moment the next question is about.
    """
    spells: list[Spell] = []
    for possession in split_possessions(match.events):
        touches = tuple(
            Touch(event.player_id, event.period_id, event.time_seconds)
            for event in match.events[possession.first : possession.last + 1]
            if event.team_id == possession.team_id
            and (after is None or (event.period_id, event.time_seconds) > after)
            and (event.period_id, event.time_seconds) < before
        )
        if touches:
            spells.append(Spell(possession.team_id, touches))
    return tuple(spells)
