"""Small hand-built matches for the concept detectors."""

from dataclasses import replace

import numpy as np

from btl.schema.event import Event
from btl.schema.ids import PlayerId, TeamId
from btl.schema.match import Match
from btl.schema.snapshot import PlayerSlot, Positions
from btl.schema.vocab import ActionType, Result
from tests.fixtures.matches import (
    AWAY,
    AWAY_MIDFIELDER,
    GAME,
    HOME,
    HOME_MIDFIELDER,
    make_event,
)

HOME_WINGER = PlayerId(12)
DEFENDER_IDS = 100
KEEPER_ID = PlayerId(99)

Spot = tuple[float, float]

# Two banks of four, in the home team's attacking direction (towards x = 105). The midfield
# line's gaps are 14, 12 and 14 m; the pitch's centre (y = 34) is in the 12 m gap.
MIDFIELD_LINE: tuple[Spot, ...] = ((50, 14), (50, 28), (50, 40), (50, 54))
BACK_LINE: tuple[Spot, ...] = ((75, 15), (75, 28), (75, 40), (75, 53))
TWO_FORWARDS: tuple[Spot, ...] = ((50, 30), (50, 38))


def switches_match() -> Match:
    """Two switches of play, one by each team, among passes that nearly qualify.

    Stored coordinates: home attacks towards x = 105, away towards x = 0.

    - 0: home, 45 m across from the right flank to the left: a switch.
    - 1: 31 m across but ends in the middle third: no.
    - 2: from the middle to the left flank, only 26 m across: no.
    - 3: a dribble 38 m across: no, only passes and crosses count.
    - 4: 48 m across but intercepted: no.
    - 5: away wins the ball.
    - 6: away, 52 m across to the far flank: a switch.
    """
    events = (
        make_event(0, HOME, HOME_MIDFIELDER, (40, 10), (55, 55)),
        make_event(1, HOME, HOME_WINGER, (55, 55), (60, 24)),
        make_event(2, HOME, HOME_MIDFIELDER, (60, 24), (62, 50)),
        make_event(3, HOME, HOME_WINGER, (62, 50), (70, 12), ActionType.DRIBBLE),
        make_event(4, HOME, HOME_WINGER, (70, 12), (72, 60), result=Result.FAIL),
        make_event(5, AWAY, AWAY_MIDFIELDER, (72, 60), (72, 60), ActionType.INTERCEPTION),
        make_event(6, AWAY, AWAY_MIDFIELDER, (72, 60), (60, 8)),
    )
    return Match(game_id=GAME, home_team_id=HOME, away_team_id=AWAY, events=events)


def one_pass(
    start: Spot,
    end: Spot,
    defenders: tuple[Spot, ...],
    *,
    team: TeamId = HOME,
    result: Result = Result.SUCCESS,
    with_snapshot: bool = True,
) -> Match:
    """A one-event match: a pass, with the passer, the defenders and their keeper tracked.

    Everything is in stored coordinates. The defending keeper stands on their goal line.
    """
    other = AWAY if team == HOME else HOME
    passer = HOME_MIDFIELDER if team == HOME else AWAY_MIDFIELDER
    event = make_event(0, team, passer, start, end, result=result)
    if not with_snapshot:
        return Match(game_id=GAME, home_team_id=HOME, away_team_id=AWAY, events=(event,))
    keeper_spot = (104.0, 34.0) if other == AWAY else (1.0, 34.0)
    slots = (
        PlayerSlot(passer, team, is_goalkeeper=False),
        PlayerSlot(KEEPER_ID, other, is_goalkeeper=True),
        *(PlayerSlot(PlayerId(DEFENDER_IDS + i), other, False) for i in range(len(defenders))),
    )
    xy = np.array([[start, keeper_spot, *defenders]], dtype=np.float64)
    return Match(
        game_id=GAME,
        home_team_id=HOME,
        away_team_id=AWAY,
        events=(event,),
        positions=Positions(slots=slots, xy=xy),
    )


def mirrored(spots: tuple[Spot, ...]) -> tuple[Spot, ...]:
    """The same spots seen from the other end: for building an away team's fixtures."""
    return tuple((105 - x, 68 - y) for x, y in spots)


LOST_AT = 23.0


