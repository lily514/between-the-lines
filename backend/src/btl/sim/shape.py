"""Where the 22 players stand, worked out from formations and the ball.

There is no player tracking. Instead each team's positions are a deterministic function of
its formation, the ball's position, and whether it has the ball, plus optional random
jitter. Each team reasons in its own attacking direction (towards x = 105); `place_teams`
returns both teams in the attacking team's direction.
"""

from dataclasses import dataclass

from numpy.random import Generator

from btl.league.league import Role
from btl.sim.pitch import PITCH_LENGTH, PITCH_WIDTH, Point, clamp_to_pitch, mirror


@dataclass(frozen=True, slots=True)
class Slot:
    """One position in a formation.

    ``depth`` runs from 0 (the back line) to 1 (the front line) within the outfield block.
    ``across`` runs from 0 (the right touchline side, y = 0) to 1 (the left, y = 68).
    Goalkeepers ignore both.
    """

    role: Role
    depth: float
    across: float


@dataclass(frozen=True, slots=True)
class Formation:
    """A named set of 11 slots, exactly one of them a goalkeeper."""

    name: str
    slots: tuple[Slot, ...]

    def __post_init__(self) -> None:
        """Check the formation has 11 slots and one goalkeeper."""
        if len(self.slots) != 11:
            raise ValueError(f"{self.name} has {len(self.slots)} slots, not 11")
        keepers = sum(slot.role is Role.GOALKEEPER for slot in self.slots)
        if keepers != 1:
            raise ValueError(f"{self.name} has {keepers} goalkeepers, not 1")


def _line(role: Role, depth: float, count: int) -> tuple[Slot, ...]:
    """``count`` slots spread evenly across the pitch at one depth."""
    return tuple(Slot(role, depth, (index + 0.5) / count) for index in range(count))


_KEEPER = Slot(Role.GOALKEEPER, 0.0, 0.5)

FOUR_FOUR_TWO = Formation(
    "4-4-2",
    (
        _KEEPER,
        *_line(Role.DEFENDER, 0.0, 4),
        *_line(Role.MIDFIELDER, 0.5, 4),
        *_line(Role.FORWARD, 1.0, 2),
    ),
)
FOUR_THREE_THREE = Formation(
    "4-3-3",
    (
        _KEEPER,
        *_line(Role.DEFENDER, 0.0, 4),
        *_line(Role.MIDFIELDER, 0.45, 3),
        *_line(Role.FORWARD, 1.0, 3),
    ),
)
FORMATIONS = {formation.name: formation for formation in (FOUR_FOUR_TWO, FOUR_THREE_THREE)}

# How long (goal to goal) and wide the outfield block is. Teams stretch with the ball and
# squeeze without it, which is what makes gaps between the lines appear and close.
IN_POSSESSION_LENGTH = 40.0
OUT_OF_POSSESSION_LENGTH = 28.0
IN_POSSESSION_WIDTH = 56.0
OUT_OF_POSSESSION_WIDTH = 40.0

# How far the block's centre slides towards the ball's side, as a fraction of the gap.
IN_POSSESSION_BALL_PULL = 0.25
OUT_OF_POSSESSION_BALL_PULL = 0.45

# Where the back line sits relative to the ball, in the team's own direction, and its limits.
IN_POSSESSION_BACK_LINE_GAP = 30.0
OUT_OF_POSSESSION_BACK_LINE_GAP = 18.0
BACK_LINE_RANGE = (10.0, 55.0)

KEEPER_LINE_RANGE = (4.0, 16.0)
DEFAULT_JITTER = 1.5  # metres, standard deviation
_MARGIN = 0.5


def _clamp(value: float, low: float, high: float) -> float:
    return min(max(value, low), high)


def team_shape(formation: Formation, ball: Point, in_possession: bool) -> tuple[Point, ...]:
    """Where a team's 11 players stand, in the team's own attacking direction.

    Args:
        formation: The team's formation.
        ball: The ball's position, in the team's own attacking direction.
        in_possession: Whether this team has the ball.

    Returns:
        One position per formation slot, in slot order. No randomness.
    """
    if in_possession:
        length, width, pull, gap = (
            IN_POSSESSION_LENGTH,
            IN_POSSESSION_WIDTH,
            IN_POSSESSION_BALL_PULL,
            IN_POSSESSION_BACK_LINE_GAP,
        )
    else:
        length, width, pull, gap = (
            OUT_OF_POSSESSION_LENGTH,
            OUT_OF_POSSESSION_WIDTH,
            OUT_OF_POSSESSION_BALL_PULL,
            OUT_OF_POSSESSION_BACK_LINE_GAP,
        )
    back_x = _clamp(ball.x - gap, *BACK_LINE_RANGE)
    centre_y = PITCH_WIDTH / 2 + (ball.y - PITCH_WIDTH / 2) * pull
    centre_y = _clamp(centre_y, width / 2, PITCH_WIDTH - width / 2)
    keeper_x = _clamp(back_x * 0.25, *KEEPER_LINE_RANGE)
    keeper_y = PITCH_WIDTH / 2 + (ball.y - PITCH_WIDTH / 2) * 0.15

    positions: list[Point] = []
    for slot in formation.slots:
        if slot.role is Role.GOALKEEPER:
            point = Point(keeper_x, keeper_y)
        else:
            point = Point(back_x + slot.depth * length, centre_y + (slot.across - 0.5) * width)
        positions.append(clamp_to_pitch(point, _MARGIN))
    return tuple(positions)


