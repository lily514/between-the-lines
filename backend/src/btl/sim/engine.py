"""Whole matches: two halves of possession chains, turned into numbered events.

The engine owns the clock and the event numbering, converts each chain's coordinates into the
stored direction (the home team attacks towards x = 105), and, unless asked not to, records
where all 22 players stood at the start of every event.
"""

import numpy as np
from numpy.random import Generator
from numpy.typing import NDArray

from btl.league.league import Club, Role
from btl.schema.event import Event
from btl.schema.ids import ActionId, GameId
from btl.schema.match import Match
from btl.schema.snapshot import PlayerSlot, Positions
from btl.sim.chain import Side, Step, kickoff, play_chain
from btl.sim.lineup import Lineup, pick_lineup
from btl.sim.params import DEFAULT_PARAMS, SimParams
from btl.sim.pitch import Point, mirror
from btl.sim.shape import FOUR_FOUR_TWO, Formation, place_teams

HOME, AWAY = 0, 1


def simulate_match(
    home: Club,
    away: Club,
    seed: int,
    *,
    game_id: GameId | None = None,
    home_formation: Formation = FOUR_FOUR_TWO,
    away_formation: Formation = FOUR_FOUR_TWO,
    with_snapshots: bool = True,
    params: SimParams = DEFAULT_PARAMS,
) -> Match:
    """Simulate a match of open play between two clubs.

    The home team kicks off the first half and the away team the second. Each team starts
    its usual first-choice eleven for its formation.

    Args:
        home: The home club.
        away: The away club.
        seed: The same seed always gives the same match.
        game_id: The match's id; defaults to the seed.
        home_formation: The home team's formation.
        away_formation: The away team's formation.
        with_snapshots: Record player positions. Turning this off makes batch runs faster
            and doesn't change the events.
        params: The simulator's knobs.

    Returns:
        The match, with positions for all 22 players at every event if requested.
    """
    if home.team_id == away.team_id:
        raise ValueError(f"{home.name} can't play itself")
    # Child streams depend only on their index, so spawning more later (e.g. for planting)
    # leaves these two unchanged.
    engine_seed, shape_seed = np.random.SeedSequence(seed).spawn(2)
    engine_rng = np.random.default_rng(engine_seed)
    shape_rng = np.random.default_rng(shape_seed) if with_snapshots else None
    lineups = (pick_lineup(home, home_formation), pick_lineup(away, away_formation))
    sides = tuple(Side(lineup.formation, lineup.club.strength) for lineup in lineups)
    match_id = GameId(seed) if game_id is None else game_id

    events: list[Event] = []
    snapshots: list[NDArray[np.float64]] = []
    possession_id = 0
    for period_id, team in ((1, HOME), (2, AWAY)):
        start, clock = kickoff(sides[team]), 0.0
        while True:
            clock += start.delay
            if clock >= params.period_seconds:
                break
            chain = play_chain(sides[team], sides[1 - team], start, engine_rng, params)
            for index, step in enumerate(chain.steps):
                if clock >= params.period_seconds:
                    break
                events.append(
                    _event(
                        match_id,
                        len(events),
                        period_id,
                        clock,
                        lineups[team],
                        team,
                        step,
                        possession_id,
                    )
                )
                if shape_rng is not None:
                    # Positions are at the start of the action. When it wins the ball, the
                    # other team still has it at that moment.
                    holder = 1 - team if index == 0 and start.won_with is not None else team
                    snapshots.append(_snapshot(sides, team, holder, step, shape_rng))
                clock += step.duration
            possession_id += 1
            team, start = 1 - team, chain.next_start

    positions = None
    if shape_rng is not None:
        slots = tuple(
            PlayerSlot(player.player_id, player.team_id, player.role is Role.GOALKEEPER)
            for lineup in lineups
            for player in lineup.players
        )
        positions = Positions(slots=slots, xy=np.stack(snapshots))
    return Match(
        game_id=match_id,
        home_team_id=home.team_id,
        away_team_id=away.team_id,
        events=tuple(events),
        positions=positions,
    )


def _stored(point: Point, team: int) -> Point:
    """From a team's attacking direction to the stored one."""
    return point if team == HOME else mirror(point)


def _event(
    game_id: GameId,
    action_id: int,
    period_id: int,
    clock: float,
    lineup: Lineup,
    team: int,
    step: Step,
    possession_id: int,
) -> Event:
    start, end = _stored(step.start, team), _stored(step.end, team)
    return Event(
        game_id=game_id,
        action_id=ActionId(action_id),
        period_id=period_id,
        time_seconds=clock,
        team_id=lineup.club.team_id,
        player_id=lineup.players[step.slot].player_id,
        start_x=start.x,
        start_y=start.y,
        end_x=end.x,
        end_y=end.y,
        action_type=step.action_type,
        result=step.result,
        bodypart=step.bodypart,
        possession_id=possession_id,
        phase=step.phase,
    )


def _snapshot(
    sides: tuple[Side, ...], team: int, holder: int, step: Step, rng: Generator
) -> NDArray[np.float64]:
    """All 22 stored positions, home slots first, with the actor exactly on the ball."""
    ball = step.start if holder == team else mirror(step.start)
    on_ball, off_ball = place_teams(sides[holder].formation, sides[1 - holder].formation, ball, rng)
    per_team = {holder: on_ball, 1 - holder: off_ball}
    xy = np.empty((sum(len(side.formation.slots) for side in sides), 2))
    row = 0
    for each_team in (HOME, AWAY):
        for point in per_team[each_team]:
            stored = _stored(point, holder)
            xy[row] = (stored.x, stored.y)
            row += 1
    actor = _stored(step.start, team)
    xy[team * len(sides[HOME].formation.slots) + step.slot] = (actor.x, actor.y)
    return xy
