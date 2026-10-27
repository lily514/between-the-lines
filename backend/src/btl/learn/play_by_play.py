"""Who had the ball between two questions, for a viewer following the match like a radio listener.

The page runs the match clock from where the viewer left off to the next question and says which
team and player are on the ball as it goes, what they did with it and where. The play-by-play
stops just before the moment the question is about, so it says nothing about how that play turned
out. The match feed (`btl.learn.match_feed`) tells the rest: moves, goals, restarts and fouls.
"""

from dataclasses import dataclass
from enum import StrEnum

from btl.concepts.counter_attack import BOX_DEPTH, BOX_HALF_WIDTH
from btl.schema import PITCH_LENGTH, PITCH_WIDTH
from btl.schema.event import Event
from btl.schema.ids import PlayerId, TeamId
from btl.schema.match import Match
from btl.schema.possession import split_possessions
from btl.schema.vocab import ActionType, Result


class Zone(StrEnum):
    """Where an action starts, seen by the team making it: thirds of the pitch, and their box."""

    OWN_THIRD = "own_third"
    MIDDLE_THIRD = "middle_third"
    FINAL_THIRD = "final_third"
    BOX = "box"


@dataclass(frozen=True, slots=True)
class Touch:
    """One action by the team on the ball: who, when, what they did, how it went and where."""

    player_id: PlayerId
    period_id: int
    time_seconds: float
    action_type: ActionType
    result: Result
    zone: Zone


@dataclass(frozen=True, slots=True)
class Spell:
    """One team's spell on the ball, cut to the part the play-by-play covers."""

    team_id: TeamId
    touches: tuple[Touch, ...]


def zone_of(event: Event, home_team_id: TeamId) -> Zone:
    """Where an action starts, seen by its own team; stored events have home attacking x = 105."""
    ahead = event.start_x if event.team_id == home_team_id else PITCH_LENGTH - event.start_x
    if ahead >= PITCH_LENGTH - BOX_DEPTH and abs(event.start_y - PITCH_WIDTH / 2) <= BOX_HALF_WIDTH:
        return Zone.BOX
    if ahead >= 2 * PITCH_LENGTH / 3:
        return Zone.FINAL_THIRD
    if ahead >= PITCH_LENGTH / 3:
        return Zone.MIDDLE_THIRD
    return Zone.OWN_THIRD


def _between(event: Event, after: tuple[int, float] | None, before: tuple[int, float]) -> bool:
    at = (event.period_id, event.time_seconds)
    return (after is None or at > after) and at < before


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
            Touch(
                event.player_id,
                event.period_id,
                event.time_seconds,
                event.action_type,
                event.result,
                zone_of(event, match.home_team_id),
            )
            for event in match.events[possession.first : possession.last + 1]
            if event.team_id == possession.team_id and _between(event, after, before)
        )
        if touches:
            spells.append(Spell(possession.team_id, touches))
    return tuple(spells)
