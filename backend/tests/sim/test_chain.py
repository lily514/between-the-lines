import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from btl.schema.vocab import ActionType, BodyPart, Phase, Result
from btl.sim.chain import (
    CENTRE_SPOT,
    KEEPER_PICK_UP_DEPTH,
    SIX_YARD_DEPTH,
    Chain,
    Restart,
    Side,
    Start,
    Step,
    kickoff,
    play_chain,
)
from btl.sim.params import DEFAULT_PARAMS, PerThird, SimParams
from btl.sim.pitch import PITCH_LENGTH, PITCH_WIDTH, Point, mirror, on_pitch
from btl.sim.shape import FOUR_FOUR_TWO, FOUR_THREE_THREE

HOME = Side(FOUR_THREE_THREE, 1.0)
AWAY = Side(FOUR_FOUR_TWO, 1.0)
IN_THE_BOX = Point(95, 34)
STRIKER = 9


def chain(start: Start, seed: int = 0, params: SimParams = DEFAULT_PARAMS) -> Chain:
    return play_chain(HOME, AWAY, start, np.random.default_rng(seed), params)


CORNERS = (ActionType.CORNER_CROSSED, ActionType.CORNER_SHORT)


def is_corner_flag(point: Point) -> bool:
    return point.x == PITCH_LENGTH and point.y in (0, PITCH_WIDTH)


def tackled_in_the_box(params: SimParams, seed: int = 0) -> Chain:
    start = Start(IN_THE_BOX, slot=STRIKER, won_with=ActionType.TACKLE)
    return chain(start, seed, params)


def first_corner(steps: tuple[Step, ...]) -> int:
    return next(i for i, step in enumerate(steps) if step.action_type in CORNERS)


def test_a_kickoff_is_a_set_piece_pass_backwards_from_the_centre_spot() -> None:
    first = chain(kickoff(HOME)).steps[0]

    assert first.action_type is ActionType.PASS
    assert first.phase is Phase.SET_PIECE
    assert first.start == CENTRE_SPOT
    assert first.end.x < CENTRE_SPOT.x
    assert kickoff(HOME).restart is Restart.KICKOFF


def test_a_possession_starts_in_exactly_one_way() -> None:
    with pytest.raises(ValueError, match="either"):
        Start(CENTRE_SPOT, slot=9)
    with pytest.raises(ValueError, match="either"):
        Start(CENTRE_SPOT, 9, won_with=ActionType.TACKLE, restart=Restart.KICKOFF)


def test_a_possession_won_by_an_interception_opens_with_it_as_a_transition() -> None:
    start = Start(Point(40, 20), slot=6, won_with=ActionType.INTERCEPTION)

    steps = chain(start).steps

    assert steps[0].action_type is ActionType.INTERCEPTION
    assert steps[0].result is Result.SUCCESS
    assert steps[0].slot == 6
    assert steps[0].phase is Phase.TRANSITION


@settings(max_examples=200)
@given(st.integers(min_value=0, max_value=2**32 - 1))
def test_a_chain_succeeds_until_its_last_action_and_stays_on_the_pitch(seed: int) -> None:
    result = chain(kickoff(HOME), seed)

    *before_last, last = result.steps
    for step, after in zip(before_last, result.steps[1:], strict=True):
        # A failed cross or a missed shot can go out for the team's own corner.
        assert step.result is Result.SUCCESS or after.action_type in CORNERS
    assert last.result is Result.FAIL or last.action_type is ActionType.SHOT
    for step in result.steps:
        assert on_pitch(step.start)
        assert on_pitch(step.end)
        assert step.duration > 0
    assert on_pitch(result.next_start.ball)


@settings(max_examples=200)
@given(st.integers(min_value=0, max_value=2**32 - 1))
def test_a_ball_that_goes_out_restarts_in_the_right_place(seed: int) -> None:
    result = chain(kickoff(HOME), seed)

    last, start = result.steps[-1], result.next_start
    went_out = last.action_type is not ActionType.SHOT and (
        last.end.y in (0, PITCH_WIDTH) or last.end.x in (0, PITCH_LENGTH)
    )
    if not went_out:
        assert start.restart in (None, Restart.GOAL_KICK, Restart.KICKOFF)
    elif last.end.x == PITCH_LENGTH:
        assert start.restart is Restart.GOAL_KICK
        assert start.ball.x == SIX_YARD_DEPTH
    elif last.end.x == 0:
        assert start.restart is Restart.CORNER
        assert is_corner_flag(start.ball)
        assert (start.ball.y == 0) == (mirror(last.end).y < PITCH_WIDTH / 2)
    else:
        assert start.restart is Restart.THROW_IN
        assert start.ball == mirror(last.end)


