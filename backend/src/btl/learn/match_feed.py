"""The match feed: the match told in short entries, from kick-off up to the moment asked about.

The page shows it beside the questions, standing in for the viewer's TV: each passing move, each
goal, shot, restart, foul, card and offside, and the halftime break. It uses only events strictly
before the moment the next question is about, so no entry says how that moment turned out, nor
how any later play went.
"""

from dataclasses import dataclass
from enum import StrEnum

from btl.schema import PITCH_WIDTH
from btl.schema.event import Event
from btl.schema.ids import PlayerId, TeamId
from btl.schema.match import Match
from btl.schema.possession import SHOTS, split_possessions
from btl.schema.vocab import ActionType, Result

CORNERS = frozenset({ActionType.CORNER_CROSSED, ActionType.CORNER_SHORT})
FREE_KICKS = frozenset(
    {ActionType.FREEKICK_CROSSED, ActionType.FREEKICK_SHORT, ActionType.SHOT_FREEKICK}
)


class FeedKind(StrEnum):
    """What a feed entry tells."""

    KICK_OFF = "kick_off"
    MOVE = "move"
    GOAL = "goal"
    OWN_GOAL = "own_goal"
    SHOT = "shot"
    CORNER = "corner"
    THROW_IN = "throw_in"
    GOAL_KICK = "goal_kick"
    FOUL = "foul"
    YELLOW_CARD = "yellow_card"
    RED_CARD = "red_card"
    OFFSIDE = "offside"
    HALFTIME = "halftime"


class ShotEnd(StrEnum):
    """How a shot that didn't go in ended, from the action after it."""

    SAVED = "saved"
    WIDE = "wide"
    DEFLECTED = "deflected"


class FoulGives(StrEnum):
    """What a foul gave the fouled team, from the action after it."""

    FREE_KICK = "free_kick"
    PENALTY = "penalty"
    ADVANTAGE = "advantage"


class Flank(StrEnum):
    """A side of the pitch, as the team taking a restart faces the goal it attacks."""

    LEFT = "left"
    RIGHT = "right"


@dataclass(frozen=True, slots=True)
class FeedEntry:
    """One entry, at the time it happened.

    ``players`` are in the order the words use them: a move's players in turn; a goal's or a
    card's player; a shot's shooter, then the keeper who saved it; a foul's fouler, then the
    fouled player; a restart's taker, then for a throw-in the player it went out off. A move is
    shown once its last touch, at ``until_seconds``, has happened; anything else at once.
    ``score`` is (home, away) after a goal, and at halftime.
    """

    kind: FeedKind
    period_id: int
    time_seconds: float
    until_seconds: float
    team_id: TeamId | None
    players: tuple[PlayerId, ...] = ()
    shot_end: ShotEnd | None = None
    foul_gives: FoulGives | None = None
    flank: Flank | None = None
    score: tuple[int, int] | None = None


def match_feed(match: Match, before: tuple[int, float]) -> tuple[FeedEntry, ...]:
    """The feed from kick-off to just before ``before``, oldest first.

    Args:
        match: The match.
        before: The moment the next question is about, as (period, seconds into it).
    """
    cut = next(
        (i for i, e in enumerate(match.events) if (e.period_id, e.time_seconds) >= before),
        len(match.events),
    )
    # Action ids index the match's events, so a prefix keeps possessions' ids valid.
    events = list(match.events[:cut])
    entries = [*_moves(match, events), *_incidents(match, events)]
    if any(event.period_id == 2 for event in events):
        first_half = sum(event.period_id == 1 for event in events)
        score = _score(match, events, first_half)
        entries.append(FeedEntry(FeedKind.HALFTIME, 2, 0.0, 0.0, None, score=score))
    # At the same moment the halftime break comes first, then a move, then what happened in it.
    rank = {FeedKind.HALFTIME: 0, FeedKind.KICK_OFF: 1, FeedKind.MOVE: 1}
    return tuple(sorted(entries, key=lambda e: (e.period_id, e.time_seconds, rank.get(e.kind, 2))))


def _moves(match: Match, events: list[Event]) -> list[FeedEntry]:
    moves: list[FeedEntry] = []
    period_starts = {e.period_id: e.action_id for e in reversed(match.events)}
    for possession in split_possessions(events):
        touches = [
            e
            for e in events[possession.first : possession.last + 1]
            if e.team_id == possession.team_id
        ]
        if not touches:
            continue
        players = tuple(
            touch.player_id
            for i, touch in enumerate(touches)
            if i == 0 or touch.player_id != touches[i - 1].player_id
        )
        first, last = touches[0], touches[-1]
        kicks_off = period_starts.get(first.period_id) == first.action_id
        moves.append(
            FeedEntry(
                FeedKind.KICK_OFF if kicks_off else FeedKind.MOVE,
                first.period_id,
                first.time_seconds,
                last.time_seconds,
                possession.team_id,
                players,
            )
        )
    return moves


