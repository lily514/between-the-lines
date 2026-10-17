"""Restarts: the throw-in, corner or goal kick after the ball goes out, and which team takes it."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from itertools import pairwise

from btl.concepts.base import ConceptTag, MatchContext
from btl.schema import PITCH_LENGTH
from btl.schema.vocab import ActionType, ConceptId

CORNERS = frozenset({ActionType.CORNER_CROSSED, ActionType.CORNER_SHORT})
OUT_OF_PLAY = frozenset({ActionType.THROW_IN, ActionType.GOALKICK, *CORNERS})
# A throw-in this close to a corner flag is where touchline and goal line are easy to mix up.
NEAR_CORNER = 5.0
NEAR_CORNER_EXTRA = 0.15
# How hard each restart is to call, by kind and by whether the last touch went unrecorded.
DIFFICULTY: Mapping[tuple[ActionType, bool], float] = {
    (ActionType.THROW_IN, False): 0.1,
    (ActionType.GOALKICK, False): 0.3,
    (ActionType.CORNER_CROSSED, False): 0.4,
    (ActionType.THROW_IN, True): 0.5,
    (ActionType.GOALKICK, True): 0.75,
    (ActionType.CORNER_CROSSED, True): 0.75,
}


@dataclass(frozen=True, slots=True)
class BallOutOfPlay:
    """Finds the restarts that follow the ball going out of play.

    When the whole ball crosses a touchline or a goal line, play restarts with the team that
    didn't touch it last. Over a touchline that's a throw-in, from where it went out. Over a
    goal line it's a corner if the defending team touched it last, and a goal kick if the
    attacking team did.

    Event data doesn't always record the last touch: a block off a defender usually has no
    event of its own. So the restart decides. When the team taking it also made the last
    recorded action, an unrecorded touch by the other team sent the ball out, and the tag says
    so ("off an opponent" is 1).

    Kickoffs, free kicks and penalties are left out: the ball didn't go out. The key action is
    the last one before the restart, and the span runs to the restart. Evidence: "off an
    opponent" and "over a goal line" (1 or 0), and for a throw-in, "metres from a corner flag"
    along the touchline. Difficulty is from ``DIFFICULTY``, plus ``NEAR_CORNER_EXTRA`` for a
    throw-in within ``NEAR_CORNER`` of a flag.
    """

    concept: ConceptId = field(default=ConceptId.RESTART, init=False)
    needs_snapshots: bool = field(default=False, init=False)

    def detect(self, ctx: MatchContext) -> tuple[ConceptTag, ...]:
        """Every throw-in, corner and goal kick in the match, in event order."""
        tags: list[ConceptTag] = []
        for before, restart in pairwise(ctx.events):
            kind = restart.action_type
            if kind not in OUT_OF_PLAY or before.period_id != restart.period_id:
                continue
            off_an_opponent = before.team_id == restart.team_id
            evidence = {
                "off an opponent": float(off_an_opponent),
                "over a goal line": float(kind is not ActionType.THROW_IN),
            }
            difficulty = DIFFICULTY[(_kind(kind), off_an_opponent)]
            if kind is ActionType.THROW_IN:
                from_flag = min(restart.start_x, PITCH_LENGTH - restart.start_x)
                evidence["metres from a corner flag"] = round(from_flag, 1)
                if from_flag <= NEAR_CORNER:
                    difficulty += NEAR_CORNER_EXTRA
            tags.append(
                ConceptTag(
                    concept=self.concept,
                    game_id=restart.game_id,
                    action_id=before.action_id,
                    span=(before.action_id, restart.action_id),
                    difficulty=min(1.0, difficulty),
                    evidence=evidence,
                )
            )
        return tuple(tags)


def _kind(action: ActionType) -> ActionType:
    return ActionType.CORNER_CROSSED if action in CORNERS else action
