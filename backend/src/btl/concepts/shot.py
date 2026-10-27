"""Shot: every shot at goal, how it ended, where it was from, and how the chance came about."""

import math
from dataclasses import dataclass, field
from enum import IntEnum

from btl.concepts.base import ConceptTag, MatchContext
from btl.concepts.counter_attack import BOX_DEPTH, BOX_HALF_WIDTH
from btl.schema import PITCH_LENGTH, PITCH_WIDTH
from btl.schema.event import Event
from btl.schema.vocab import ActionType, ConceptId, Result

SHOTS = frozenset({ActionType.SHOT, ActionType.SHOT_FREEKICK})
GOAL_HALF_WIDTH = 3.66
SIX_YARD_DEPTH = 5.5
SIX_YARD_HALF_WIDTH = 9.16
# A shot ending this far from the nearest post, or further, is an easy call on target or not.
CLEAR_OF_A_POST = 3.0
CROSSES = frozenset({ActionType.CROSS, ActionType.CORNER_CROSSED, ActionType.FREEKICK_CROSSED})
PASSES = frozenset(
    {
        ActionType.PASS,
        ActionType.THROW_IN,
        ActionType.CORNER_SHORT,
        ActionType.FREEKICK_SHORT,
        ActionType.GOALKICK,
    }
)
DRIBBLES = frozenset({ActionType.DRIBBLE, ActionType.TAKE_ON})


class ShotOutcome(IntEnum):
    """How a shot ended. Stored in a tag's evidence as ``"outcome"``."""

    SCORED = 0
    SAVED = 1
    OFF_TARGET = 2

    @property
    def label(self) -> str:
        """The outcome in words."""
        return OUTCOME_LABELS[self]


class ShotZone(IntEnum):
    """Where a shot was taken from. Stored in a tag's evidence as ``"zone"``."""

    SIX_YARD_BOX = 0
    PENALTY_AREA = 1
    OUTSIDE_THE_BOX = 2

    @property
    def label(self) -> str:
        """The zone in words."""
        return ZONE_LABELS[self]


class ChanceFrom(IntEnum):
    """What made the chance: the team's action just before the shot. Evidence ``"chance from"``."""

    CROSS = 0
    PASS = 1
    DRIBBLE = 2
    FREE_KICK = 3
    LOOSE_BALL = 4

    @property
    def label(self) -> str:
        """The source in words."""
        return CHANCE_LABELS[self]


OUTCOME_LABELS = {
    ShotOutcome.SCORED: "scored",
    ShotOutcome.SAVED: "saved",
    ShotOutcome.OFF_TARGET: "off target",
}
ZONE_LABELS = {
    ShotZone.SIX_YARD_BOX: "the six-yard box",
    ShotZone.PENALTY_AREA: "the penalty area",
    ShotZone.OUTSIDE_THE_BOX: "outside the box",
}
CHANCE_LABELS = {
    ChanceFrom.CROSS: "a cross",
    ChanceFrom.PASS: "a pass",
    ChanceFrom.DRIBBLE: "a dribble",
    ChanceFrom.FREE_KICK: "a free kick",
    ChanceFrom.LOOSE_BALL: "a loose ball",
}