def lost_and_won_back(
    seconds: float,
    where: Spot,
    *,
    team: TeamId = HOME,
    lost_with: ActionType = ActionType.INTERCEPTION,
    won_with: ActionType = ActionType.TACKLE,
) -> Match:
    """A team loses the ball at ``LOST_AT`` seconds and wins it back ``seconds`` later.

    ``where`` is the spot it wins the ball back, seen as if ``team`` attacks towards x = 105;
    the match stores it, like everything else, in the team's real direction.

    - 0: ``team`` passes forward.
    - 1: its pass towards the opponent's box fails.
    - 2: the opponent wins the ball (``lost_with``).
    - 3: the opponent passes to ``where``.
    - 4: ``team`` wins it back there (``won_with``).
    - 5: ``team`` passes on.
    """
    other = AWAY if team == HOME else HOME
    ours = HOME_MIDFIELDER if team == HOME else AWAY_MIDFIELDER
    theirs = AWAY_MIDFIELDER if team == HOME else HOME_MIDFIELDER
    timed = (
        (20.0, make_event(0, team, ours, (40, 34), (65, 30))),
        (22.0, make_event(1, team, ours, (65, 30), (80, 40), result=Result.FAIL)),
        (LOST_AT, make_event(2, other, theirs, (80, 40), (80, 40), lost_with)),
        (LOST_AT + 0.5, make_event(3, other, theirs, (80, 40), where)),
        (LOST_AT + seconds, make_event(4, team, ours, where, where, won_with)),
        (LOST_AT + seconds + 1, make_event(5, team, ours, where, (90, 34))),
    )
    events = tuple(replace(event, time_seconds=time) for time, event in timed)
    if team == AWAY:
        events = tuple(_mirror_event(event) for event in events)
    return Match(game_id=GAME, home_team_id=HOME, away_team_id=AWAY, events=events)


def _mirror_event(event: Event) -> Event:
    (start, end) = mirrored(((event.start_x, event.start_y), (event.end_x, event.end_y)))
    return replace(event, start_x=start[0], start_y=start[1], end_x=end[0], end_y=end[1])


WON_AT = 30.0


def won_and_carried(
    seconds: float,
    where: Spot,
    *,
    team: TeamId = HOME,
    won_with: ActionType = ActionType.INTERCEPTION,
) -> Match:
    """A team wins the ball at ``where`` at ``WON_AT`` seconds and is in the box ``seconds`` later.

    ``where`` is seen as if ``team`` attacks towards x = 105, like the other spots; the match
    stores everything in the team's real direction.

    - 0: the opponent passes towards ``where``, and it's cut out.
    - 1: ``team`` wins the ball there (``won_with``).
    - 2: ``team`` passes forward, to the edge of the box.
    - 3: ``team`` shoots from inside the box.
    """
    other = AWAY if team == HOME else HOME
    ours = HOME_MIDFIELDER if team == HOME else AWAY_MIDFIELDER
    theirs = AWAY_MIDFIELDER if team == HOME else HOME_MIDFIELDER
    timed = (
        (WON_AT - 2, make_event(0, other, theirs, (70, 30), where, result=Result.FAIL)),
        (WON_AT, make_event(1, team, ours, where, where, won_with)),
        (WON_AT + 1, make_event(2, team, ours, where, (92, 40))),
        (WON_AT + seconds, make_event(3, team, ours, (92, 40), (105, 34), ActionType.SHOT)),
    )
    events = tuple(replace(event, time_seconds=time) for time, event in timed)
    if team == AWAY:
        events = tuple(_mirror_event(event) for event in events)
    return Match(game_id=GAME, home_team_id=HOME, away_team_id=AWAY, events=events)


def out_and_restart(
    out: tuple[TeamId, ActionType, Result],
    restart: tuple[TeamId, ActionType, Spot],
    period: int = 1,
) -> Match:
    """A two-event match: an action that ends with the ball out of play, then the restart.

    Stored coordinates. The first action runs from midfield towards the restart's spot.
    """
    team, action, result = out
    by, kind, spot = restart
    first_player = HOME_MIDFIELDER if team == HOME else AWAY_MIDFIELDER
    second_player = HOME_MIDFIELDER if by == HOME else AWAY_MIDFIELDER
    events = (
        make_event(0, team, first_player, (52, 34), spot, action, result),
        make_event(1, by, second_player, spot, (spot[0], 34), kind, period_id=period),
    )
    return Match(game_id=GAME, home_team_id=HOME, away_team_id=AWAY, events=events)


ATTACKER_ID = PlayerId(13)
# Their keeper on the line and a back four at x = 80, in the home team's direction.
OFFSIDE_DEFENCE: tuple[Spot, ...] = ((104, 34), (80, 15), (80, 28), (80, 40), (80, 53))


