"""The team sheet shown before a match: who plays for each side, growing with the viewer.

A beginner (stage 1) sees each starter's shirt number, name, position in plain words and where
they stood at kick-off, so the page can put them on a pitch. Stage 2 adds each side's formation.
Stage 3 adds each
player's numbers from the matches the viewer has finished (`btl.learn.player_stats`). The stage
follows the viewer's best concept: it is the level the selector would ask them about that
concept at, so one concept going well is enough to see more.

The sheet never looks at the coming match's events, only at its line-ups and kick-off, so it
can't hint at what the viewer will be asked.
"""

from collections.abc import Callable, Iterable
from dataclasses import dataclass

from btl.league.league import Role
from btl.learn.learner import LearnerState
from btl.learn.player_stats import NO_NUMBERS, PlayerStats, WatchedNumbers, watched_numbers
from btl.learn.selector import level_for
from btl.learn.session import Course, PreparedMatch
from btl.schema.frames import seen_by
from btl.schema.ids import ActionId, PlayerId, TeamId
from btl.schema.match import Match
from btl.sim.lineup import Lineup
from btl.sim.position_names import Position, position_names

STAGES = (1, 2, 3)
# The stages from which the sheet shows formations, then numbers.
SHAPE_STAGE = 2
NUMBERS_STAGE = 3
ROLE_ORDER = (Role.GOALKEEPER, Role.DEFENDER, Role.MIDFIELDER, Role.FORWARD)
# What opens the next stage, shown under the sheet so the viewer knows it will grow.
NEXT_STAGE: dict[int, str] = {
    1: "Get to level 2 in any concept to see formations and position tags.",
    2: "Get to level 3 in any concept to see players' numbers from matches you've watched.",
}


@dataclass(frozen=True, slots=True)
class SheetPlayer:
    """A starter on the sheet.

    ``at_kickoff`` is where they stood at kick-off, with the sheet's first team attacking
    towards x = 105. ``numbers`` are from the watched matches they
    started; None before stage 3, or if the viewer hasn't seen them play.
    """

    player_id: PlayerId
    shirt_number: int
    name: str
    role: Role
    position: Position
    at_kickoff: tuple[float, float]
    numbers: PlayerStats | None


@dataclass(frozen=True, slots=True)
class SheetTeam:
    """One side's starters: goalkeeper, defenders, midfielders, forwards, each line left to right.

    ``formation`` is None before stage 2. ``matches_watched`` counts the viewer's finished
    matches the club played in; None before stage 3.
    """

    team_id: TeamId
    name: str
    short_name: str
    home: bool
    yours: bool
    formation: str | None
    matches_watched: int | None
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


def viewer_sheet(
    course: Course, state: LearnerState, prepare: Callable[[int, int, TeamId | None], PreparedMatch]
) -> TeamSheet:
    """The sheet for the match a viewer is about to watch, at the stage they have reached.

    Args:
        course: What every viewer shares.
        state: The viewer's record; they mustn't have finished.
        prepare: Gives the prepared match for a session seed, match number and club.
    """
    stage = sheet_stage(course.bars(state).values())
    current = prepare(state.seed, state.match_number, state.club)
    numbers = finished_numbers(state, prepare) if stage >= NUMBERS_STAGE else NO_NUMBERS
    return team_sheet(
        current.match, current.lineups, state.match_number, stage, state.club, numbers
    )


def finished_numbers(
    state: LearnerState, prepare: Callable[[int, int, TeamId | None], PreparedMatch]
) -> WatchedNumbers:
    """Every player's numbers from the matches the viewer has finished, never the current one."""
    finished = [prepare(state.seed, number, state.club) for number in range(1, state.match_number)]
    return watched_numbers(
        (prepared.ctx, [p.player_id for lineup in prepared.lineups for p in lineup.players])
        for prepared in finished
    )


def team_sheet(
    match: Match,
    lineups: tuple[Lineup, Lineup],
    match_number: int,
    stage: int,
    club: TeamId | None,
    numbers: WatchedNumbers = NO_NUMBERS,
) -> TeamSheet:
    """The sheet for a match the viewer is about to watch.

    Args:
        match: The match, for its kick-off positions.
        lineups: The home and away elevens.
        match_number: Which of the viewer's matches it is.
        stage: How much to show, from `sheet_stage`.
        club: The viewer's team, if they have one.
        numbers: From the matches the viewer has finished; shown from stage 3.

    Raises:
        ValueError: If the stage is unknown, or a starter has no kick-off position.
    """
    if stage not in STAGES:
        raise ValueError(f"stage must be one of {STAGES}, got {stage}")
    playing = (match.home_team_id, match.away_team_id)
    first = club if club is not None and club in playing else match.home_team_id
    kickoff = _kickoff_spots(match, first)
    shown = numbers if stage >= NUMBERS_STAGE else None
    teams = tuple(
        _team(
            lineup,
            match,
            kickoff,
            shown,
            yours=lineup.club.team_id == club,
            shape=stage >= SHAPE_STAGE,
        )
        for lineup in lineups
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
    kickoff: dict[PlayerId, tuple[float, float]],
    numbers: WatchedNumbers | None,
    *,
    yours: bool,
    shape: bool,
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
        if player.player_id not in kickoff:
            raise ValueError(f"{player.full_name} has no kick-off position")
        players.append(
            SheetPlayer(
                player.player_id,
                player.shirt_number,
                player.full_name,
                player.role,
                positions[index],
                kickoff[player.player_id],
                None if numbers is None else numbers.players.get(player.player_id),
            )
        )
    club = lineup.club
    return SheetTeam(
        team_id=club.team_id,
        name=club.name,
        short_name=club.short_name,
        home=club.team_id == match.home_team_id,
        yours=yours,
        formation=lineup.formation.name if shape else None,
        matches_watched=None if numbers is None else numbers.team_matches.get(club.team_id, 0),
        players=tuple(players),
    )
