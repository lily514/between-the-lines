"""Counter-attack: winning the ball deep and reaching the other box before the defence is set."""

from dataclasses import dataclass, field
from itertools import pairwise

from btl.concepts.base import ConceptTag, MatchContext
from btl.schema import PITCH_LENGTH, PITCH_WIDTH
from btl.schema.event import Event
from btl.schema.possession import changes_hands_in_open_play
from btl.schema.vocab import ConceptId

MAX_SECONDS = 12.0
HALFWAY = PITCH_LENGTH / 2
BOX_DEPTH = 16.5
BOX_HALF_WIDTH = 20.16


@dataclass(frozen=True, slots=True)
class CounterAttack:
    """Finds counter-attacks.

    A team that has just lost the ball is out of shape: its full-backs have pushed on and its
    midfield is spread for attacking. A counter-attack uses those few seconds, going straight
    for goal before the defence gets back. It pairs with the counter-press: pressing wins the
    ball high up, and the counter-attack is what a team does with a ball won deep.

    Here a team wins the ball in open play (its possession must not start with a set piece or
    with the kickoff after a goal) in its own half, and has the ball in the opponent's penalty
    area within ``max_seconds``: one of its actions in the same possession starts there. A cross
    that is cleared before anyone touches it doesn't count, because the team never has the ball
    in the box. Possessions come from `btl.schema.possession`.

    No difficulty is given. The tag's key action is the one that wins the ball, and its span
    runs to the first action in the box.
    """

    max_seconds: float = MAX_SECONDS
    concept: ConceptId = field(default=ConceptId.COUNTER_ATTACK, init=False)
    needs_snapshots: bool = field(default=False, init=False)

    def detect(self, ctx: MatchContext) -> tuple[ConceptTag, ...]:
        """Every counter-attack in the match, in event order."""
        tags: list[ConceptTag] = []
        for before, won in pairwise(ctx.possessions):
            win = ctx.events[won.first]
            if before.period_id != won.period_id or win.start_x >= HALFWAY:
                continue
            if not changes_hands_in_open_play(ctx.events[before.last], win):
                continue
            in_box = next(
                (
                    event
                    for event in ctx.events[won.first : won.last + 1]
                    if event.team_id == won.team_id and _in_box(event)
                ),
                None,
            )
            if in_box is None:
                continue
            seconds = in_box.time_seconds - win.time_seconds
            if seconds <= self.max_seconds:
                tags.append(
                    ConceptTag(
                        concept=self.concept,
                        game_id=win.game_id,
                        action_id=win.action_id,
                        span=(win.action_id, in_box.action_id),
                        difficulty=None,
                        evidence={
                            "seconds to the box": round(seconds, 1),
                            "won (m from own goal)": round(win.start_x, 1),
                        },
                    )
                )
        return tuple(tags)


def _in_box(event: Event) -> bool:
    """Whether the action starts in the penalty area being attacked."""
    return (
        event.start_x >= PITCH_LENGTH - BOX_DEPTH
        and abs(event.start_y - PITCH_WIDTH / 2) <= BOX_HALF_WIDTH
    )
