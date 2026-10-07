import math

import pytest

from btl.sim.pitch import (
    GOAL_CENTRE,
    Lane,
    Point,
    Third,
    Zone,
    clamp_to_pitch,
    distance,
    distance_to_goal,
    goal_angle,
    in_penalty_area,
    mirror,
    zone_of,
)


@pytest.mark.parametrize(
    ("point", "zone"),
    [
        (Point(10, 34), Zone(Third.DEFENSIVE, Lane.CENTRE)),
        (Point(50, 60), Zone(Third.MIDDLE, Lane.LEFT)),
        (Point(90, 5), Zone(Third.ATTACKING, Lane.RIGHT)),
    ],
)
def test_zone_of_finds_the_third_and_lane(point: Point, zone: Zone) -> None:
    assert zone_of(point) == zone


@pytest.mark.parametrize(
    ("point", "inside"),
    [(Point(95, 34), True), (Point(95, 5), False), (Point(80, 34), False)],
)
def test_in_penalty_area(point: Point, inside: bool) -> None:
    assert in_penalty_area(point) is inside


def test_penalty_spot_is_eleven_metres_from_goal() -> None:
    assert distance_to_goal(Point(94, 34)) == pytest.approx(11)


def test_goal_looks_wider_from_closer_and_more_central_spots() -> None:
    assert goal_angle(Point(94, 34)) > goal_angle(Point(80, 34)) > goal_angle(Point(80, 10))
    assert goal_angle(Point(105, 10)) == pytest.approx(0)


def test_mirroring_twice_gives_back_the_same_point() -> None:
    point = Point(12.5, 40)

    assert mirror(mirror(point)) == point
    assert mirror(GOAL_CENTRE) == Point(0, 34)


def test_clamp_keeps_points_inside_the_lines() -> None:
    assert clamp_to_pitch(Point(-3, 70), margin=1) == Point(1, 67)


def test_distance() -> None:
    assert distance(Point(0, 0), Point(3, 4)) == pytest.approx(5)
    assert math.isclose(distance(Point(1, 1), Point(1, 1)), 0)
