import math
from itertools import pairwise

import numpy as np
import pytest

from btl.league.league import Role
from btl.plant.templates import GAP_WIDTHS, LineBreakingTemplate
from btl.schema.vocab import ActionType
from btl.sim.chain import Restart, Side, Start
from btl.sim.params import DEFAULT_PARAMS
from btl.sim.pitch import Point, distance
from btl.sim.script import Script
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
    assert script.ball == answer.end


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
    assert attackers[script.slot] == answer.end


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
