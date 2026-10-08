"""One on-ball action: a SPADL row plus the context SPADL has no columns for."""

from dataclasses import dataclass

from btl.schema.ids import ActionId, GameId, PlayerId, TeamId
from btl.schema.vocab import ActionType, BodyPart, Phase, Result


@dataclass(frozen=True, slots=True)
class Event:
    """One action, in metres and in the stored direction described in `btl.schema`.

    The fields up to ``bodypart`` map one-to-one onto SPADL columns. The rest are extension
    fields, which `btl.schema.frames` keeps in a separate frame because SPADL's schema is strict.
    """

    game_id: GameId
    action_id: ActionId
    period_id: int
    time_seconds: float
    team_id: TeamId
    player_id: PlayerId
    start_x: float
    start_y: float
    end_x: float
    end_y: float
    action_type: ActionType
    result: Result
    bodypart: BodyPart
    possession_id: int
    phase: Phase
    planted_moment_id: int | None = None

    @property
    def original_event_id(self) -> str:
        """The id SPADL keeps for the source event, e.g. ``"g12-e0345"``."""
        return f"g{self.game_id}-e{self.action_id:04d}"
