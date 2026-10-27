"""Ball win: a team winning the ball back in open play, how it did, and where."""

from dataclasses import dataclass, field
from enum import IntEnum
from itertools import pairwise

from btl.concepts.base import ConceptTag, MatchContext
from btl.schema import PITCH_LENGTH
from btl.schema.possession import changes_hands_in_open_play
from btl.schema.vocab import ActionType, ConceptId

THIRD = PITCH_LENGTH / 3
# A win this close to a third's line is a hard call on which third it was in.
NEAR_A_LINE = 12.0
KEEPER_ACTIONS = frozenset(
    {
        ActionType.KEEPER_SAVE,
        ActionType.KEEPER_CLAIM,
        ActionType.KEEPER_PUNCH,
        ActionType.KEEPER_PICK_UP,
    }
)


class WonWith(IntEnum):
    """How a team won the ball back. Stored in a tag's evidence as ``"won with"``."""

    TACKLE = 0
    INTERCEPTION = 1
    KEEPER = 2
    LOOSE_BALL = 3

    @property
    def label(self) -> str:
        """The way, in words: "a tackle", "an interception", "the keeper", "a loose ball"."""
        return LABELS[self]


LABELS = {
    WonWith.TACKLE: "a tackle",
    WonWith.INTERCEPTION: "an interception",
    WonWith.KEEPER: "the keeper",
    WonWith.LOOSE_BALL: "a loose ball",
}
THIRDS = ("own third", "middle third", "attacking third")


@dataclass(frozen=True, slots=True)
class BallWin:
    """Finds every ball won in open play.

    A team wins the ball when its action starts a new possession (by `btl.schema.possession`)
    and the ball changed hands in open play: not at a set piece, and not at the kickoff after
    a goal. How it won it is read from that action: a tackle takes the ball off the player on
    it, an interception cuts out a pass, the keeper gathers a shot or a cross, and anything else
    picks up a loose ball.

    Where it won it matters as much as how, so the evidence says how far from the team's own
    goal line the ball was won, in its own attacking direction; `pitch_third` turns that into
    the own, middle or attacking third. Difficulty is how hard that third is to call: 0 when
    the ball is won ``near_a_line`` metres or more from a third's line, rising to 1 on the line.

    The key action is the one that wins the ball, and the span runs from the losing team's last
    action to it. Evidence: "won with" (a `WonWith` value) and "metres from own goal".
    """

    near_a_line: float = NEAR_A_LINE
    concept: ConceptId = field(default=ConceptId.BALL_WIN, init=False)
    needs_snapshots: bool = field(default=False, init=False)

    def detect(self, ctx: MatchContext) -> tuple[ConceptTag, ...]:
        """Every ball won in open play, in event order."""
        tags: list[ConceptTag] = []
        for before, won in pairwise(ctx.possessions):
            if before.period_id != won.period_id:
                continue
            lost, win = ctx.events[before.last], ctx.events[won.first]
            if not changes_hands_in_open_play(lost, win):
                continue
            tags.append(
                ConceptTag(
                    concept=self.concept,
                    game_id=win.game_id,
                    action_id=win.action_id,
                    span=(lost.action_id, win.action_id),
                    difficulty=self._difficulty(win.start_x),
                    evidence={
                        "won with": float(won_with(win.action_type)),
                        "metres from own goal": round(win.start_x, 1),
                    },
                )
            )
        return tuple(tags)

    def _difficulty(self, x: float) -> float:
        from_a_line = min(abs(x - THIRD), abs(x - 2 * THIRD))
        return round(1 - min(from_a_line, self.near_a_line) / self.near_a_line, 2)


def won_with(action: ActionType) -> WonWith:
    """How an action that starts a possession won the ball."""
    if action is ActionType.TACKLE:
        return WonWith.TACKLE
    if action is ActionType.INTERCEPTION:
        return WonWith.INTERCEPTION
    if action in KEEPER_ACTIONS:
        return WonWith.KEEPER
    return WonWith.LOOSE_BALL


def pitch_third(metres_from_own_goal: float) -> str:
    """Which third of the pitch a point is in, for the team whose goal line is at 0."""
    if metres_from_own_goal >= 2 * THIRD:
        return THIRDS[2]
    return THIRDS[1] if metres_from_own_goal >= THIRD else THIRDS[0]
