from dataclasses import replace
from functools import cache
from itertools import pairwise

import numpy as np
import pytest

from btl.concepts.ball_win import THIRD, BallWin, WonWith, pitch_third, won_with
from btl.concepts.base import ConceptTag, match_context
from btl.league.league import generate_league
from btl.schema.match import Match
from btl.schema.possession import changes_hands_in_open_play, split_possessions
from btl.schema.vocab import ActionType, ConceptId, Result
from btl.sim.engine import simulate_match
from tests.fixtures.concepts import lost_and_won_back, won_and_carried
from tests.fixtures.matches import AWAY, AWAY_KEEPER, GAME, HOME, HOME_MIDFIELDER, make_event

ON_THE_LINE = (70.0, 30.0)
OWN_HALF = (30.0, 34.0)


@cache
def simulated(seed: int) -> Match:
    home, away = generate_league(np.random.default_rng(0)).clubs[:2]
    return simulate_match(home, away, seed, with_snapshots=False)


def detect(match: Match) -> tuple[ConceptTag, ...]:
    return BallWin().detect(match_context(match))


def test_an_interception_and_a_tackle_are_both_ball_wins_with_their_own_span() -> None:
    interception, tackle = detect(lost_and_won_back(4, ON_THE_LINE))

    assert interception.concept is tackle.concept is ConceptId.BALL_WIN
    # Away cuts out home's pass at (80, 40): 25 m from its own goal, in its own third.
    assert (interception.action_id, interception.span) == (2, (1, 2))
    assert interception.evidence == {
        "won with": float(WonWith.INTERCEPTION),
        "metres from own goal": 25.0,
    }
    # Home tackles on the attacking third's line, the hardest third to call.
    assert (tackle.action_id, tackle.span) == (4, (3, 4))
    assert tackle.evidence == {"won with": float(WonWith.TACKLE), "metres from own goal": 70.0}
    assert tackle.difficulty == 1.0


@pytest.mark.parametrize(
    ("x", "difficulty"),
    [(5.0, 0.0), (23.0, 0.0), (29.0, 0.5), (35.0, 1.0), (41.0, 0.5), (52.5, 0.0)],
)
def test_the_nearer_a_thirds_line_the_harder_the_third_is_to_call(
    x: float, difficulty: float
) -> None:
    (tag,) = detect(won_and_carried(9, (x, 34.0)))

    assert tag.difficulty == pytest.approx(difficulty)


def test_the_keeper_gathering_a_shot_is_a_ball_win_near_their_own_goal() -> None:
    events = (
        make_event(0, HOME, HOME_MIDFIELDER, (85, 34), (104, 34), ActionType.SHOT, Result.FAIL),
        make_event(1, AWAY, AWAY_KEEPER, (104, 34), (104, 34), ActionType.KEEPER_SAVE),
        make_event(2, AWAY, AWAY_KEEPER, (104, 34), (70, 20)),
    )
    match = Match(game_id=GAME, home_team_id=HOME, away_team_id=AWAY, events=events)

    (tag,) = detect(match)

    assert tag.evidence == {"won with": float(WonWith.KEEPER), "metres from own goal": 1.0}
    assert tag.span == (0, 1)
    assert tag.difficulty == 0.0


def test_a_set_piece_or_the_kickoff_after_a_goal_is_not_a_ball_win() -> None:
    assert detect(won_and_carried(9, OWN_HALF, won_with=ActionType.THROW_IN)) == ()
    match = lost_and_won_back(4, ON_THE_LINE)
    passed, failed_pass, interception, *rest = match.events
    scored = (
        passed,
        replace(failed_pass, action_type=ActionType.SHOT, result=Result.SUCCESS),
        replace(interception, action_type=ActionType.PASS, start_x=52.5, start_y=34),
        *rest,
    )

    tags = detect(replace(match, events=scored))

    assert [tag.action_id for tag in tags] == [4]


def test_a_new_half_starts_afresh() -> None:
    match = lost_and_won_back(4, ON_THE_LINE)
    second_half = tuple(
        replace(event, period_id=2) if event.action_id >= 2 else event for event in match.events
    )

    tags = detect(replace(match, events=second_half))

    assert [tag.action_id for tag in tags] == [4]


def test_how_the_ball_was_won_is_read_from_the_action() -> None:
    assert won_with(ActionType.TACKLE) is WonWith.TACKLE
    assert won_with(ActionType.INTERCEPTION) is WonWith.INTERCEPTION
    assert all(
        won_with(action) is WonWith.KEEPER
        for action in (
            ActionType.KEEPER_SAVE,
            ActionType.KEEPER_CLAIM,
            ActionType.KEEPER_PUNCH,
            ActionType.KEEPER_PICK_UP,
        )
    )
    assert won_with(ActionType.PASS) is WonWith.LOOSE_BALL
    assert won_with(ActionType.CLEARANCE) is WonWith.LOOSE_BALL
    assert WonWith.KEEPER.label == "the keeper"


@pytest.mark.parametrize(
    ("metres", "third"),
    [(0.0, "own third"), (34.9, "own third"), (THIRD, "middle third"), (70.0, "attacking third")],
)
def test_the_third_follows_the_metres_from_the_teams_own_goal(metres: float, third: str) -> None:
    assert pitch_third(metres) == third


@pytest.mark.parametrize("seed", range(3))
def test_in_simulated_play_every_change_of_hands_in_open_play_is_tagged_once(seed: int) -> None:
    played = simulated(seed)
    possessions = split_possessions(played.events)
    expected = [
        won.first
        for before, won in pairwise(possessions)
        if before.period_id == won.period_id
        and changes_hands_in_open_play(played.events[before.last], played.events[won.first])
    ]

    tags = detect(played)

    assert [tag.action_id for tag in tags] == expected
    assert len(tags) > 20
    assert all(tag.difficulty is not None and 0 <= tag.difficulty <= 1 for tag in tags)
    ways = {WonWith(int(tag.evidence["won with"])) for tag in tags}
    assert {WonWith.TACKLE, WonWith.INTERCEPTION, WonWith.KEEPER} <= ways
    for tag in tags:
        win = played.events[tag.action_id]
        attacks_towards_105 = win.team_id == HOME
        from_own_goal = win.start_x if attacks_towards_105 else 105 - win.start_x
        assert tag.evidence["metres from own goal"] == pytest.approx(from_own_goal, abs=0.05)
