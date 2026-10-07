"""Small hand-built matches for the concept detectors."""

import numpy as np

from btl.schema.ids import PlayerId, TeamId
from btl.schema.match import Match
from btl.schema.snapshot import PlayerSlot, Positions
from btl.schema.vocab import ActionType, Result
from tests.fixtures.matches import AWAY, AWAY_MIDFIELDER, GAME, HOME, HOME_MIDFIELDER, make_event

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
