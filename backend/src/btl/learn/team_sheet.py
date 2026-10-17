"""The team sheet shown before a match: who plays for each side, growing with the viewer.

A beginner (stage 1) sees each starter's shirt number, name and position in plain words. Stage 2
adds each side's formation and where every starter stood at kick-off. The stage follows the
viewer's best concept: it is the level the selector would ask them about that concept at, so
one concept going well is enough to see more.

The sheet is about the line-ups only. It never looks at the match's events, so it can't hint
at what the viewer will be asked.
"""

from collections.abc import Iterable
from dataclasses import dataclass

from btl.league.league import Role
from btl.learn.selector import level_for
from btl.schema.frames import seen_by
from btl.schema.ids import ActionId, PlayerId, TeamId
from btl.schema.match import Match
from btl.sim.lineup import Lineup
from btl.sim.position_names import Position, position_names

STAGES = (1, 2, 3)
# The stage from which the sheet shows formations and kick-off positions.
SHAPE_STAGE = 2
ROLE_ORDER = (Role.GOALKEEPER, Role.DEFENDER, Role.MIDFIELDER, Role.FORWARD)


@dataclass(frozen=True, slots=True)
class SheetPlayer:
    """A starter on the sheet.

    ``at_kickoff`` is where they stood at kick-off, with the sheet's first team attacking
    towards x = 105; None before stage 2.
    """

    player_id: PlayerId
    shirt_number: int
    name: str
    role: Role
    position: Position
    at_kickoff: tuple[float, float] | None


@dataclass(frozen=True, slots=True)
class SheetTeam:
    """One side's starters: goalkeeper, defenders, midfielders, forwards, each line left to right.

    ``formation`` is None before stage 2.
    """

    team_id: TeamId
    name: str
    short_name: str
    home: bool
    yours: bool
    formation: str | None
    players: tuple[SheetPlayer, ...]


@dataclass(frozen=True, slots=True)
class TeamSheet:
    """Both sides before a match: the viewer's team first, or the home team if they have none."""

    match_number: int
    stage: int
    teams: tuple[SheetTeam, SheetTeam]


def sheet_stage(mastery: Iterable[float]) -> int:
    """The sheet's stage for a viewer: the level of their best concept."""
    return level_for(max(mastery, default=0.0))


def team_sheet(
    match: Match,
    lineups: tuple[Lineup, Lineup],
    match_number: int,
    stage: int,
    club: TeamId | None,
) -> TeamSheet:
    """The sheet for a match the viewer is about to watch.

    Args:
        match: The match, for its kick-off positions.
        lineups: The home and away elevens.
        match_number: Which of the viewer's matches it is.
        stage: How much to show, from `sheet_stage`.
        club: The viewer's team, if they have one.

    Raises:
        ValueError: If the stage is unknown, or a starter has no kick-off position.
    """
    if stage not in STAGES:
        raise ValueError(f"stage must be one of {STAGES}, got {stage}")
    playing = (match.home_team_id, match.away_team_id)
    first = club if club is not None and club in playing else match.home_team_id
    kickoff = _kickoff_spots(match, first) if stage >= SHAPE_STAGE else None
    teams = tuple(
        _team(lineup, match, kickoff, yours=lineup.club.team_id == club) for lineup in lineups
    )
    home, away = teams
    ordered = (home, away) if home.team_id == first else (away, home)
    return TeamSheet(match_number, stage, ordered)


def _kickoff_spots(match: Match, first: TeamId) -> dict[PlayerId, tuple[float, float]]:
    snapshot = seen_by(match, first).snapshot(ActionId(0))
    if snapshot is None:
        raise ValueError("the match has no kick-off positions")
    return {p.player_id: (p.x, p.y) for p in snapshot.positions}


def _team(
    lineup: Lineup,
    match: Match,
    kickoff: dict[PlayerId, tuple[float, float]] | None,
    *,
    yours: bool,
) -> SheetTeam:
    slots = lineup.formation.slots
    positions = position_names(lineup.formation)
    # Left to right as the team faces the goal it attacks: slots run from the right touchline.
    order = sorted(
        range(len(slots)),
        key=lambda i: (ROLE_ORDER.index(slots[i].role), slots[i].depth, -slots[i].across),
    )
    players: list[SheetPlayer] = []
    for index in order:
        player = lineup.players[index]
        spot = None
        if kickoff is not None:
            if player.player_id not in kickoff:
                raise ValueError(f"{player.full_name} has no kick-off position")
            spot = kickoff[player.player_id]
        players.append(
            SheetPlayer(
                player.player_id,
                player.shirt_number,
                player.full_name,
                player.role,
                positions[index],
                spot,
            )
        )
    club = lineup.club
    return SheetTeam(
        team_id=club.team_id,
        name=club.name,
        short_name=club.short_name,
        home=club.team_id == match.home_team_id,
        yours=yours,
        formation=lineup.formation.name if kickoff is not None else None,
        players=tuple(players),
    )
