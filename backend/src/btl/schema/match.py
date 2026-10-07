"""A whole match: its events and, optionally, where the players stood."""

from dataclasses import dataclass

import numpy as np

from btl.schema.event import Event
from btl.schema.ids import ActionId, GameId, TeamId
from btl.schema.snapshot import PlayerPosition, Positions, Snapshot


@dataclass(frozen=True, slots=True)
class Match:
    """One match. Action ids run 0 … n-1 in event order, so they double as indexes."""

    game_id: GameId
    home_team_id: TeamId
    away_team_id: TeamId
    events: tuple[Event, ...]
    positions: Positions | None = None

    def __post_init__(self) -> None:
        """Check that events are numbered in order and belong to this match."""
        for index, event in enumerate(self.events):
            if event.action_id != index:
                raise ValueError(f"event {index} has action_id {event.action_id}")
            if event.game_id != self.game_id:
                raise ValueError(f"event {index} belongs to game {event.game_id}")
            if event.team_id not in (self.home_team_id, self.away_team_id):
                raise ValueError(f"event {index} is by team {event.team_id}, not in this match")
        if self.positions is not None and self.positions.n_actions != len(self.events):
            raise ValueError(
                f"positions cover {self.positions.n_actions} actions, "
                f"but the match has {len(self.events)}"
            )

    def snapshot(self, action_id: ActionId) -> Snapshot | None:
        """The known player positions at the start of an action, or None if there are none."""
        if self.positions is None:
            return None
        event = self.events[action_id]
        xy = self.positions.xy[action_id]
        known = ~np.isnan(xy).any(axis=1)
        if not known.any():
            return None
        positions = tuple(
            PlayerPosition(
                player_id=slot.player_id,
                team_id=slot.team_id,
                x=float(xy[index, 0]),
                y=float(xy[index, 1]),
                is_actor=slot.player_id == event.player_id,
                is_goalkeeper=slot.is_goalkeeper,
            )
            for index, slot in enumerate(self.positions.slots)
            if known[index]
        )
        return Snapshot(game_id=self.game_id, action_id=action_id, positions=positions)
