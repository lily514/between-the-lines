import math
from itertools import pairwise

import numpy as np
import pytest

from btl.league.league import Role
from btl.plant.templates import (
    GAP_WIDTHS,
    SECONDS_TO_BOX,
    CounterAttackTemplate,
    CounterPressTemplate,
    LineBreakingTemplate,
)
from btl.schema.vocab import ActionType, Result
from btl.sim.chain import Restart, Side, Start
from btl.sim.params import DEFAULT_PARAMS
from btl.sim.pitch import PITCH_LENGTH, Point, distance, in_penalty_area, mirror
from btl.sim.script import PlayOn, Script
from btl.sim.shape import FOUR_FOUR_TWO, FOUR_THREE_THREE

ATTACK = Side(FOUR_FOUR_TWO, 1.0)
DEFENCE = Side(FOUR_THREE_THREE, 1.0)
WON_IN_MIDFIELD = Start(Point(40, 20), 6, ActionType.INTERCEPTION)


def write(difficulty: int, seed: int = 0) -> Script:
    return LineBreakingTemplate().write(
        ATTACK, DEFENCE, WON_IN_MIDFIELD, difficulty, np.random.default_rng(seed), DEFAULT_PARAMS
    )


def midfield_line(script: Script) -> list[Point]:
    _, defenders = script.shapes[script.answer]
    return sorted(
        (
            point
            for slot, point in zip(DEFENCE.formation.slots, defenders, strict=True)
            if slot.role is Role.MIDFIELDER
        ),
        key=lambda point: point.y,
    )


@pytest.mark.parametrize(
    ("start", "fits"),
    [
        (WON_IN_MIDFIELD, True),
        (Start(Point(40, 20), 6, ActionType.TACKLE), True),
        (Start(Point(75, 20), 6, ActionType.INTERCEPTION), False),
        (Start(Point(10, 20), 0, ActionType.KEEPER_SAVE), False),
        (Start(Point(40, 0), 6, restart=Restart.THROW_IN), False),
    ],
)
def test_needs_the_ball_won_in_open_play_in_the_teams_own_two_thirds(
    start: Start, fits: bool
) -> None:
    assert LineBreakingTemplate().fits(start) is fits


def test_the_ball_is_won_laid_off_then_passed_forward() -> None:
    script = write(1)
    won, lay_off, answer = script.steps

    assert won.action_type is ActionType.INTERCEPTION
    assert lay_off.start == won.end and answer.start == lay_off.end
    assert (script.pause, script.answer) == (1, 2)
    assert answer.end.x > answer.start.x
    assert isinstance(script.then, PlayOn) and script.then.ball == answer.end


@pytest.mark.parametrize("difficulty", [1, 2, 3])
def test_the_pass_goes_through_a_gap_of_the_levels_width(difficulty: int) -> None:
    script = write(difficulty)
    answer = script.steps[script.answer]
    line = midfield_line(script)
    line_x = (min(point.x for point in line) + max(point.x for point in line)) / 2

    along = (line_x - answer.start.x) / (answer.end.x - answer.start.x)
    crossing_y = answer.start.y + along * (answer.end.y - answer.start.y)
    left, right = next((a, b) for a, b in pairwise(line) if a.y <= crossing_y <= b.y)
    assert math.isclose(distance(left, right), GAP_WIDTHS[difficulty])
    assert answer.start.x < min(point.x for point in line)
    assert answer.end.x > max(point.x for point in line)


def test_the_pass_ends_short_of_the_back_line() -> None:
    script = write(2)
    _, defenders = script.shapes[script.answer]
    back_line = [
        point
        for slot, point in zip(DEFENCE.formation.slots, defenders, strict=True)
        if slot.role is Role.DEFENDER
    ]

    assert script.steps[script.answer].end.x < min(point.x for point in back_line)


def test_the_passer_and_receiver_stand_where_the_ball_is() -> None:
    script = write(2)
    attackers, _ = script.shapes[script.answer]
    answer = script.steps[script.answer]

    assert attackers[answer.slot] == answer.start
    assert isinstance(script.then, PlayOn)
    assert attackers[script.then.slot] == answer.end


@pytest.mark.parametrize(("difficulty", "decoy"), [(1, False), (2, False), (3, True)])
def test_only_the_hardest_level_has_a_free_teammate_to_the_side(
    difficulty: int, decoy: bool
) -> None:
    script = write(difficulty)
    attackers, _ = script.shapes[script.answer]
    passer = script.steps[script.answer].start

    beside = [
        point
        for point in attackers
        if point != passer and abs(point.x - passer.x) <= 2 and 10 <= abs(point.y - passer.y) <= 14
    ]
    assert bool(beside) is decoy


