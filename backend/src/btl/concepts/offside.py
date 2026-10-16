"""Offside: whether the attacker a forward pass goes to stood in an offside position."""

import math
from dataclasses import dataclass, field

from btl.concepts.base import ConceptTag, MatchContext
from btl.schema import PITCH_LENGTH
from btl.schema.event import Event
from btl.schema.ids import ActionId
from btl.schema.snapshot import PlayerPosition, Snapshot
from btl.schema.vocab import ActionType, ConceptId, Result

HALFWAY = PITCH_LENGTH / 2
# Only receivers this close to the offside line, either side, make a call worth asking about.
NEAR_LINE = 5.0
# Difficulty falls from HARDEST at a margin of TIGHT metres to EASIEST at CLEAR metres.
TIGHT = 0.5
CLEAR = 4.0
HARDEST = 0.9
EASIEST = 0.1


@dataclass(frozen=True, slots=True)
class OffsidePass:
    """Finds forward passes to an attacker near the offside line, onside or offside.

    By the Laws, an attacker is in an offside position if, at the moment a teammate plays
    the ball, they are in the opponents' half and nearer the opponents' goal line than both
    the ball and the second-last opponent (usually the last outfield defender, with the
    keeper behind). Level is onside. Being in an offside position is only an offence when the
    attacker then becomes involved, here by being the one the pass goes to. A throw-in, goal
    kick or corner can't be offside, so only passes count.

    The receiver of a completed pass is the player of the team's next action. For a pass
    flagged offside, event data doesn't say who it was for, so the receiver is the attacker
    in an offside position nearest where the pass ended: the one the referee judged involved.

    A pass is tagged when it goes forward into the opponents' half and its receiver stands
    within ``NEAR_LINE`` metres of the offside line, either side. The key action is the pass,
    and the span runs to the receiver's action, if there is one. Evidence: "offside" (1 or 0),
    "margin (m)" from the line, "line (m)" (the line's x, with the passing team attacking left
    to right) and the receiver's "player id". Difficulty falls from ``HARDEST`` for a margin
    of ``TIGHT`` metres or less to ``EASIEST`` at ``CLEAR`` metres or more.
    """

    concept: ConceptId = field(default=ConceptId.OFFSIDE, init=False)
    needs_snapshots: bool = field(default=True, init=False)

    def detect(self, ctx: MatchContext) -> tuple[ConceptTag, ...]:
        """Every forward pass to an attacker near the offside line, in event order."""
        tags: list[ConceptTag] = []
        for event in ctx.events:
            if event.action_type is not ActionType.PASS or event.result is Result.FAIL:
                continue
            if event.end_x <= HALFWAY or event.end_x <= event.start_x:
                continue
            snapshot = ctx.snapshot(event.action_id)
            if snapshot is None:
                continue
            found = self.receiver(ctx, event, snapshot)
            if found is None:
                continue
            receiver, answered_by = found
            line = offside_line(snapshot, event)
            if line is None:
                continue
            margin = receiver.x - line
            if abs(margin) > NEAR_LINE:
                continue
            tags.append(
                ConceptTag(
                    concept=self.concept,
                    game_id=event.game_id,
                    action_id=event.action_id,
                    span=(event.action_id, answered_by),
                    difficulty=_difficulty(abs(margin)),
                    evidence={
                        "offside": float(margin > 0),
                        "margin (m)": round(abs(margin), 1),
                        "line (m)": round(line, 1),
                        "player id": float(receiver.player_id),
                    },
                )
            )
        return tuple(tags)

    def receiver(
        self, ctx: MatchContext, event: Event, snapshot: Snapshot
    ) -> tuple[PlayerPosition, ActionId] | None:
        """The attacker a pass went to, and the action that ends the play.

        Returns:
            The receiver as they stood when the pass was played, and the id of their next
            action (or of the pass itself, when flagged), or None if no receiver is known.
        """
        mates = [
            p
            for p in snapshot.positions
            if p.team_id == event.team_id and not p.is_actor and not p.is_goalkeeper
        ]
        if event.result is Result.OFFSIDE:
            line = offside_line(snapshot, event)
            beyond = [p for p in mates if line is not None and p.x > line]
            if not beyond:
                return None
            nearest = min(beyond, key=lambda p: math.dist((p.x, p.y), (event.end_x, event.end_y)))
            return nearest, event.action_id
        if event.action_id + 1 >= len(ctx.events):
            return None
        after = ctx.events[event.action_id + 1]
        if after.team_id != event.team_id or after.period_id != event.period_id:
            return None
        player = next((p for p in mates if p.player_id == after.player_id), None)
        return None if player is None else (player, after.action_id)


def offside_line(snapshot: Snapshot, event: Event) -> float | None:
    """The x past which the passing team's attackers are offside, attacking left to right.

    Returns:
        The furthest of the second-last opponent, the ball and halfway; None if fewer than
        two opponents are known.
    """
    opponents = sorted(
        (p.x for p in snapshot.positions if p.team_id != event.team_id), reverse=True
    )
    if len(opponents) < 2:
        return None
    return max(opponents[1], event.start_x, HALFWAY)


def _difficulty(margin: float) -> float:
    share = (min(max(margin, TIGHT), CLEAR) - TIGHT) / (CLEAR - TIGHT)
    return round(HARDEST - share * (HARDEST - EASIEST), 3)