def pass_to(
    receiver: Spot,
    *,
    start: Spot = (70, 34),
    end: Spot = (90, 30),
    result: Result = Result.SUCCESS,
    action: ActionType = ActionType.PASS,
    other_attacker: Spot | None = None,
    defence: tuple[Spot, ...] = OFFSIDE_DEFENCE,
) -> Match:
    """A home pass, with the passer, a receiver and the defence (their keeper first) tracked.

    Stored coordinates, home attacking towards x = 105. A completed pass is followed by the
    receiver's action from ``end``. ``other_attacker`` adds a second, tracked teammate.
    """
    first = make_event(0, HOME, HOME_MIDFIELDER, start, end, action, result)
    events = [first]
    if result is Result.SUCCESS:
        events.append(make_event(1, HOME, HOME_WINGER, end, (end[0] + 5, end[1])))
    slots = [
        PlayerSlot(HOME_MIDFIELDER, HOME, is_goalkeeper=False),
        PlayerSlot(HOME_WINGER, HOME, is_goalkeeper=False),
        PlayerSlot(KEEPER_ID, AWAY, is_goalkeeper=True),
        *(PlayerSlot(PlayerId(DEFENDER_IDS + i), AWAY, False) for i in range(4)),
    ]
    spots = [start, receiver, *defence]
    if other_attacker is not None:
        slots.append(PlayerSlot(ATTACKER_ID, HOME, is_goalkeeper=False))
        spots.append(other_attacker)
    xy = np.full((len(events), len(slots), 2), np.nan)
    xy[0] = spots
    return Match(
        game_id=GAME,
        home_team_id=HOME,
        away_team_id=AWAY,
        events=tuple(events),
        positions=Positions(slots=tuple(slots), xy=xy),
    )


def chance_and_shot(
    start: Spot,
    end: Spot,
    *,
    result: Result = Result.FAIL,
    made_by: ActionType | None = ActionType.PASS,
    saved: bool = False,
    kind: ActionType = ActionType.SHOT,
    team: TeamId = HOME,
) -> Match:
    """A team's action makes a chance, and it shoots; then what the shot leads to.

    ``start`` and ``end`` are seen as if ``team`` attacks towards x = 105; the match stores
    everything in the team's real direction.

    - 0: the ``made_by`` action from (70, 20) to ``start``, or the other team's failed pass
      there when None, so the shot opens the possession.
    - 1: the shot (``kind``), from ``start`` to ``end``.
    - 2: the other team's keeper saves it, or the kickoff after a goal, or a goal kick.
    """
    other = AWAY if team == HOME else HOME
    ours = HOME_MIDFIELDER if team == HOME else AWAY_MIDFIELDER
    theirs = AWAY_MIDFIELDER if team == HOME else HOME_MIDFIELDER
    their_keeper = KEEPER_ID
    if made_by is None:
        first = make_event(0, other, theirs, (70, 20), start, result=Result.FAIL)
    else:
        first = make_event(0, team, ours, (70, 20), start, made_by)
    events = [first, make_event(1, team, ours, start, end, kind, result)]
    if saved:
        events.append(make_event(2, other, their_keeper, end, end, ActionType.KEEPER_SAVE))
    elif result is Result.SUCCESS:
        events.append(make_event(2, other, theirs, (52.5, 34), (45, 30)))
    else:
        events.append(make_event(2, other, their_keeper, (99.5, 34), (70, 34), ActionType.GOALKICK))
    if team == AWAY:
        events = [_mirror_event(event) for event in events]
    return Match(game_id=GAME, home_team_id=HOME, away_team_id=AWAY, events=tuple(events))


def fouled(
    where: Spot,
    *,
    passes_first: int = 1,
    result: Result = Result.FAIL,
    then: ActionType = ActionType.FREEKICK_SHORT,
) -> Match:
    """Home wins the ball, passes, and is fouled by away at ``where``; then home's ``then``.

    Stored coordinates, home attacking towards x = 105. Each action takes 4 seconds, so one
    pass leaves home in a transition and five have it settled. ``then`` is a free kick, a
    penalty (taken from the spot) or, for advantage, any other action.
    """
    events = [
        make_event(0, AWAY, AWAY_MIDFIELDER, (60, 34), (40, 34), result=Result.FAIL),
        make_event(1, HOME, HOME_MIDFIELDER, (40, 34), (40, 34), ActionType.INTERCEPTION),
    ]
    events += [
        make_event(2 + k, HOME, HOME_MIDFIELDER, (40, 34), where) for k in range(passes_first)
    ]
    at = len(events)
    events.append(make_event(at, AWAY, AWAY_MIDFIELDER, where, where, ActionType.FOUL, result))
    spot = (94.0, 34.0) if then is ActionType.SHOT_PENALTY else where
    events.append(make_event(at + 1, HOME, HOME_MIDFIELDER, spot, (spot[0] + 5, spot[1]), then))
    return Match(game_id=GAME, home_team_id=HOME, away_team_id=AWAY, events=tuple(events))
