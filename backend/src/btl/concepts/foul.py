"""Fouls: what a foul gives, whether a booking was for stopping an attack, and advantage."""

import math
from dataclasses import dataclass, field

from btl.concepts.base import ConceptTag, MatchContext
from btl.concepts.counter_attack import BOX_DEPTH, BOX_HALF_WIDTH
from btl.concepts.phase import PhaseOfPlay, phase_timeline
from btl.schema import PITCH_LENGTH, PITCH_WIDTH
from btl.schema.vocab import ActionType, ConceptId, Result

FREE_KICKS = frozenset(
    {ActionType.FREEKICK_SHORT, ActionType.FREEKICK_CROSSED, ActionType.SHOT_FREEKICK}
)
# The fouled team's middle third starts this far from its own goal line.
PROMISING_FROM = PITCH_LENGTH / 3
# A foul this close to the penalty area's line, either side, is a hard call; ON_THE_LINE harder.
# Within AROUND_THE_BOX, free kick or penalty is a real question, but not a close one.
NEAR_BOX = 5.0
ON_THE_LINE = 1.0
AROUND_THE_BOX = 20.0
PLAIN = 0.1
IN_OR_AROUND_THE_BOX = 0.35
EXPLAINED_BOOKING = 0.45
ADVANTAGE = 0.6
NEAR_THE_BOX = 0.6
ON_THE_BOX_LINE = 0.85


@dataclass(frozen=True, slots=True)
class FoulCommitted:
    """Finds fouls, and what each one gives.

    A foul is judged where the contact is: here, where the ball was. The fouled team gets a
    direct free kick there, or a penalty if that point is inside the fouling team's own
    penalty area, lines included. Where the fouled player lands doesn't matter.

    The referee may instead let play go on (advantage), when stopping it would help the team
    that fouled: here, the fouled team's next action follows the foul with no free kick.

    A booking can be for many reasons, but event data shows only one: **stopping a promising
    attack**, when the fouled team was in a transition (by `btl.concepts.phase`) and in its
    middle or attacking third, at least ``PROMISING_FROM`` metres from its own goal line.

    The key action is the foul, and the span runs to the free kick, the penalty, or the
    fouled team's next action. Evidence: "penalty", "advantage", "booked" and "promising
    attack" (1 or 0), and "metres from the box": from the penalty area's line, negative
    inside it. Difficulty is the highest that applies: ``PLAIN`` for any foul,
    ``IN_OR_AROUND_THE_BOX`` inside the box or within ``AROUND_THE_BOX`` metres of it,
    ``EXPLAINED_BOOKING`` for a booking for stopping a promising attack, ``ADVANTAGE``,
    ``NEAR_THE_BOX`` within ``NEAR_BOX`` metres of the box's line and ``ON_THE_BOX_LINE``
    within ``ON_THE_LINE``.
    """

    concept: ConceptId = field(default=ConceptId.FOUL, init=False)
    needs_snapshots: bool = field(default=False, init=False)

    def detect(self, ctx: MatchContext) -> tuple[ConceptTag, ...]:
        """Every foul followed by the fouled team's free kick, penalty or play, in event order."""
        timeline = phase_timeline(ctx.match)
        events = ctx.events
        tags: list[ConceptTag] = []
        for foul in events:
            if foul.action_type is not ActionType.FOUL or foul.action_id + 1 >= len(events):
                continue
            after = events[foul.action_id + 1]
            if after.period_id != foul.period_id or after.team_id == foul.team_id:
                continue
            advantage = after.action_type not in (*FREE_KICKS, ActionType.SHOT_PENALTY)
            # Seen by the fouling team, attacking left to right: its own box is at x = 0.
            from_box = metres_from_box(foul.start_x, foul.start_y)
            before = events[foul.action_id - 1] if foul.action_id > 0 else None
            promising = (
                before is not None
                and before.team_id != foul.team_id
                and before.period_id == foul.period_id
                and timeline.phase_of(before.action_id) is PhaseOfPlay.TRANSITION
                and PITCH_LENGTH - foul.start_x >= PROMISING_FROM
            )
            booked = foul.result is Result.YELLOW_CARD
            tags.append(
                ConceptTag(
                    concept=self.concept,
                    game_id=foul.game_id,
                    action_id=foul.action_id,
                    span=(foul.action_id, after.action_id),
                    difficulty=_difficulty(from_box, booked and promising, advantage),
                    evidence={
                        "penalty": float(after.action_type is ActionType.SHOT_PENALTY),
                        "advantage": float(advantage),
                        "booked": float(booked),
                        "promising attack": float(promising),
                        "metres from the box": round(from_box, 1),
                    },
                )
            )
        return tuple(tags)


def metres_from_box(x: float, y: float) -> float:
    """How far a point is from the penalty area at x = 0: negative inside it, 0 on its line."""
    across = abs(y - PITCH_WIDTH / 2)
    if x <= BOX_DEPTH and across <= BOX_HALF_WIDTH:
        return -min(BOX_DEPTH - x, BOX_HALF_WIDTH - across)
    return math.hypot(max(0.0, x - BOX_DEPTH), max(0.0, across - BOX_HALF_WIDTH))


def _difficulty(from_box: float, explained_booking: bool, advantage: bool) -> float:
    levels = [PLAIN]
    if from_box <= AROUND_THE_BOX:
        levels.append(IN_OR_AROUND_THE_BOX)
    if explained_booking:
        levels.append(EXPLAINED_BOOKING)
    if advantage:
        levels.append(ADVANTAGE)
    if abs(from_box) <= NEAR_BOX:
        levels.append(NEAR_THE_BOX)
    if abs(from_box) <= ON_THE_LINE:
        levels.append(ON_THE_BOX_LINE)
    return max(levels)