@dataclass(frozen=True, slots=True)
class Shot:
    """Finds every shot from open play or a direct free kick.

    A shot is on target when the keeper has to stop it or it goes in: it is **scored** when its
    result says so, **saved** when the other team's keeper's save is the next action, and
    **off target** otherwise. Penalties are left out: the foul that gave one is asked about at
    its own stoppage.

    Where it was from is the **zone** of the shot's start: the six-yard box, the rest of the
    penalty area, or outside the box. How the chance came about is the team's last action
    before the shot in the same possession: a cross (open play, a corner or a free kick), a
    pass, a dribble, or, with none, a loose ball; a direct free kick is its own source.

    The key action is the shot. The span runs from the action that made the chance to the shot,
    so the picture can show the ball arriving. Evidence: "outcome", "zone" and "chance from" (a
    `ShotOutcome`, `ShotZone` and `ChanceFrom` value), "metres from goal" and "metres from a
    post". Difficulty is how hard on target or not is to call: 0 when the ball ends
    ``clear_of_a_post`` metres or more from the nearest post, rising to 1 on the post.
    """

    clear_of_a_post: float = CLEAR_OF_A_POST
    concept: ConceptId = field(default=ConceptId.SHOT, init=False)
    needs_snapshots: bool = field(default=False, init=False)

    def detect(self, ctx: MatchContext) -> tuple[ConceptTag, ...]:
        """Every shot and direct free kick in the match, in event order."""
        tags: list[ConceptTag] = []
        by_possession = {
            action: possession
            for possession in ctx.possessions
            for action in range(possession.first, possession.last + 1)
        }
        for shot in ctx.events:
            if shot.action_type not in SHOTS:
                continue
            source = _source(ctx, shot, by_possession[shot.action_id].first)
            first = shot.action_id if source is None else source.action_id
            from_post = abs(abs(shot.end_y - PITCH_WIDTH / 2) - GOAL_HALF_WIDTH)
            clear = min(from_post, self.clear_of_a_post) / self.clear_of_a_post
            from_goal = math.hypot(PITCH_LENGTH - shot.start_x, shot.start_y - PITCH_WIDTH / 2)
            tags.append(
                ConceptTag(
                    concept=self.concept,
                    game_id=shot.game_id,
                    action_id=shot.action_id,
                    span=(first, shot.action_id),
                    difficulty=round(1 - clear, 2),
                    evidence={
                        "outcome": float(shot_outcome(ctx, shot)),
                        "zone": float(shot_zone(shot.start_x, shot.start_y)),
                        "chance from": float(chance_from(shot, source)),
                        "metres from goal": round(from_goal, 1),
                        "metres from a post": round(from_post, 1),
                    },
                )
            )
        return tuple(tags)


def shot_outcome(ctx: MatchContext, shot: Event) -> ShotOutcome:
    """How a shot ended: scored, saved by the next action, or off target."""
    if shot.result is Result.SUCCESS:
        return ShotOutcome.SCORED
    following = shot.action_id + 1
    if following < len(ctx.events):
        after = ctx.events[following]
        saved = (
            after.action_type is ActionType.KEEPER_SAVE
            and after.team_id != shot.team_id
            and after.period_id == shot.period_id
        )
        if saved:
            return ShotOutcome.SAVED
    return ShotOutcome.OFF_TARGET


def shot_zone(x: float, y: float) -> ShotZone:
    """The zone a shot from ``(x, y)`` is taken from, attacking towards x = 105."""
    across = abs(y - PITCH_WIDTH / 2)
    if x >= PITCH_LENGTH - SIX_YARD_DEPTH and across <= SIX_YARD_HALF_WIDTH:
        return ShotZone.SIX_YARD_BOX
    if x >= PITCH_LENGTH - BOX_DEPTH and across <= BOX_HALF_WIDTH:
        return ShotZone.PENALTY_AREA
    return ShotZone.OUTSIDE_THE_BOX


def chance_from(shot: Event, source: Event | None) -> ChanceFrom:
    """What made the chance, from the shot and the team's action before it."""
    if shot.action_type is ActionType.SHOT_FREEKICK:
        return ChanceFrom.FREE_KICK
    if source is None:
        return ChanceFrom.LOOSE_BALL
    if source.action_type in CROSSES:
        return ChanceFrom.CROSS
    if source.action_type in PASSES:
        return ChanceFrom.PASS
    if source.action_type in DRIBBLES:
        return ChanceFrom.DRIBBLE
    return ChanceFrom.LOOSE_BALL


def _source(ctx: MatchContext, shot: Event, first: int) -> Event | None:
    """The shooting team's last action before the shot in the same possession, if any."""
    for action in range(shot.action_id - 1, first - 1, -1):
        before = ctx.events[action]
        if before.team_id == shot.team_id and before.action_type is not ActionType.FOUL:
            return before
    return None
