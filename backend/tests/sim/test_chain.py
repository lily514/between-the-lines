import numpy as np
from hypothesis import given, settings
from hypothesis import strategies as st

from btl.schema.vocab import ActionType, Phase, Result
from btl.sim.chain import CENTRE_SPOT, SIX_YARD_DEPTH, Chain, Side, Start, kickoff, play_chain
from btl.sim.params import DEFAULT_PARAMS, SimParams
from btl.sim.pitch import PITCH_LENGTH, PITCH_WIDTH, Point
from btl.sim.shape import FOUR_FOUR_TWO, FOUR_THREE_THREE

HOME = Side(FOUR_THREE_THREE, 1.0)
AWAY = Side(FOUR_FOUR_TWO, 1.0)
IN_THE_BOX = Point(95, 34)
STRIKER = 9


def chain(start: Start, seed: int = 0, params: SimParams = DEFAULT_PARAMS) -> Chain:
    return play_chain(HOME, AWAY, start, np.random.default_rng(seed), params)


def on_pitch(point: Point) -> bool:
    return 0 <= point.x <= PITCH_LENGTH and 0 <= point.y <= PITCH_WIDTH


def test_a_kickoff_is_a_set_piece_pass_backwards_from_the_centre_spot() -> None:
    first = chain(kickoff(HOME)).steps[0]

    assert first.action_type is ActionType.PASS
    assert first.phase is Phase.SET_PIECE
    assert first.start == CENTRE_SPOT
    assert first.end.x < CENTRE_SPOT.x


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
    assert all(step.result is Result.SUCCESS for step in before_last)
    assert last.result is Result.FAIL or last.action_type is ActionType.SHOT
    for step in result.steps:
        assert on_pitch(step.start)
        assert on_pitch(step.end)
        assert step.duration > 0
    assert on_pitch(result.next_start.ball)


def test_a_goal_is_followed_by_the_other_teams_kickoff() -> None:
    sure_goal = SimParams(shot_share_in_box=1.0, goal_intercept=20.0)

    result = chain(Start(IN_THE_BOX, slot=STRIKER, won_with=ActionType.TACKLE), params=sure_goal)

    assert result.steps[-1].action_type is ActionType.SHOT
    assert result.steps[-1].result is Result.SUCCESS
    assert result.next_start == kickoff(AWAY, delay=sure_goal.goal_restart_delay)


def test_a_missed_shot_is_followed_by_the_keepers_kick_from_the_six_yard_box() -> None:
    sure_miss = SimParams(shot_share_in_box=1.0, goal_intercept=-50.0, save_share=0.0)

    result = chain(Start(IN_THE_BOX, slot=STRIKER, won_with=ActionType.TACKLE), params=sure_miss)

    assert result.steps[-1].action_type is ActionType.SHOT
    assert result.steps[-1].result is Result.FAIL
    assert result.next_start.won_with is None
    assert result.next_start.slot == 0  # the keeper
    assert result.next_start.ball.x == SIX_YARD_DEPTH


def test_a_saved_shot_hands_the_ball_to_the_keeper_in_front_of_their_goal() -> None:
    sure_save = SimParams(shot_share_in_box=1.0, goal_intercept=-50.0, save_share=1.0)

    result = chain(Start(IN_THE_BOX, slot=STRIKER, won_with=ActionType.TACKLE), params=sure_save)

    assert result.next_start.won_with is ActionType.KEEPER_SAVE
    assert result.next_start.slot == 0
    assert result.next_start.ball.x < 5
