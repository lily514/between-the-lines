"""Counter-press: winning the ball straight back after losing it, high up the pitch."""

from dataclasses import dataclass, field

from btl.concepts.base import ConceptTag, MatchContext
from btl.schema import PITCH_LENGTH
from btl.schema.possession import changes_hands_in_open_play
from btl.schema.vocab import ConceptId

MAX_SECONDS = 5.0
HALFWAY = PITCH_LENGTH / 2


@dataclass(frozen=True, slots=True)
class CounterPress:
    """Finds counter-presses.

    When a team loses the ball, it can drop back into shape, or it can hunt the ball straight
    away, while the opponent is still turning to play forward and before it has spread out.
    Hunting it is the counter-press. It is risky, because the team is still spread for attacking,
    but a ball won back high up the pitch is close to the opponent's goal.

    Here a team loses the ball when the other team wins it in open play: the other team's
    possession must not start with a set piece, or with the kickoff after a goal. The team
    counter-presses when it wins the ball back, in open play, within ``max_seconds`` of losing it
    and in the opponent's half. Possessions come from `btl.schema.possession`, and the times are
    those of the actions that win the ball each way.

    No difficulty is given. The tag's key action is the one that wins the ball back, and its span
    runs from the team's last action before it lost the ball.
    """

    max_seconds: float = MAX_SECONDS
    concept: ConceptId = field(default=ConceptId.COUNTER_PRESS, init=False)
    needs_snapshots: bool = field(default=False, init=False)

    def detect(self, ctx: MatchContext) -> tuple[ConceptTag, ...]:
        """Every counter-press in the match, in event order."""
        tags: list[ConceptTag] = []
        for before, lost, regained in zip(
            ctx.possessions, ctx.possessions[1:], ctx.possessions[2:], strict=False
        ):
            if not (before.period_id == lost.period_id == regained.period_id):
                continue
            last_touch = ctx.events[before.last]
            loss, regain = ctx.events[lost.first], ctx.events[regained.first]
            lost_it = changes_hands_in_open_play(last_touch, loss)
            if not (lost_it and changes_hands_in_open_play(ctx.events[lost.last], regain)):
                continue
            seconds = regain.time_seconds - loss.time_seconds
            if seconds <= self.max_seconds and regain.start_x > HALFWAY:
                tags.append(
                    ConceptTag(
                        concept=self.concept,
                        game_id=regain.game_id,
                        action_id=regain.action_id,
                        span=(last_touch.action_id, regain.action_id),
                        difficulty=None,
                        evidence={
                            "seconds to win back": round(seconds, 1),
                            "metres from goal": round(PITCH_LENGTH - regain.start_x, 1),
                        },
                    )
                )
        return tuple(tags)
