"""Pitch geometry, in metres, from the point of view of a team attacking towards x = 105.

Facing the opponent's goal, the left touchline is y = 68 and the right is y = 0.
"""

import math
from dataclasses import dataclass
from enum import Enum

PITCH_LENGTH = 105.0
PITCH_WIDTH = 68.0
GOAL_WIDTH = 7.32
PENALTY_AREA_DEPTH = 16.5
PENALTY_AREA_WIDTH = 40.32

_BOX_SIDE = (PITCH_WIDTH - PENALTY_AREA_WIDTH) / 2


@dataclass(frozen=True, slots=True)
class Point:
    """A position on the pitch."""

    x: float
    y: float


GOAL_CENTRE = Point(PITCH_LENGTH, PITCH_WIDTH / 2)


class Third(Enum):
    """Which third of the pitch, from the attacking team's point of view."""

    DEFENSIVE = "defensive"
    MIDDLE = "middle"
    ATTACKING = "attacking"


class Lane(Enum):
    """Which channel of the pitch: the two wings outside the penalty area, or the centre."""

    RIGHT = "right"
    CENTRE = "centre"
    LEFT = "left"


@dataclass(frozen=True, slots=True)
class Zone:
    """A coarse area of the pitch: one of nine third-and-lane combinations."""

    third: Third
    lane: Lane


def distance(a: Point, b: Point) -> float:
    """Straight-line distance in metres."""
    return math.hypot(a.x - b.x, a.y - b.y)


def distance_to_goal(point: Point) -> float:
    """Distance to the centre of the goal being attacked."""
    return distance(point, GOAL_CENTRE)


def goal_angle(point: Point) -> float:
    """How wide the goal mouth looks from a point, in radians.

    Zero on the goal line outside the posts, largest close in front of goal.
    """
    near_post = Point(PITCH_LENGTH, GOAL_CENTRE.y - GOAL_WIDTH / 2)
    far_post = Point(PITCH_LENGTH, GOAL_CENTRE.y + GOAL_WIDTH / 2)
    to_near = math.atan2(near_post.y - point.y, near_post.x - point.x)
    to_far = math.atan2(far_post.y - point.y, far_post.x - point.x)
    return abs(to_far - to_near)


def zone_of(point: Point) -> Zone:
    """The zone a point falls in."""
    if point.x < PITCH_LENGTH / 3:
        third = Third.DEFENSIVE
    elif point.x < 2 * PITCH_LENGTH / 3:
        third = Third.MIDDLE
    else:
        third = Third.ATTACKING
    if point.y < _BOX_SIDE:
        lane = Lane.RIGHT
    elif point.y > PITCH_WIDTH - _BOX_SIDE:
        lane = Lane.LEFT
    else:
        lane = Lane.CENTRE
    return Zone(third, lane)


def in_penalty_area(point: Point) -> bool:
    """Whether a point is inside the penalty area being attacked."""
    return point.x >= PITCH_LENGTH - PENALTY_AREA_DEPTH and _BOX_SIDE <= point.y <= (
        PITCH_WIDTH - _BOX_SIDE
    )


def clamp_to_pitch(point: Point, margin: float = 0.0) -> Point:
    """The nearest point on the pitch, at least ``margin`` metres inside the lines."""
    return Point(
        min(max(point.x, margin), PITCH_LENGTH - margin),
        min(max(point.y, margin), PITCH_WIDTH - margin),
    )


def mirror(point: Point) -> Point:
    """The same spot seen from the other team's attacking direction."""
    return Point(PITCH_LENGTH - point.x, PITCH_WIDTH - point.y)
