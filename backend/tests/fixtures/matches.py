"""Small hand-built matches for schema and detector tests."""

from dataclasses import replace

import numpy as np

from btl.schema.event import Event
from btl.schema.ids import ActionId, GameId, PlayerId, TeamId
from btl.schema.match import Match
from btl.schema.snapshot import PlayerSlot, Positions
from btl.schema.vocab import ActionType, BodyPart, Phase, Result

GAME = GameId(1)
HOME = TeamId(1)
AWAY = TeamId(2)

HOME_KEEPER = PlayerId(10)
HOME_MIDFIELDER = PlayerId(11)
HOME_WINGER = PlayerId(12)  # not tracked in the snapshots
AWAY_KEEPER = PlayerId(20)
AWAY_MIDFIELDER = PlayerId(21)


def make_event(
    action_id: int,
    team_id: TeamId,
    player_id: PlayerId,
    start: tuple[float, float],
    end: tuple[float, float],
    action_type: ActionType = ActionType.PASS,
    result: Result = Result.SUCCESS,
    period_id: int = 1,
) -> Event:
    """An event with sensible defaults for everything a test doesn't care about."""
    return Event(
        game_id=GAME,
        action_id=ActionId(action_id),
        period_id=period_id,
        time_seconds=float(action_id * 4),
        team_id=team_id,
        player_id=player_id,
        start_x=start[0],
        start_y=start[1],
        end_x=end[0],
        end_y=end[1],
        action_type=action_type,
        result=result,
        bodypart=BodyPart.FOOT,
        possession_id=0,
        phase=Phase.OPEN_PLAY,
    )


def six_event_match() -> Match:
    """Home builds up and loses the ball; away intercepts, survives a tackle, and passes on.

    Coordinates are stored: home attacks towards x = 105, away towards x = 0. Positions are
    tracked for four players, and are unknown for action 4.
    """
    events = (
        make_event(0, HOME, HOME_MIDFIELDER, (40, 34), (60, 30)),
        make_event(1, HOME, HOME_WINGER, (60, 30), (70, 30), ActionType.DRIBBLE),
        make_event(2, HOME, HOME_WINGER, (70, 30), (85, 40), result=Result.FAIL),
        make_event(3, AWAY, AWAY_MIDFIELDER, (85, 40), (85, 40), ActionType.INTERCEPTION),
        make_event(4, HOME, HOME_MIDFIELDER, (75, 35), (75, 35), ActionType.TACKLE, Result.FAIL),
        make_event(5, AWAY, AWAY_MIDFIELDER, (75, 35), (50, 30)),
    )
    events = tuple(
        replace(event, possession_id=0 if event.action_id < 3 else 1) for event in events
    )
    slots = (
        PlayerSlot(HOME_KEEPER, HOME, is_goalkeeper=True),
        PlayerSlot(HOME_MIDFIELDER, HOME, is_goalkeeper=False),
        PlayerSlot(AWAY_KEEPER, AWAY, is_goalkeeper=True),
        PlayerSlot(AWAY_MIDFIELDER, AWAY, is_goalkeeper=False),
    )
    keepers_and_midfielders = [
        [[5, 34], [40, 34], [100, 34], [55, 36]],
        [[6, 34], [50, 32], [100, 34], [62, 34]],
        [[7, 34], [55, 32], [99, 35], [72, 37]],
        [[7, 34], [58, 33], [98, 36], [85, 40]],
        [[np.nan, np.nan]] * 4,
        [[6, 34], [74, 35], [99, 34], [75, 35]],
    ]
    positions = Positions(slots=slots, xy=np.array(keepers_and_midfielders, dtype=np.float64))
    return Match(
        game_id=GAME, home_team_id=HOME, away_team_id=AWAY, events=events, positions=positions
    )
