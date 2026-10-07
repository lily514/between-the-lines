"""Typed ids, so that a player id can't be passed where a team id is expected."""

from typing import NewType

GameId = NewType("GameId", int)
TeamId = NewType("TeamId", int)
PlayerId = NewType("PlayerId", int)
ActionId = NewType("ActionId", int)
