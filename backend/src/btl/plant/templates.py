"""Templates: one scripted possession opening per concept, built to a requested difficulty.

A template never looks at the detectors. It builds its moment from the same football idea,
so the test that planted moments are detected checks both sides independently.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

from numpy.random import Generator

from btl.league.league import Role
from btl.schema.vocab import ActionType, BodyPart, ConceptId, Phase, Result
from btl.sim.chain import Side, Start, Step
from btl.sim.params import SimParams
from btl.sim.pitch import PITCH_WIDTH, Point, clamp_to_pitch, distance
from btl.sim.script import Script
from btl.sim.shape import Formation, place_teams

# Where the ball must be won for a line-breaking moment to follow, in the winner's direction:
# deep enough that the opponent's midfield line is still in front of it.
WIN_ZONE = (20.0, 60.0)
WINNING_ACTIONS = frozenset({ActionType.INTERCEPTION, ActionType.TACKLE})
# Where the playmaker can receive the lay-off.
PLAYMAKER_X = (25.0, 50.0)
PLAYMAKER_Y = (14.0, 54.0)
LAY_OFF_SIDEWAYS = (6.0, 12.0)
LAY_OFF_BACK = (0.0, 6.0)
# The midfield line stands this far in front of the playmaker, and the pass ends this far
# beyond it, well short of the back line.
LINE_AHEAD = 7.0
RECEIVER_BEYOND = 7.0
# The gap in the midfield line the pass goes through, per difficulty level.
GAP_WIDTHS: Mapping[int, float] = {1: 18.0, 2: 12.0, 3: 7.0}
GAP_OFF_CENTRE = 5.0
MIDFIELD_SPACING = 10.0
# At the hardest level a teammate stands free to the side: the safe pass that tempts the eye.
DECOY_FROM_LEVEL = 3
DECOY_SIDEWAYS = 12.0
JITTER = 0.5
_MARGIN = 0.5


class Template(Protocol):
    """Writes the opening of a possession that holds one teachable moment."""

    def fits(self, start: Start) -> bool:
        """Whether a possession starting this way can hold the moment."""
        ...

    def write(
        self,
        attack: Side,
        defence: Side,
        start: Start,
        difficulty: int,
        rng: Generator,
        params: SimParams,
    ) -> Script:
        """The possession's opening, in the attacking team's direction."""
        ...


@dataclass(frozen=True, slots=True)
class LineBreakingTemplate:
    """A line-breaking pass after winning the ball in midfield.

    The ball is won, laid off to a midfielder, and the midfielder passes through a gap in the
    opponent's midfield line to a teammate standing between that line and the back line. The
    learner sees the moment the midfielder has the ball. The narrower the gap, the harder the
    pass is to see: level 1 has an 18 m gap, level 2 a 12 m one, and level 3 a 7 m one, with a
    teammate standing free to the side as the obvious safe option.
    """

    def fits(self, start: Start) -> bool:
        """Whether the ball was won in open play, deep enough to play forward through a line."""
        return start.won_with in WINNING_ACTIONS and WIN_ZONE[0] <= start.ball.x <= WIN_ZONE[1]

    def write(
        self,
        attack: Side,
        defence: Side,
        start: Start,
        difficulty: int,
        rng: Generator,
        params: SimParams,
    ) -> Script:
        """Win, lay off, then the line-breaking pass; play carries on from its receiver."""
        if start.won_with is None:
            raise ValueError("a line-breaking moment starts by winning the ball")
        won_at = start.ball
        playmaker_at = _lay_off_target(won_at, rng)
        attackers, defenders = place_teams(attack.formation, defence.formation, playmaker_at)
        playmaker = _nearest(
            attack.formation, attackers, playmaker_at, {Role.MIDFIELDER}, {start.slot}
        )

        line_x = playmaker_at.x + LINE_AHEAD
        gap_centre = _clamp(
            playmaker_at.y + rng.uniform(-GAP_OFF_CENTRE, GAP_OFF_CENTRE), *PLAYMAKER_Y
        )
        defenders, gap_pair = _open_gap(
            defence.formation, defenders, line_x, gap_centre, GAP_WIDTHS[difficulty]
        )
        # The pass crosses the line halfway along, so aiming it through the gap's centre means
        # ending as far beyond the centre as the playmaker is short of it.
        receiver_at = Point(line_x + RECEIVER_BEYOND, 2 * gap_centre - playmaker_at.y)
        outfield = {Role.DEFENDER, Role.MIDFIELDER, Role.FORWARD}
        receiver = _nearest(attack.formation, attackers, receiver_at, outfield, {playmaker})
        placed = {playmaker: playmaker_at, receiver: receiver_at}
        if difficulty >= DECOY_FROM_LEVEL:
            side = 1.0 if playmaker_at.y < PITCH_WIDTH / 2 else -1.0
            decoy_at = Point(playmaker_at.x + 1, playmaker_at.y + side * DECOY_SIDEWAYS)
            decoy = _nearest(attack.formation, attackers, decoy_at, outfield, set(placed))
            placed[decoy] = decoy_at
        attackers = tuple(
            placed.get(slot, _jittered(point, rng)) for slot, point in enumerate(attackers)
        )
        defenders = tuple(
            point if slot in gap_pair else _jittered(point, rng)
            for slot, point in enumerate(defenders)
        )

        steps = (
            Step(
                start.slot,
                start.won_with,
                Result.SUCCESS,
                BodyPart.FOOT,
                won_at,
                won_at,
                rng.uniform(*params.reaction_time),
                Phase.TRANSITION,
            ),
            _pass(start.slot, won_at, playmaker_at, rng, params),
            _pass(playmaker, playmaker_at, receiver_at, rng, params),
        )
        return Script(
            steps=steps,
            ball=receiver_at,
            slot=receiver,
            shapes={2: (attackers, defenders)},
            concept=ConceptId.LINE_BREAKING_PASS,
            difficulty=difficulty,
            pause=1,
            answer=2,
        )


TEMPLATES: Mapping[ConceptId, Template] = {ConceptId.LINE_BREAKING_PASS: LineBreakingTemplate()}


def _lay_off_target(won_at: Point, rng: Generator) -> Point:
    """A short pass back and infield, to where a midfielder can see the opponent's lines."""
    infield = 1.0 if won_at.y < PITCH_WIDTH / 2 else -1.0
    return Point(
        _clamp(won_at.x - rng.uniform(*LAY_OFF_BACK), *PLAYMAKER_X),
        _clamp(won_at.y + infield * rng.uniform(*LAY_OFF_SIDEWAYS), *PLAYMAKER_Y),
    )


