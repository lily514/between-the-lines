import numpy as np
from rich.console import Console

from btl.cli.viewer import show_team_sheet
from btl.league.league import generate_league
from btl.learn.candidates import designed_lineups
from btl.learn.player_stats import watched_numbers
from btl.learn.team_sheet import team_sheet
from tests.fixtures.learning import context, designed

HOME, AWAY = generate_league(np.random.default_rng(0)).clubs[:2]


def shown(stage: int, watched: int) -> str:
    lineups = designed_lineups(HOME, AWAY)
    home_eleven = [p.player_id for p in lineups[0].players]
    numbers = watched_numbers([(context(designed(1)), home_eleven)] * watched)
    console = Console(record=True, width=160)
    show_team_sheet(console, team_sheet(designed(0), lineups, 2, stage, HOME.team_id, numbers))
    return console.export_text()


def test_a_beginner_sees_names_and_positions_only() -> None:
    text = shown(1, watched=1)

    assert "your team" in text and "Left back" in text
    assert "LB" not in text and "Passes" not in text


def test_stage_three_shows_numbers_and_marks_players_not_seen_yet() -> None:
    text = shown(3, watched=1)

    assert "4-4-2" in text and "LB" in text
    assert "Passes" in text and "Threat added" in text
    # The watched match's starters given here are the home eleven only.
    assert text.count("first time you've seen them") == 11


def test_stage_three_says_when_no_match_of_a_club_has_been_watched() -> None:
    text = shown(3, watched=0)

    assert f"You haven't watched {HOME.name} yet" in text
    assert f"You haven't watched {AWAY.name} yet" in text
    assert "Passes" not in text
