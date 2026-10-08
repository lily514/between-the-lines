"""Player positions: stored per match as one array, viewed one moment at a time."""

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from btl.schema.ids import ActionId, GameId, PlayerId, TeamId


@dataclass(frozen=True, slots=True)
class PlayerPosition:
    """Where one player stood at the start of an action."""

    player_id: PlayerId
    team_id: TeamId
    x: float
    y: float
    is_actor: bool
    is_goalkeeper: bool


@dataclass(frozen=True, slots=True)
class Snapshot:
    """The positions of every known player at the start of one action."""

    game_id: GameId
    action_id: ActionId
    positions: tuple[PlayerPosition, ...]


@dataclass(frozen=True, slots=True)
class PlayerSlot:
    """A player tracked for the whole match: one column of `Positions.xy`."""

    player_id: PlayerId
    team_id: TeamId
    is_goalkeeper: bool


@dataclass(frozen=True, slots=True, eq=False)
class Positions:
    """Where each tracked player stood at the start of every action in a match.

    ``xy`` has shape ``(actions, len(slots), 2)``, indexed by action id. NaN means the position
    is unknown, so a data source can supply partial snapshots or none for some actions.
    """

    slots: tuple[PlayerSlot, ...]
    xy: NDArray[np.float64]

    def __post_init__(self) -> None:
        """Reject an array whose shape doesn't match the slots."""
        if self.xy.ndim != 3 or self.xy.shape[1:] != (len(self.slots), 2):
            raise ValueError(
                f"xy must have shape (actions, {len(self.slots)}, 2), got {self.xy.shape}"
            )

    def __eq__(self, other: object) -> bool:
        """Compare slots and coordinates, treating unknown positions as equal."""
        if not isinstance(other, Positions):
            return NotImplemented
        return self.slots == other.slots and np.array_equal(self.xy, other.xy, equal_nan=True)

    @property
    def n_actions(self) -> int:
        """How many actions the array covers."""
        return self.xy.shape[0]