def test_a_throw_in_is_a_set_piece_thrown_from_the_touchline() -> None:
    start = Start(Point(60, 0), slot=STRIKER, restart=Restart.THROW_IN)

    first = chain(start).steps[0]

    assert first.action_type is ActionType.THROW_IN
    assert first.bodypart is BodyPart.OTHER
    assert first.phase is Phase.SET_PIECE
    assert first.start == Point(60, 0)


def test_a_corner_is_a_set_piece_from_the_flag() -> None:
    start = Start(Point(PITCH_LENGTH, PITCH_WIDTH), slot=STRIKER, restart=Restart.CORNER)

    firsts = [chain(start, seed).steps[0] for seed in range(20)]

    assert {step.action_type for step in firsts} == set(CORNERS)
    assert all(step.phase is Phase.SET_PIECE for step in firsts)
    assert all(step.start == start.ball for step in firsts)


def test_a_deflected_shot_gives_the_same_team_a_corner() -> None:
    deflected = SimParams(
        shot_share_in_box=1.0, goal_intercept=-50.0, save_share=0.0, miss_out_for_corner=1.0
    )

    steps = tackled_in_the_box(deflected).steps
    corner = first_corner(steps)

    shot = steps[corner - 1]
    assert shot.action_type is ActionType.SHOT
    assert shot.result is Result.FAIL
    assert shot.duration == deflected.shot_flight + deflected.corner_delay
    assert is_corner_flag(steps[corner].start)
    assert steps[corner].phase is Phase.SET_PIECE


def test_a_deflected_cross_gives_the_same_team_a_corner() -> None:
    deflected = SimParams(cross_share_on_wing=1.0, cross_success=0.0, cross_out_for_corner=1.0)
    on_the_wing = Start(Point(90, 5), slot=STRIKER, won_with=ActionType.TACKLE)

    steps = chain(on_the_wing, params=deflected).steps

    assert steps[1].action_type is ActionType.CROSS
    assert steps[1].result is Result.FAIL
    assert steps[2].action_type in CORNERS
    assert steps[2].start == Point(PITCH_LENGTH, 0)


def test_a_goal_is_followed_by_the_other_teams_kickoff() -> None:
    sure_goal = SimParams(shot_share_in_box=1.0, goal_intercept=20.0)

    result = tackled_in_the_box(sure_goal)

    assert result.steps[-1].action_type is ActionType.SHOT
    assert result.steps[-1].result is Result.SUCCESS
    assert result.next_start == kickoff(AWAY, delay=sure_goal.goal_restart_delay)


def test_a_missed_shot_is_followed_by_a_goal_kick_from_the_six_yard_box() -> None:
    sure_miss = SimParams(
        shot_share_in_box=1.0, goal_intercept=-50.0, save_share=0.0, miss_out_for_corner=0.0
    )

    result = tackled_in_the_box(sure_miss)

    assert result.steps[-1].action_type is ActionType.SHOT
    assert result.steps[-1].result is Result.FAIL
    assert result.next_start.restart is Restart.GOAL_KICK
    assert result.next_start.slot == 0  # the keeper
    assert result.next_start.ball.x == SIX_YARD_DEPTH
    assert result.next_start.delay == sure_miss.goal_kick_delay


def test_a_saved_shot_hands_the_ball_to_the_keeper_in_front_of_their_goal() -> None:
    sure_save = SimParams(shot_share_in_box=1.0, goal_intercept=-50.0, save_share=1.0)

    result = tackled_in_the_box(sure_save)

    assert result.next_start.won_with is ActionType.KEEPER_SAVE
    assert result.next_start.slot == 0
    assert result.next_start.ball.x < 5


def test_a_pass_running_through_in_front_of_goal_is_picked_up_by_the_keeper() -> None:
    overhit_at_goal = SimParams(
        shot_share_in_box=0.0,
        shot_share_in_range=0.0,
        dribble_share=PerThird(0.0, 0.0, 0.0),
        pass_kappa=PerThird(500.0, 500.0, 500.0),
        pass_length_mean=PerThird(8.0, 8.0, 8.0),
        pass_success=PerThird(0.0, 0.0, 0.0),
        run_on=(30.0, 30.0),
        keeper_pick_up_share=1.0,
    )
    start = Start(Point(80, 34), slot=STRIKER, won_with=ActionType.TACKLE)

    result = chain(start, params=overhit_at_goal)

    last = result.steps[-1]
    assert last.action_type is ActionType.PASS
    assert last.result is Result.FAIL
    assert last.end.x == PITCH_LENGTH - KEEPER_PICK_UP_DEPTH
    assert result.next_start.won_with is ActionType.KEEPER_PICK_UP
    assert result.next_start.slot == 0  # the keeper
