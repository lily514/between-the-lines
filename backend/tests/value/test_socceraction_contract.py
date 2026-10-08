# pyright: basic
# pandas and socceraction are only partially typed; see CLAUDE.md on edge modules.
"""Pins down the socceraction behaviour this project relies on.

If socceraction is upgraded and one of these fails, the assumption it names has changed.
"""

import numpy as np
import pandas as pd
import pandera.errors
import pytest
from pandera.typing import DataFrame
from socceraction import xthreat
from socceraction.spadl import SPADLSchema, play_left_to_right

from btl.schema.vocab import ActionType, BodyPart, Result

HOME = 1
AWAY = 2


def _action(
    action_id: int,
    team_id: int,
    start: tuple[float, float],
    end: tuple[float, float],
    action_type: ActionType,
    result: Result = Result.SUCCESS,
) -> dict[str, object]:
    return {
        "game_id": 1,
        "original_event_id": f"e{action_id}",
        "action_id": action_id,
        "period_id": 1,
        "time_seconds": float(action_id * 3),
        "team_id": team_id,
        "player_id": team_id * 100 + action_id,
        "start_x": start[0],
        "start_y": start[1],
        "end_x": end[0],
        "end_y": end[1],
        "type_id": int(action_type),
        "result_id": int(result),
        "bodypart_id": int(BodyPart.FOOT),
    }


def _ten_actions() -> DataFrame[SPADLSchema]:
    """Home builds up and scores twice; away attacks the other way and loses the ball.

    Stored in the converter convention: home attacks towards x = 105, away towards x = 0.
    """
    rows = [
        _action(0, HOME, (30, 34), (60, 34), ActionType.PASS),
        _action(1, HOME, (60, 34), (95, 34), ActionType.PASS),
        _action(2, HOME, (95, 34), (105, 34), ActionType.SHOT),
        _action(3, AWAY, (52.5, 34), (40, 20), ActionType.PASS),
        _action(4, AWAY, (40, 20), (15, 30), ActionType.PASS, Result.FAIL),
        _action(5, HOME, (90, 38), (75, 40), ActionType.CLEARANCE),
        _action(6, HOME, (30, 34), (60, 34), ActionType.PASS, Result.FAIL),
        _action(7, HOME, (60, 34), (95, 34), ActionType.DRIBBLE),
        _action(8, HOME, (95, 34), (105, 34), ActionType.SHOT),
        _action(9, AWAY, (52.5, 34), (60, 34), ActionType.PASS),
    ]
    return DataFrame[SPADLSchema](rows)


def test_hand_built_actions_pass_the_spadl_schema() -> None:
    SPADLSchema.validate(_ten_actions())


def test_spadl_schema_rejects_extra_columns() -> None:
    # Why our extension fields (possession, phase, planted moment) live in a separate frame.
    actions = _ten_actions().assign(possession_id=0)

    with pytest.raises(pandera.errors.SchemaError):
        SPADLSchema.validate(actions)


def test_play_left_to_right_flips_only_the_away_team() -> None:
    actions = _ten_actions()

    flipped = play_left_to_right(actions, home_team_id=HOME)

    home = actions.team_id == HOME
    pd.testing.assert_frame_equal(flipped[home], actions[home])
    away_pass = flipped.loc[3]
    assert (away_pass.start_x, away_pass.start_y) == (105 - 52.5, 68 - 34)
    assert (away_pass.end_x, away_pass.end_y) == (105 - 40, 68 - 20)


def test_expected_threat_fits_and_rates_successful_moves_only() -> None:
    actions = play_left_to_right(_ten_actions(), home_team_id=HOME)

    model = xthreat.ExpectedThreat().fit(actions)
    ratings = model.rate(actions)

    successful_moves = [0, 1, 3, 7, 9]
    assert not np.isnan(ratings[successful_moves]).any()
    assert np.isnan(np.delete(ratings, successful_moves)).all()
    # Half the passes from deep fail; reaching midfield, where every move led to a goal,
    # adds threat.
    assert ratings[0] > 0


def test_expected_threat_interpolation_is_unavailable() -> None:
    # socceraction wraps scipy.interpolate.interp2d, which SciPy 1.14 removed.
    actions = play_left_to_right(_ten_actions(), home_team_id=HOME)
    model = xthreat.ExpectedThreat().fit(actions)

    with pytest.raises(NotImplementedError):
        model.rate(actions, use_interpolation=True)