def _jitter(positions: tuple[Point, ...], rng: Generator, sd: float) -> tuple[Point, ...]:
    return tuple(
        clamp_to_pitch(
            Point(point.x + sd * rng.standard_normal(), point.y + sd * rng.standard_normal()),
            _MARGIN,
        )
        for point in positions
    )


def place_teams(
    attack: Formation,
    defence: Formation,
    ball: Point,
    rng: Generator | None = None,
    jitter: float = DEFAULT_JITTER,
) -> tuple[tuple[Point, ...], tuple[Point, ...]]:
    """Positions of both teams around the ball, in the attacking team's direction.

    Args:
        attack: Formation of the team with the ball.
        defence: Formation of the team without it.
        ball: The ball's position, in the attacking team's direction.
        rng: The shape model's random stream. Without one, there is no jitter.
        jitter: Standard deviation of the random offset added to each player, in metres.

    Returns:
        ``(attacking_positions, defending_positions)``, each in its formation's slot order.
    """
    attackers = team_shape(attack, ball, in_possession=True)
    defenders = tuple(
        mirror(point) for point in team_shape(defence, mirror(ball), in_possession=False)
    )
    if rng is not None and jitter > 0:
        attackers = _jitter(attackers, rng, jitter)
        defenders = _jitter(defenders, rng, jitter)
    return attackers, defenders


HALFWAY = PITCH_LENGTH / 2
CENTRE_CIRCLE_RADIUS = 9.15
# How far inside their own half, and outside the centre circle, players stand at a kick-off.
KICKOFF_MARGIN = 1.0


def kickoff_shape(
    attackers: tuple[Point, ...], defenders: tuple[Point, ...]
) -> tuple[tuple[Point, ...], tuple[Point, ...]]:
    """Both teams lined up for a kick-off, from their shapes with the ball on the centre spot.

    At a kick-off every player stands in their own half, and the team not kicking off stays
    outside the centre circle until the ball is played. The in-play shape pushes both front
    lines over halfway, so players who have strayed step back to the halfway line, and
    defenders inside the circle step straight out from the spot to its edge. Everyone else
    keeps their place.

    Args:
        attackers: The team kicking off, as `place_teams` gives it.
        defenders: The other team, in the same direction.

    Returns:
        ``(attacking_positions, defending_positions)``, in the same slot order.
    """
    centre = Point(HALFWAY, PITCH_WIDTH / 2)
    reach = CENTRE_CIRCLE_RADIUS + KICKOFF_MARGIN

    def outside_circle(point: Point) -> Point:
        dx, dy = point.x - centre.x, point.y - centre.y
        distance = (dx * dx + dy * dy) ** 0.5
        if distance >= reach:
            return point
        if distance == 0:
            return Point(centre.x + reach, centre.y)
        return Point(centre.x + dx * reach / distance, centre.y + dy * reach / distance)

    own_half = tuple(Point(min(p.x, HALFWAY - KICKOFF_MARGIN), p.y) for p in attackers)
    their_half = tuple(
        outside_circle(Point(max(p.x, HALFWAY + KICKOFF_MARGIN), p.y)) for p in defenders
    )
    return own_half, their_half


# How far beyond the offside line a receiver flagged offside stands, and how far behind it an
# unflagged receiver who would be offside is pulled back to.
OFFSIDE_MARGIN = (0.5, 4.0)
ONSIDE_MARGIN = (0.0, 2.0)


def offside_line(defenders: tuple[Point, ...], ball: Point) -> float:
    """The x past which an attacker is in an offside position, attacking towards x = 105.

    By the Laws, an attacker is in an offside position when in the opponents' half and nearer
    their goal line than both the ball and the second-last opponent. Level is onside.
    """
    second_last = sorted((point.x for point in defenders), reverse=True)[1]
    return max(second_last, ball.x, PITCH_LENGTH / 2)


def place_receiver(
    attackers: tuple[Point, ...],
    defenders: tuple[Point, ...],
    ball: Point,
    end: Point,
    receiver: int,
    flagged: bool,
    rng: Generator,
) -> tuple[Point, ...]:
    """Move a pass's receiver so the picture agrees with the referee's flag.

    The events never depend on where players stand, so positions are drawn to explain them:
    a receiver flagged offside stands just past the offside line, in line with where the pass
    is going, and an unflagged one who would be past the line is pulled back level or behind.
    Nobody else moves.
    """
    line = offside_line(defenders, ball)
    at = attackers[receiver]
    if flagged:
        moved = Point(line + rng.uniform(*OFFSIDE_MARGIN), end.y)
    elif at.x > line:
        moved = Point(line - rng.uniform(*ONSIDE_MARGIN), at.y)
    else:
        return attackers
    return (*attackers[:receiver], moved, *attackers[receiver + 1 :])