def _open_gap(
    formation: Formation,
    defenders: tuple[Point, ...],
    line_x: float,
    gap_centre: float,
    gap: float,
) -> tuple[tuple[Point, ...], set[int]]:
    """Move the defence so its midfield line stands at ``line_x`` with the given gap.

    The whole outfield block slides with the midfield line, so the distances between the
    lines stay as the shape model made them. The two midfielders either side of the gap stand
    ``gap`` metres apart around ``gap_centre``; the rest keep ``MIDFIELD_SPACING`` outside them.

    Returns:
        The defenders' new positions, and the slots of the two either side of the gap.
    """
    midfielders = sorted(
        (slot for slot, each in enumerate(formation.slots) if each.role is Role.MIDFIELDER),
        key=lambda slot: defenders[slot].y,
    )
    shift = line_x - sum(defenders[slot].x for slot in midfielders) / len(midfielders)
    moved = [
        point if formation.slots[slot].role is Role.GOALKEEPER else Point(point.x + shift, point.y)
        for slot, point in enumerate(defenders)
    ]
    left = min(
        range(len(midfielders) - 1),
        key=lambda i: abs(
            (defenders[midfielders[i]].y + defenders[midfielders[i + 1]].y) / 2 - gap_centre
        ),
    )
    for i, slot in enumerate(midfielders):
        if i <= left:
            y = gap_centre - gap / 2 - MIDFIELD_SPACING * (left - i)
        else:
            y = gap_centre + gap / 2 + MIDFIELD_SPACING * (i - left - 1)
        moved[slot] = Point(line_x, y)
    placed = tuple(clamp_to_pitch(point, _MARGIN) for point in moved)
    return placed, {midfielders[left], midfielders[left + 1]}


def _pass(slot: int, start: Point, end: Point, rng: Generator, params: SimParams) -> Step:
    duration = distance(start, end) / params.pass_speed + rng.uniform(*params.control_time)
    return Step(
        slot, ActionType.PASS, Result.SUCCESS, BodyPart.FOOT, start, end, duration, Phase.TRANSITION
    )


def _nearest(
    formation: Formation,
    positions: tuple[Point, ...],
    target: Point,
    roles: set[Role],
    exclude: set[int],
) -> int:
    """The slot with one of ``roles``, not in ``exclude``, standing closest to ``target``."""
    candidates = (
        slot
        for slot, each in enumerate(formation.slots)
        if each.role in roles and slot not in exclude
    )
    return min(candidates, key=lambda slot: distance(positions[slot], target))


def _jittered(point: Point, rng: Generator) -> Point:
    return clamp_to_pitch(
        Point(point.x + JITTER * rng.standard_normal(), point.y + JITTER * rng.standard_normal()),
        _MARGIN,
    )


def _clamp(value: float, low: float, high: float) -> float:
    return min(max(value, low), high)
