"""Who has the ball: one shared definition, derived from events alone.

SPADL has no possession column, so this works it out from the actions. It deliberately
ignores the simulator's own ``possession_id``, so the concept detectors that rely on it also
work on data the simulator didn't produce.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from btl.schema.event import Event
from btl.schema.ids import ActionId, TeamId
from btl.schema.vocab import ActionType, Result

# A defender touching the ball without winning it doesn't end the other team's possession.
DEFENSIVE_ACTIONS = frozenset(
    {
        ActionType.TACKLE,
        ActionType.INTERCEPTION,
        ActionType.CLEARANCE,
        ActionType.KEEPER_SAVE,
        ActionType.KEEPER_CLAIM,
        ActionType.KEEPER_PUNCH,
        ActionType.KEEPER_PICK_UP,
    }
)


@dataclass(frozen=True, slots=True)
class Possession:
    """An unbroken spell on the ball by one team, from its first action to its last."""

    team_id: TeamId
    period_id: int
    first: ActionId
    last: ActionId


def _wins_the_ball(event: Event) -> bool:
    if event.action_type is ActionType.FOUL:
        return False
    return not (event.action_type in DEFENSIVE_ACTIONS and event.result is Result.FAIL)


def split_possessions(events: Sequence[Event]) -> tuple[Possession, ...]:
    """Split a match's events into possessions.

    A new possession starts at the start of each period, and whenever the other team makes an
    action that wins the ball. Fouls and failed defensive actions by the other team stay inside
    the current possession.

    Args:
        events: The match's events in order.

    Returns:
        The possessions in order. Every event belongs to exactly one.
    """
    possessions: list[Possession] = []
    current: Possession | None = None
    for event in events:
        changes_hands = (
            current is not None and event.team_id != current.team_id and _wins_the_ball(event)
        )
        if current is None or event.period_id != current.period_id or changes_hands:
            if current is not None:
                possessions.append(current)
            current = Possession(event.team_id, event.period_id, event.action_id, event.action_id)
        else:
            current = Possession(current.team_id, current.period_id, current.first, event.action_id)
    if current is not None:
        possessions.append(current)
    return tuple(possessions)
