from dataclasses import replace
from typing import NamedTuple

from btl.learn.match_feed import (
    FeedEntry,
    FeedKind,
    Flank,
    FoulGives,
    ShotEnd,
    match_feed,
)
from btl.schema.ids import PlayerId, TeamId
from btl.schema.match import Match
from btl.schema.vocab import ActionType, Result
from tests.fixtures.matches import (
    AWAY,
    AWAY_KEEPER,
    AWAY_MIDFIELDER,
    HOME,
    HOME_MIDFIELDER,
    HOME_WINGER,
    make_event,
    six_event_match,
)

LATER = (3, 0.0)


class Step(NamedTuple):
    team: TeamId
    player: PlayerId
    action: ActionType
    result: Result = Result.SUCCESS
    start: tuple[float, float] = (50.0, 34.0)


def play(*steps: Step) -> Match:
    """A match of the given actions, 4 s apart."""
    events = tuple(
        make_event(i, s.team, s.player, s.start, s.start, s.action, s.result)
        for i, s in enumerate(steps)
    )
    return replace(six_event_match(), events=events, positions=None)


def kinds(feed: tuple[FeedEntry, ...]) -> list[FeedKind]:
    return [entry.kind for entry in feed]


def test_each_spell_is_a_move_and_the_first_of_a_half_is_the_kick_off() -> None:
    feed = match_feed(six_event_match(), (2, 0.0))

    assert feed == (
        FeedEntry(FeedKind.KICK_OFF, 1, 0.0, 8.0, HOME, (HOME_MIDFIELDER, HOME_WINGER)),
        FeedEntry(FeedKind.MOVE, 1, 12.0, 20.0, AWAY, (AWAY_MIDFIELDER,)),
    )


def test_it_stops_before_the_moment() -> None:
    feed = match_feed(six_event_match(), (1, 8.0))

    assert feed == (
        FeedEntry(FeedKind.KICK_OFF, 1, 0.0, 4.0, HOME, (HOME_MIDFIELDER, HOME_WINGER)),
    )


def test_a_shot_says_how_it_ended_only_once_that_has_happened() -> None:
    saved = play(
        Step(HOME, HOME_WINGER, ActionType.SHOT, Result.FAIL),
        Step(AWAY, AWAY_KEEPER, ActionType.KEEPER_SAVE),
    )
    wide = play(
        Step(HOME, HOME_WINGER, ActionType.SHOT, Result.FAIL),
        Step(AWAY, AWAY_KEEPER, ActionType.GOALKICK),
    )
    deflected = play(
        Step(HOME, HOME_WINGER, ActionType.SHOT, Result.FAIL),
        Step(HOME, HOME_MIDFIELDER, ActionType.CORNER_CROSSED, Result.SUCCESS, (105.0, 0.0)),
    )

    def shot(match: Match, before: tuple[int, float] = LATER) -> FeedEntry:
        return next(e for e in match_feed(match, before) if e.kind is FeedKind.SHOT)

    assert (shot(saved).shot_end, shot(saved).players) == (
        ShotEnd.SAVED,
        (HOME_WINGER, AWAY_KEEPER),
    )
    assert shot(wide).shot_end is ShotEnd.WIDE
    assert FeedKind.GOAL_KICK in kinds(match_feed(wide, LATER))
    assert shot(deflected).shot_end is ShotEnd.DEFLECTED
    corner = next(e for e in match_feed(deflected, LATER) if e.kind is FeedKind.CORNER)
    assert (corner.players, corner.flank) == ((HOME_MIDFIELDER,), Flank.RIGHT)
    assert shot(saved, (1, 4.0)).shot_end is None


def test_a_goal_carries_the_score_and_an_own_goal_counts_for_the_other_side() -> None:
    match = play(
        Step(HOME, HOME_WINGER, ActionType.SHOT),
        Step(AWAY, AWAY_MIDFIELDER, ActionType.CLEARANCE, Result.OWNGOAL),
    )

    goals = [e for e in match_feed(match, LATER) if e.kind in {FeedKind.GOAL, FeedKind.OWN_GOAL}]

    assert [(e.kind, e.players, e.score) for e in goals] == [
        (FeedKind.GOAL, (HOME_WINGER,), (1, 0)),
        (FeedKind.OWN_GOAL, (AWAY_MIDFIELDER,), (2, 0)),
    ]


def test_a_foul_names_who_was_fouled_and_what_it_gave() -> None:
    free_kick = play(
        Step(HOME, HOME_WINGER, ActionType.DRIBBLE),
        Step(AWAY, AWAY_MIDFIELDER, ActionType.FOUL, Result.YELLOW_CARD),
        Step(HOME, HOME_MIDFIELDER, ActionType.FREEKICK_SHORT),
    )
    penalty = play(
        Step(HOME, HOME_WINGER, ActionType.DRIBBLE),
        Step(AWAY, AWAY_MIDFIELDER, ActionType.FOUL, Result.FAIL),
        Step(HOME, HOME_WINGER, ActionType.SHOT_PENALTY, Result.FAIL),
    )
    advantage = play(
        Step(HOME, HOME_WINGER, ActionType.DRIBBLE),
        Step(AWAY, AWAY_MIDFIELDER, ActionType.FOUL, Result.FAIL),
        Step(HOME, HOME_WINGER, ActionType.PASS),
    )

    def foul(match: Match, before: tuple[int, float] = LATER) -> FeedEntry:
        return next(e for e in match_feed(match, before) if e.kind is FeedKind.FOUL)

    assert (foul(free_kick).players, foul(free_kick).foul_gives) == (
        (AWAY_MIDFIELDER, HOME_WINGER),
        FoulGives.FREE_KICK,
    )
    assert FeedKind.YELLOW_CARD in kinds(match_feed(free_kick, LATER))
    assert foul(penalty).foul_gives is FoulGives.PENALTY
    assert foul(advantage).foul_gives is FoulGives.ADVANTAGE
    assert foul(free_kick, (1, 8.0)).foul_gives is None


def test_a_throw_in_says_who_it_went_out_off_and_which_touchline() -> None:
    match = play(
        Step(HOME, HOME_WINGER, ActionType.PASS, Result.FAIL),
        Step(AWAY, AWAY_MIDFIELDER, ActionType.THROW_IN, Result.SUCCESS, (60.0, 68.0)),
    )

    throw = next(e for e in match_feed(match, LATER) if e.kind is FeedKind.THROW_IN)

    # Away attacks towards x = 0, so y = 68 is on its right.
    assert (throw.team_id, throw.players, throw.flank) == (
        AWAY,
        (AWAY_MIDFIELDER, HOME_WINGER),
        Flank.RIGHT,
    )


def test_halftime_comes_between_the_halves_with_the_first_half_score() -> None:
    first = make_event(0, HOME, HOME_WINGER, (90, 34), (105, 34), ActionType.SHOT)
    second = make_event(1, AWAY, AWAY_MIDFIELDER, (52, 34), (40, 34), period_id=2)
    events = (first, replace(second, time_seconds=0.0))
    match = replace(six_event_match(), events=events, positions=None)

    feed = match_feed(match, LATER)

    assert kinds(feed) == [FeedKind.KICK_OFF, FeedKind.GOAL, FeedKind.HALFTIME, FeedKind.KICK_OFF]
    assert feed[2].score == (1, 0)
    assert kinds(match_feed(match, (2, 0.0))) == [FeedKind.KICK_OFF, FeedKind.GOAL]
