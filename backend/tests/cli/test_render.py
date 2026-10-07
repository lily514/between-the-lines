from functools import cache

import numpy as np
from rich.console import Console

from btl.cli.render import events_table, goals, match_clock, scoreline
from btl.league.league import League, generate_league
from btl.schema.match import Match
from btl.schema.vocab import ActionType, Result
from btl.sim.engine import simulate_match
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
