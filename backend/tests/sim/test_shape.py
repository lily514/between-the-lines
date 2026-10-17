from statistics import fmean

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st

from btl.league.league import Role
from btl.sim.pitch import PITCH_LENGTH, PITCH_WIDTH, Point
from btl.sim.shape import (
    FORMATIONS,
    FOUR_FOUR_TWO,
    FOUR_THREE_THREE,
    Formation,
    Slot,
    offside_line,
    place_receiver,
    place_teams,
    team_shape,
)

balls = st.builds(
    Point,
    st.floats(min_value=0, max_value=PITCH_LENGTH),
    st.floats(min_value=0, max_value=PITCH_WIDTH),
)
formations = st.sampled_from(list(FORMATIONS.values()))


def outfield(formation: Formation, positions: tuple[Point, ...]) -> list[Point]:
    return [
        point
        for slot, point in zip(formation.slots, positions, strict=True)
        if slot.role is not Role.GOALKEEPER
    ]


def spread(points: list[Point]) -> float:
    """Mean distance from the group's centre: smaller means more compact."""
    centre = Point(fmean(p.x for p in points), fmean(p.y for p in points))
    return fmean(((p.x - centre.x) ** 2 + (p.y - centre.y) ** 2) ** 0.5 for p in points)


def test_every_formation_has_eleven_slots_and_one_goalkeeper() -> None:
    for formation in FORMATIONS.values():
        assert len(formation.slots) == 11
        assert sum(slot.role is Role.GOALKEEPER for slot in formation.slots) == 1


def test_a_formation_without_a_goalkeeper_is_rejected() -> None:
    with pytest.raises(ValueError, match="goalkeepers"):
        Formation("broken", tuple(Slot(Role.DEFENDER, 0, 0.5) for _ in range(11)))


@given(balls, formations, formations, st.integers(min_value=0, max_value=1000))
def test_everyone_is_on_the_pitch(
    ball: Point, attack: Formation, defence: Formation, seed: int
) -> None:
    attackers, defenders = place_teams(attack, defence, ball, np.random.default_rng(seed))

    assert len(attackers) == len(defenders) == 11
    for point in (*attackers, *defenders):
        assert 0 <= point.x <= PITCH_LENGTH
        assert 0 <= point.y <= PITCH_WIDTH


@given(balls, formations)
def test_a_team_is_more_compact_without_the_ball(ball: Point, formation: Formation) -> None:
    with_ball = outfield(formation, team_shape(formation, ball, in_possession=True))
    without_ball = outfield(formation, team_shape(formation, ball, in_possession=False))

    assert spread(without_ball) < spread(with_ball)


def test_both_blocks_move_up_the_pitch_with_the_ball() -> None:
    deep_attack, deep_defence = place_teams(FOUR_THREE_THREE, FOUR_FOUR_TWO, Point(30, 34))
    high_attack, high_defence = place_teams(FOUR_THREE_THREE, FOUR_FOUR_TWO, Point(80, 34))

    def mean_x(formation: Formation, positions: tuple[Point, ...]) -> float:
        return fmean(p.x for p in outfield(formation, positions))

    assert mean_x(FOUR_THREE_THREE, high_attack) > mean_x(FOUR_THREE_THREE, deep_attack) + 10
    assert mean_x(FOUR_FOUR_TWO, high_defence) > mean_x(FOUR_FOUR_TWO, deep_defence) + 10


def test_both_blocks_slide_towards_the_ball_side() -> None:
    _, right_defence = place_teams(FOUR_THREE_THREE, FOUR_FOUR_TWO, Point(50, 5))
    _, left_defence = place_teams(FOUR_THREE_THREE, FOUR_FOUR_TWO, Point(50, 63))

    left_y = fmean(p.y for p in outfield(FOUR_FOUR_TWO, left_defence))
    right_y = fmean(p.y for p in outfield(FOUR_FOUR_TWO, right_defence))
    assert left_y > right_y + 10


def test_defenders_are_goal_side_of_the_ball_in_midfield() -> None:
    _, defenders = place_teams(FOUR_THREE_THREE, FOUR_FOUR_TWO, Point(50, 34))

    back_line = [
        point
        for slot, point in zip(FOUR_FOUR_TWO.slots, defenders, strict=True)
        if slot.role is Role.DEFENDER
    ]
    assert all(point.x > 50 for point in back_line)


def test_goalkeepers_stay_near_their_own_goals() -> None:
    attackers, defenders = place_teams(FOUR_THREE_THREE, FOUR_FOUR_TWO, Point(70, 34))

    assert attackers[0].x < 20
    assert defenders[0].x > PITCH_LENGTH - 20


def test_same_seed_gives_the_same_jitter_and_no_rng_gives_none() -> None:
    ball = Point(60, 30)

    first = place_teams(FOUR_THREE_THREE, FOUR_FOUR_TWO, ball, np.random.default_rng(1))
    second = place_teams(FOUR_THREE_THREE, FOUR_FOUR_TWO, ball, np.random.default_rng(1))
    exact = place_teams(FOUR_THREE_THREE, FOUR_FOUR_TWO, ball)

    assert first == second
    assert first != exact
    assert exact[0] == team_shape(FOUR_THREE_THREE, ball, in_possession=True)


KEEPER_AND_BACK_LINE = (Point(103, 34), Point(80, 20), Point(78, 40), Point(85, 50))


def test_the_offside_line_is_the_second_last_defender_unless_the_ball_or_halfway_is_further() -> (
    None
):
    assert offside_line(KEEPER_AND_BACK_LINE, Point(60, 34)) == 85
    assert offside_line(KEEPER_AND_BACK_LINE, Point(90, 34)) == 90
    deep = (Point(103, 34), Point(40, 34))
    assert offside_line(deep, Point(30, 34)) == PITCH_LENGTH / 2


@given(st.integers(min_value=0, max_value=2**32 - 1))
def test_a_flagged_receiver_stands_past_the_line_in_line_with_the_pass(seed: int) -> None:
    attackers = (Point(10, 34), Point(70, 30), Point(75, 20))
    end = Point(95, 25)

    placed = place_receiver(
        attackers, KEEPER_AND_BACK_LINE, Point(70, 30), end, 2, True, np.random.default_rng(seed)
    )

    assert 85 < placed[2].x <= 85 + 4
    assert placed[2].y == end.y
    assert placed[:2] == attackers[:2]


@given(st.integers(min_value=0, max_value=2**32 - 1))
def test_an_unflagged_receiver_past_the_line_is_pulled_back_level_or_behind(seed: int) -> None:
    attackers = (Point(10, 34), Point(70, 30), Point(92, 20))
    rng = np.random.default_rng(seed)

    placed = place_receiver(
        attackers, KEEPER_AND_BACK_LINE, Point(70, 30), Point(95, 25), 2, False, rng
    )

    assert 85 - 2 <= placed[2].x <= 85
    assert placed[2].y == 20


def test_an_onside_receiver_who_isnt_flagged_stays_put() -> None:
    attackers = (Point(10, 34), Point(70, 30), Point(80, 20))
    rng = np.random.default_rng(0)

    placed = place_receiver(
        attackers, KEEPER_AND_BACK_LINE, Point(70, 30), Point(95, 25), 2, False, rng
    )

    assert placed == attackers
