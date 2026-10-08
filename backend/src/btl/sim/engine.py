"""Whole matches: two halves of possession chains, turned into numbered events.

The engine owns the clock and the event numbering, converts each chain's coordinates into the
stored direction (the home team attacks towards x = 105), and, unless asked not to, records
where all 22 players stood at the start of every event. A `Director` may write the opening of
any possession, such as a planted teachable moment.
"""

import numpy as np
from numpy.random import Generator
from numpy.typing import NDArray

from btl.league.league import Club, Role
from btl.schema.event import Event
from btl.schema.ids import ActionId, GameId
from btl.schema.match import Match
from btl.schema.moment import PlantedMoment
from btl.schema.snapshot import PlayerSlot, Positions
from btl.sim.chain import Chain, Side, Step, kickoff, play_chain, play_on
from btl.sim.lineup import Lineup, pick_lineup
from btl.sim.params import DEFAULT_PARAMS, SimParams
from btl.sim.pitch import Point, mirror
from btl.sim.script import Director, PlayOn, Shape
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
    director: Director | None = None,
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
        director: Writes the opening of chosen possessions. Play before its first script is
            the same as without it.

    Returns:
        The match, with positions for all 22 players at every event if requested, and the
        moments the director planted.
    """
    if home.team_id == away.team_id:
        raise ValueError(f"{home.name} can't play itself")
    # Child streams depend only on their index, so adding one leaves the others unchanged.
    engine_seed, shape_seed, director_seed = np.random.SeedSequence(seed).spawn(3)
    engine_rng = np.random.default_rng(engine_seed)
    director_rng = np.random.default_rng(director_seed)
    shape_rng = np.random.default_rng(shape_seed) if with_snapshots else None
    lineups = (pick_lineup(home, home_formation), pick_lineup(away, away_formation))
    sides = tuple(Side(lineup.formation, lineup.club.strength) for lineup in lineups)
    match_id = GameId(seed) if game_id is None else game_id

    events: list[Event] = []
    snapshots: list[NDArray[np.float64]] = []
    planted: list[PlantedMoment] = []
    # The moment being written, and the first and last action ids to mark with it.
    marking: tuple[int, int, int] | None = None
    possession_id = 0
    for period_id, team in ((1, HOME), (2, AWAY)):
        start, clock = kickoff(sides[team]), 0.0
        while True:
            clock += start.delay
            if clock >= params.period_seconds:
                break
            attack, defence = sides[team], sides[1 - team]
            script = (
                None
                if director is None
                else director.script(
                    len(planted), period_id, clock, attack, defence, start, director_rng
                )
            )
            shapes: dict[int, Shape] = {}
            if script is None:
                chain = play_chain(attack, defence, start, engine_rng, params)
            else:
                if isinstance(script.then, PlayOn):
                    won_the_ball = start.won_with is not None
                    chain = play_on(
                        attack,
                        defence,
                        script.steps,
                        script.then.ball,
                        script.then.slot,
                        won_the_ball,
                        engine_rng,
                        params,
                    )
                else:
                    chain = Chain(script.steps, script.then)
                shapes = dict(script.shapes)
                marking = (len(planted), len(events), len(events) + script.answer)
                planted.append(
                    PlantedMoment(
                        script.concept,
                        script.difficulty,
                        ActionId(len(events) + script.pause),
                        ActionId(len(events) + script.answer),
                    )
                )
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
                        _moment_of(len(events), marking),
                    )
                )
                if shape_rng is not None and index in shapes:
                    snapshots.append(_stored_positions(sides, team, *shapes[index]))
                elif shape_rng is not None:
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
        planted=tuple(planted),
    )


def _moment_of(action_id: int, marking: tuple[int, int, int] | None) -> int | None:
    """The planted moment an action belongs to: from its script's first step to its answer."""
    if marking is None:
        return None
    moment_id, first, last = marking
    return moment_id if first <= action_id <= last else None


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
    planted_moment_id: int | None,
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
        planted_moment_id=planted_moment_id,
    )


def _snapshot(
    sides: tuple[Side, ...], team: int, holder: int, step: Step, rng: Generator
) -> NDArray[np.float64]:
    """All 22 stored positions, home slots first, with the actor exactly on the ball."""
    ball = step.start if holder == team else mirror(step.start)
    on_ball, off_ball = place_teams(sides[holder].formation, sides[1 - holder].formation, ball, rng)
    xy = _stored_positions(sides, holder, on_ball, off_ball)
    actor = _stored(step.start, team)
    xy[team * len(sides[HOME].formation.slots) + step.slot] = (actor.x, actor.y)
    return xy


def _stored_positions(
    sides: tuple[Side, ...], holder: int, on_ball: tuple[Point, ...], off_ball: tuple[Point, ...]
) -> NDArray[np.float64]:
    """Both teams' positions, given in ``holder``'s direction, as stored rows: home slots first."""
    per_team = {holder: on_ball, 1 - holder: off_ball}
    xy = np.empty((sum(len(side.formation.slots) for side in sides), 2))
    row = 0
    for each_team in (HOME, AWAY):
        for point in per_team[each_team]:
            stored = _stored(point, holder)
            xy[row] = (stored.x, stored.y)
            row += 1
    return xy
