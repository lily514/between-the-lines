"""Small hand-built matches for the concept detectors."""

from btl.schema.ids import PlayerId
from btl.schema.match import Match
from btl.schema.vocab import ActionType, Result
from tests.fixtures.matches import AWAY, AWAY_MIDFIELDER, GAME, HOME, HOME_MIDFIELDER, make_event

HOME_WINGER = PlayerId(12)


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