def test_the_same_random_stream_writes_the_same_moment() -> None:
    assert write(3, seed=5) == write(3, seed=5)


WON_DEEP = Start(Point(25, 30), 2, ActionType.TACKLE)


def write_press(difficulty: int, seed: int = 0) -> Script:
    return CounterPressTemplate().write(
        ATTACK, DEFENCE, WON_DEEP, difficulty, np.random.default_rng(seed), DEFAULT_PARAMS
    )


@pytest.mark.parametrize(
    ("start", "fits"),
    [
        (WON_DEEP, True),
        (Start(Point(50, 30), 6, ActionType.INTERCEPTION), False),
        (Start(Point(25, 0), 2, restart=Restart.THROW_IN), False),
    ],
)
def test_a_counter_press_needs_the_opponent_to_win_the_ball_in_its_own_half(
    start: Start, fits: bool
) -> None:
    assert CounterPressTemplate().fits(start) is fits


@pytest.mark.parametrize(("difficulty", "passes"), [(1, 0), (2, 1), (3, 2)])
def test_the_opponent_keeps_the_ball_longer_at_harder_levels(difficulty: int, passes: int) -> None:
    won, *completed, cut_out = write_press(difficulty).steps

    assert won.action_type is ActionType.TACKLE
    assert len(completed) == passes
    assert all(step.result is Result.SUCCESS for step in completed)
    assert cut_out.result is Result.FAIL


@pytest.mark.parametrize("seed", range(20))
def test_the_ball_is_won_back_quickly_in_the_opponents_half(seed: int) -> None:
    script = write_press(3, seed)

    assert isinstance(script.then, Start)
    assert script.then.won_with is ActionType.INTERCEPTION
    assert script.then.ball == mirror(script.steps[-1].end)
    assert script.then.ball.x > PITCH_LENGTH / 2
    assert sum(step.duration for step in script.steps) < 5
    assert (script.pause, script.answer) == (0, len(script.steps))


WON_IN_OWN_HALF = Start(Point(35, 40), 7, ActionType.INTERCEPTION)


def write_counter(difficulty: int, seed: int = 0) -> Script:
    return CounterAttackTemplate().write(
        ATTACK, DEFENCE, WON_IN_OWN_HALF, difficulty, np.random.default_rng(seed), DEFAULT_PARAMS
    )


@pytest.mark.parametrize(
    ("start", "fits"),
    [
        (WON_IN_OWN_HALF, True),
        (Start(Point(25, 20), 2, ActionType.TACKLE), True),
        (Start(Point(20, 30), 2, ActionType.TACKLE), False),
        (Start(Point(60, 30), 6, ActionType.INTERCEPTION), False),
        (Start(Point(35, 0), 2, restart=Restart.THROW_IN), False),
    ],
)
def test_a_counter_attack_needs_the_ball_won_in_open_play_in_the_teams_own_half(
    start: Start, fits: bool
) -> None:
    assert CounterAttackTemplate().fits(start) is fits


def test_the_ball_is_won_played_forward_into_the_box_and_touched_there() -> None:
    script = write_counter(1)
    won, forward, into_the_box, touch = script.steps

    assert won.action_type is ActionType.INTERCEPTION
    assert forward.start == won.end and forward.end.x > forward.start.x
    assert into_the_box.start == forward.end and in_penalty_area(into_the_box.end)
    assert touch.action_type is ActionType.DRIBBLE and touch.start == into_the_box.end
    # The winner plays it forward, a runner plays it into the box, and a third player is there.
    assert won.slot == forward.slot
    assert len({won.slot, into_the_box.slot, touch.slot}) == 3
    assert (script.pause, script.answer) == (0, 3)
    assert isinstance(script.then, PlayOn) and script.then.ball == touch.end


@pytest.mark.parametrize("difficulty", [1, 2, 3])
@pytest.mark.parametrize("seed", range(10))
def test_the_run_to_the_box_takes_as_long_as_the_level_says(difficulty: int, seed: int) -> None:
    script = write_counter(difficulty, seed)

    low, high = SECONDS_TO_BOX[difficulty]
    to_the_box = sum(step.duration for step in script.steps[:-1])
    assert low <= to_the_box <= high
    assert all(step.duration > 0 for step in script.steps)


def test_the_same_random_stream_writes_the_same_counter_attack() -> None:
    assert write_counter(2, seed=5) == write_counter(2, seed=5)