def _incidents(match: Match, events: list[Event]) -> list[FeedEntry]:
    entries: list[FeedEntry] = []
    for i, event in enumerate(events):
        after = events[i + 1] if i + 1 < len(events) else None
        if after is not None and after.period_id != event.period_id:
            after = None
        entries.extend(_entries_for(match, events, i, event, after))
    return entries


def _entries_for(
    match: Match, events: list[Event], i: int, event: Event, after: Event | None
) -> list[FeedEntry]:
    def entry(
        kind: FeedKind,
        *players: PlayerId,
        flank: Flank | None = None,
        foul_gives: FoulGives | None = None,
        score: tuple[int, int] | None = None,
    ) -> FeedEntry:
        at = event.time_seconds
        return FeedEntry(
            kind,
            event.period_id,
            at,
            at,
            event.team_id,
            players,
            foul_gives=foul_gives,
            flank=flank,
            score=score,
        )

    found: list[FeedEntry] = []
    action, result = event.action_type, event.result
    if result is Result.OWNGOAL:
        found.append(entry(FeedKind.OWN_GOAL, event.player_id, score=_score(match, events, i + 1)))
    elif action in SHOTS and result is Result.SUCCESS:
        found.append(entry(FeedKind.GOAL, event.player_id, score=_score(match, events, i + 1)))
    elif action in SHOTS:
        found.append(_shot(event, after))
    if action in CORNERS:
        found.append(entry(FeedKind.CORNER, event.player_id, flank=_flank(match, event)))
    elif action is ActionType.THROW_IN:
        previous = events[i - 1] if i > 0 else None
        out_off = (
            (previous.player_id,)
            if previous is not None
            and previous.team_id != event.team_id
            and previous.period_id == event.period_id
            else ()
        )
        found.append(
            entry(FeedKind.THROW_IN, event.player_id, *out_off, flank=_flank(match, event))
        )
    elif action is ActionType.GOALKICK:
        found.append(entry(FeedKind.GOAL_KICK, event.player_id))
    elif action is ActionType.FOUL:
        fouled = next(
            (
                e.player_id
                for e in reversed(events[:i])
                if e.team_id != event.team_id and e.period_id == event.period_id
            ),
            None,
        )
        players = (event.player_id,) if fouled is None else (event.player_id, fouled)
        found.append(entry(FeedKind.FOUL, *players, foul_gives=_foul_gives(event, after)))
    if result is Result.YELLOW_CARD:
        found.append(entry(FeedKind.YELLOW_CARD, event.player_id))
    elif result is Result.RED_CARD:
        found.append(entry(FeedKind.RED_CARD, event.player_id))
    elif result is Result.OFFSIDE:
        found.append(entry(FeedKind.OFFSIDE, event.player_id))
    return found


def _shot(event: Event, after: Event | None) -> FeedEntry:
    at = event.time_seconds
    end: ShotEnd | None = None
    players = (event.player_id,)
    if after is not None and after.team_id != event.team_id:
        if after.action_type is ActionType.KEEPER_SAVE:
            end, players = ShotEnd.SAVED, (event.player_id, after.player_id)
        elif after.action_type is ActionType.GOALKICK:
            end = ShotEnd.WIDE
    elif after is not None and after.action_type in CORNERS:
        end = ShotEnd.DEFLECTED
    return FeedEntry(FeedKind.SHOT, event.period_id, at, at, event.team_id, players, shot_end=end)


def _foul_gives(foul: Event, after: Event | None) -> FoulGives | None:
    """What the fouled team got; None when the next action isn't theirs or isn't known yet."""
    if after is None or after.team_id == foul.team_id:
        return None
    if after.action_type is ActionType.SHOT_PENALTY:
        return FoulGives.PENALTY
    if after.action_type in FREE_KICKS:
        return FoulGives.FREE_KICK
    return FoulGives.ADVANTAGE


def _flank(match: Match, event: Event) -> Flank:
    # Stored events have home attacking towards x = 105, with y = 0 on its right.
    on_home_right = event.start_y < PITCH_WIDTH / 2
    home = event.team_id == match.home_team_id
    return Flank.RIGHT if on_home_right == home else Flank.LEFT


def _score(match: Match, events: list[Event], upto: int) -> tuple[int, int]:
    home = away = 0
    for event in events[:upto]:
        scored = event.action_type in SHOTS and event.result is Result.SUCCESS
        if scored or event.result is Result.OWNGOAL:
            for_home = (event.team_id == match.home_team_id) == scored
            home, away = (home + 1, away) if for_home else (home, away + 1)
    return home, away
