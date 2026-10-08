"""Switch of play: moving the ball quickly to the far side of the pitch."""

from dataclasses import dataclass, field

from btl.concepts.base import ConceptTag, MatchContext
from btl.schema import PITCH_WIDTH
from btl.schema.vocab import ActionType, ConceptId, Result

MIN_ACROSS = 30.0
FLANK_WIDTH = PITCH_WIDTH / 3
SWITCHING_ACTIONS = frozenset({ActionType.PASS, ActionType.CROSS})


@dataclass(frozen=True, slots=True)
class SwitchOfPlay:
    """Finds switches of play.

    A switch of play moves the ball from one side of the pitch to the other, usually to where
    the defence is thinner, because defenders shift towards the ball. Here it is a successful
    pass or cross that travels at least ``min_across`` metres across the pitch and ends on the
    far flank: within ``flank_width`` of the touchline on the other side of the pitch's
    centre line from where it started.

    No difficulty is given: a switch is easy to see once you know to look for it.
    """

    min_across: float = MIN_ACROSS
    flank_width: float = FLANK_WIDTH
    concept: ConceptId = field(default=ConceptId.SWITCH_OF_PLAY, init=False)
    needs_snapshots: bool = field(default=False, init=False)

    def detect(self, ctx: MatchContext) -> tuple[ConceptTag, ...]:
        """Every switch of play in the match, in event order."""
        tags: list[ConceptTag] = []
        for event in ctx.events:
            if event.action_type not in SWITCHING_ACTIONS or event.result is not Result.SUCCESS:
                continue
            across = abs(event.end_y - event.start_y)
            from_right = event.start_y < PITCH_WIDTH / 2
            far_flank = (
                event.end_y >= PITCH_WIDTH - self.flank_width
                if from_right
                else event.end_y <= self.flank_width
            )
            if across >= self.min_across and far_flank:
                tags.append(
                    ConceptTag(
                        concept=self.concept,
                        game_id=event.game_id,
                        action_id=event.action_id,
                        span=(event.action_id, event.action_id),
                        difficulty=None,
                        evidence={"across (m)": round(across, 1)},
                    )
                )
        return tuple(tags)
