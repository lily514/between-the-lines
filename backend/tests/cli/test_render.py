from functools import cache

import numpy as np
import pytest
from rich.console import Console

from btl.cli.render import (
    PITCH_LEGEND,
    events_table,
    goals,
    match_clock,
    pitch_picture,
    scoreline,
    tags_table,
    threat_grid,
    threat_text,
)
from btl.concepts.base import ConceptTag
from btl.league.league import League, generate_league
from btl.schema.ids import ActionId
from btl.schema.match import Match
from btl.schema.vocab import ActionType, ConceptId, Result
from btl.sim.engine import simulate_match
from btl.value.xt import FitInfo, ThreatModel
from tests.fixtures.concepts import BACK_LINE, MIDFIELD_LINE, one_pass
from tests.fixtures.matches import (
    AWAY,
    AWAY_MIDFIELDER,
    GAME,
    HOME,
    HOME_MIDFIELDER,
    make_event,
)


@cache
def league() -> League:
    return generate_league(np.random.default_rng(0))


@cache
def simulated() -> Match:
    home, away = league().clubs[:2]
    return simulate_match(home, away, 0)


def text_of(renderable: object) -> str:
    console = Console(width=200, record=True)
    console.print(renderable)
    return console.export_text()


def test_the_clock_carries_on_from_45_minutes_in_the_second_half() -> None:
    first_half = make_event(0, HOME, HOME_MIDFIELDER, (50, 34), (60, 34))
    second_half = make_event(1, HOME, HOME_MIDFIELDER, (50, 34), (60, 34), period_id=2)

    assert match_clock(first_half) == "00:00"
    assert match_clock(make_event(150, HOME, HOME_MIDFIELDER, (50, 34), (60, 34))) == "10:00"
    assert match_clock(second_half) == "45:04"


def test_goals_count_scored_shots_and_own_goals_for_the_other_team() -> None:
    events = (
        make_event(0, HOME, HOME_MIDFIELDER, (90, 34), (105, 34), ActionType.SHOT),
        make_event(1, AWAY, AWAY_MIDFIELDER, (90, 34), (105, 34), ActionType.SHOT, Result.FAIL),
        make_event(2, AWAY, AWAY_MIDFIELDER, (10, 34), (0, 34), ActionType.PASS, Result.OWNGOAL),
    )

    assert goals(Match(GAME, HOME, AWAY, events)) == {HOME: 2, AWAY: 0}


def test_the_scoreline_names_both_clubs() -> None:
    match = simulated()
    score = goals(match)

    text = text_of(scoreline(match, league()))

    home, away = league().club(match.home_team_id), league().club(match.away_team_id)
    assert text.strip() == (
        f"{home.name} {score[match.home_team_id]}-{score[match.away_team_id]} {away.name}"
    )


def test_the_events_table_shows_the_requested_slice_with_names() -> None:
    match = simulated()
    event = match.events[100]
    player = league().player(event.player_id)

    table = events_table(match, league(), start=100, count=5)

    assert table.row_count == 5
    first_row = text_of(table).splitlines()[3]
    assert first_row.split()[1] == "100"
    assert f"#{player.shirt_number} {player.full_name}" in first_row
    assert league().club(event.team_id).name in first_row


def test_threat_shows_its_sign_and_hides_rounding_noise() -> None:
    assert threat_text(0.0123).plain == "+0.012"
    assert threat_text(-0.004).plain == "-0.004"
    assert threat_text(-0.0001).plain == "0.000"
    assert threat_text(None).plain == ""


def test_the_events_table_has_a_threat_column_only_when_given_values() -> None:
    match = simulated()
    threat = [0.0123 if event.action_id == 1 else None for event in match.events]

    without = text_of(events_table(match, league(), 0, 3))
    with_threat = text_of(events_table(match, league(), 0, 3, threat))

    assert "threat" not in without
    assert "threat" in with_threat
    assert "+0.012" in with_threat


def test_the_threat_grid_shows_every_cell_in_percent() -> None:
    model = ThreatModel(
        grid=tuple(tuple(0.001 * column for column in range(16)) for _ in range(12)),
        fitted_on=FitInfo(matches=1, seed=0, league_seed=0, actions=1),
    )

    lines = text_of(threat_grid(model)).splitlines()

    assert len(lines) == 12
    assert lines[0].split() == [f"{column / 10:.1f}" for column in range(16)]
    assert all(len(line) <= 80 for line in lines)


def test_the_tags_table_shows_each_tag_with_its_action_and_evidence() -> None:
    match = simulated()
    event = match.events[5]
    tag = ConceptTag(
        ConceptId.SWITCH_OF_PLAY,
        match.game_id,
        event.action_id,
        (event.action_id, event.action_id),
        0.25,
        {"across (m)": 41.2},
    )

    text = text_of(tags_table(match, league(), [tag]))

    assert "switch of play" in text
    assert "across (m) 41.2" in text
    assert "0.25" in text
    assert match_clock(event) in text


def test_the_pitch_shows_the_players_and_the_pass_attacking_left_to_right() -> None:
    match = one_pass((40, 34), (60, 34), MIDFIELD_LINE + BACK_LINE)

    lines = text_of(pitch_picture(match, ActionId(0))).splitlines()

    assert len(lines) == 20
    assert lines[0] == lines[-2] == "+" + "-" * 53 + "+"
    assert lines[-1] == PITCH_LEGEND
    drawn = "".join(lines[:-1])
    assert [drawn.count(mark) for mark in "@*xKoG"] == [1, 1, 8, 1, 0, 0]
    on_the_ball = lines[9]
    assert on_the_ball.index("@") < on_the_ball.index("·") < on_the_ball.index("*")
    assert on_the_ball.endswith("K|")


def test_the_pitch_needs_a_snapshot() -> None:
    match = one_pass((40, 34), (60, 34), (), with_snapshot=False)

    with pytest.raises(ValueError, match="no player positions"):
        pitch_picture(match, ActionId(0))
