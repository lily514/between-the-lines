import numpy as np
import pytest

from btl.league.league import Role, generate_league
from btl.learn.candidates import designed_lineups, play_designed_match
from btl.learn.team_sheet import SheetTeam, TeamSheet, sheet_stage, team_sheet
from btl.schema.frames import seen_by
from btl.schema.ids import ActionId, TeamId
from btl.schema.match import Match
from btl.sim.lineup import Lineup
from tests.fixtures.learning import designed

LEAGUE = generate_league(np.random.default_rng(0))
HOME, AWAY = LEAGUE.clubs[:2]


def sheet(match: Match, stage: int, club: TeamId | None = None) -> TeamSheet:
    return team_sheet(match, designed_lineups(HOME, AWAY), 1, stage, club)


@pytest.mark.parametrize(
    ("mastery", "stage"),
    [([], 1), ([0.35, 0.15], 1), ([0.15, 0.45], 2), ([0.71, 0.1, 0.35], 3)],
)
def test_the_stage_is_the_level_of_the_best_concept(mastery: list[float], stage: int) -> None:
    assert sheet_stage(mastery) == stage


@pytest.mark.parametrize("seed", range(40))
def test_the_sheet_lists_exactly_the_players_in_the_match(seed: int) -> None:
    match = designed(seed)
    assert match.positions is not None

    on_sheet = [p.player_id for team in sheet(match, 1).teams for p in team.players]

    tracked = [slot.player_id for slot in match.positions.slots]
    assert sorted(on_sheet) == sorted(tracked) and len(set(on_sheet)) == 22
    assert {event.player_id for event in match.events} <= set(on_sheet)


def test_the_designed_lineups_are_the_ones_the_match_tracks_for_any_clubs() -> None:
    for home, away in [LEAGUE.clubs[4:6], LEAGUE.clubs[9:7:-1]]:
        match = play_designed_match(home, away, 3)
        assert match.positions is not None

        lineups: tuple[Lineup, Lineup] = designed_lineups(home, away)

        expected = [p.player_id for lineup in lineups for p in lineup.players]
        assert [slot.player_id for slot in match.positions.slots] == expected


def test_a_beginner_sees_names_and_positions_but_no_shape() -> None:
    first = sheet(designed(0), 1).teams[0]

    assert first.formation is None
    assert all(player.at_kickoff is None for player in first.players)
    assert [p.role for p in first.players][:2] == [Role.GOALKEEPER, Role.DEFENDER]


def test_each_line_is_listed_left_to_right_as_the_team_faces() -> None:
    defenders = [p for p in sheet(designed(0), 1).teams[0].players if p.role is Role.DEFENDER]

    assert [p.position.short for p in defenders] == ["LB", "CB", "CB", "RB"]


def test_the_viewers_team_comes_first_and_is_marked_as_theirs() -> None:
    plain = sheet(designed(0), 1)
    supporting_away = sheet(designed(0), 1, AWAY.team_id)
    elsewhere = sheet(designed(0), 1, LEAGUE.clubs[5].team_id)

    assert [team.name for team in plain.teams] == [HOME.name, AWAY.name]
    assert [team.name for team in supporting_away.teams] == [AWAY.name, HOME.name]
    assert [team.yours for team in supporting_away.teams] == [True, False]
    assert [team.home for team in supporting_away.teams] == [False, True]
    assert elsewhere == plain


def test_stage_two_shows_formations_and_kickoff_spots_seen_by_the_first_team() -> None:
    match = designed(0)

    staged = sheet(match, 2, AWAY.team_id)

    kickoff = seen_by(match, AWAY.team_id).snapshot(ActionId(0))
    assert kickoff is not None
    spots = {p.player_id: (p.x, p.y) for p in kickoff.positions}
    team: SheetTeam
    for team in staged.teams:
        assert team.formation == "4-4-2"
        assert all(player.at_kickoff == spots[player.player_id] for player in team.players)
    # The first team attacks towards x = 105, so its keeper is near x = 0.
    keeper = staged.teams[0].players[0]
    assert keeper.at_kickoff is not None and keeper.at_kickoff[0] < 20


def test_an_unknown_stage_is_refused() -> None:
    with pytest.raises(ValueError, match="stage must be one of"):
        sheet(designed(0), 4)
