"""The commentary's words: what a player did with the ball, where, and each feed entry's line."""

from collections.abc import Callable

from btl.learn.match_feed import FeedEntry, FeedKind, FoulGives, ShotEnd
from btl.learn.play_by_play import Zone
from btl.schema.ids import PlayerId, TeamId
from btl.schema.possession import SHOTS
from btl.schema.vocab import ActionType, Result

ACTION_WORDS = {
    ActionType.PASS: "passes",
    ActionType.CROSS: "crosses",
    ActionType.THROW_IN: "takes the throw-in",
    ActionType.FREEKICK_CROSSED: "takes the free kick",
    ActionType.FREEKICK_SHORT: "takes the free kick",
    ActionType.CORNER_CROSSED: "takes the corner",
    ActionType.CORNER_SHORT: "takes the corner",
    ActionType.TAKE_ON: "takes on a defender",
    ActionType.FOUL: "commits a foul",
    ActionType.TACKLE: "wins it with a tackle",
    ActionType.INTERCEPTION: "intercepts",
    ActionType.SHOT: "shoots",
    ActionType.SHOT_PENALTY: "takes the penalty",
    ActionType.SHOT_FREEKICK: "shoots from the free kick",
    ActionType.KEEPER_SAVE: "saves",
    ActionType.KEEPER_CLAIM: "claims it",
    ActionType.KEEPER_PUNCH: "punches it clear",
    ActionType.KEEPER_PICK_UP: "picks it up",
    ActionType.CLEARANCE: "clears",
    ActionType.BAD_TOUCH: "takes a heavy touch",
    ActionType.NON_ACTION: "has it",
    ActionType.DRIBBLE: "carries it",
    ActionType.GOALKICK: "takes the goal kick",
}

APOSTROPHE = "\N{RIGHT SINGLE QUOTATION MARK}"

ZONE_WORDS = {
    Zone.OWN_THIRD: "in their own third",
    Zone.MIDDLE_THIRD: "in midfield",
    Zone.FINAL_THIRD: "in the final third",
    Zone.BOX: "in the box",
}


def action_words(action_type: ActionType, result: Result) -> str:
    """What a player did, e.g. "crosses" or "shoots and scores"."""
    words = ACTION_WORDS[action_type]
    if action_type in SHOTS and result is Result.SUCCESS:
        return f"{words} and scores"
    return words


def feed_words(
    entry: FeedEntry,
    surname: Callable[[PlayerId], str],
    club: Callable[[TeamId], str],
    rival: Callable[[TeamId], str],
) -> tuple[str, str]:
    """A feed entry's label and line, e.g. ("Shot · saved", "Ferreiro shoots; Halloran saves.").

    ``club`` names a team, and ``rival`` the team it is playing. A move's players are shown by
    the page, one after another, so its line is empty unless it starts the second half.
    """
    names = [surname(player) for player in entry.players]
    other = None if entry.team_id is None else club(entry.team_id)
    match entry.kind:
        case FeedKind.KICK_OFF:
            return "Kick-off", "Second half under way." if entry.period_id == 2 else ""
        case FeedKind.MOVE:
            count = len(entry.players)
            return f"Passing move · {count} player{'' if count == 1 else 's'}", ""
        case FeedKind.GOAL:
            return "Goal", f"{names[0]} scores."
        case FeedKind.OWN_GOAL:
            return "Own goal", f"{names[0]} scores an own goal."
        case FeedKind.SHOT:
            return _shot_words(entry.shot_end, names)
        case FeedKind.CORNER:
            return "Corner", f"Corner on the {entry.flank}, taken by {names[0]}."
        case FeedKind.THROW_IN:
            out_off = f"Out off {names[1]}. " if len(names) > 1 else ""
            return "Dead ball · throw-in", f"{out_off}Throw-in to {other}, {entry.flank} touchline."
        case FeedKind.GOAL_KICK:
            return "Dead ball · goal kick", f"Goal kick to {other}, taken by {names[0]}."
        case FeedKind.FOUL:
            return "Foul", _foul_line(entry, names, rival)
        case FeedKind.YELLOW_CARD:
            return "Yellow card", f"{names[0]} is booked."
        case FeedKind.RED_CARD:
            return "Red card", f"{names[0]} is sent off."
        case FeedKind.OFFSIDE:
            return (
                "Offside",
                f"Flag up: offside from {names[0]}{APOSTROPHE}s pass.",
            )
        case FeedKind.HALFTIME:
            return "Halftime", ""


def _shot_words(end: ShotEnd | None, names: list[str]) -> tuple[str, str]:
    match end:
        case ShotEnd.SAVED:
            return "Shot · saved", f"{names[0]} shoots; {names[1]} saves."
        case ShotEnd.WIDE:
            return "Shot · wide", f"{names[0]} shoots wide."
        case ShotEnd.DEFLECTED:
            return "Shot · deflected", f"{names[0]} shoots; it goes behind for a corner."
        case None:
            return "Shot", f"{names[0]} shoots."


def _foul_line(entry: FeedEntry, names: list[str], rival: Callable[[TeamId], str]) -> str:
    who = f"{names[0]} fouls {names[1]}." if len(names) > 1 else f"Foul by {names[0]}."
    if entry.team_id is None:
        return who
    fouled = rival(entry.team_id)
    match entry.foul_gives:
        case FoulGives.FREE_KICK:
            return f"{who} Free kick to {fouled}."
        case FoulGives.PENALTY:
            return f"{who} Penalty to {fouled}."
        case FoulGives.ADVANTAGE:
            return f"{who} Play goes on: advantage {fouled}."
        case None:
            return who
