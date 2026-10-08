from functools import cache

import numpy as np
import pytest
from rich.console import Console

from btl.cli.render import (
    PITCH_LEGEND,
    REPLAY_LEGEND,
    counted,
    events_table,
    goals,
    match_clock,
    pitch_picture,
    replay_picture,
    scoreline,
    summary_table,
    tags_table,
    threat_grid,
    threat_text,
)
from btl.concepts.base import ConceptTag
from btl.league.league import League, generate_league
from btl.replay import frame_at, lead_up_frames
from btl.schema.ids import ActionId
from btl.schema.match import Match
from btl.schema.moment import PlantedMoment
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
    six_event_match,
)

PLANTED_PASS = PlantedMoment(ConceptId.LINE_BREAKING_PASS, 1, ActionId(1), ActionId(2))


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


def test_counts_are_plural_unless_there_is_exactly_one() -> None:
    assert counted(1, "tag") == "1 tag"
    assert counted(0, "tag") == "0 tags"
    assert counted(1_203, "tag") == "1,203 tags"
    assert counted(2, "match", "matches") == "2 matches"
    assert counted(1, "match", "matches") == "1 match"


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

    table = events_table(match, league(), match.events[100:105])

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

    without = text_of(events_table(match, league(), match.events[:3]))
    with_threat = text_of(events_table(match, league(), match.events[:3], threat))

    assert "threat" not in without
    assert "threat" in with_threat
    assert "+0.012" in with_threat


def tag_at(match: Match, concept: ConceptId, action_id: int) -> ConceptTag:
    action = ActionId(action_id)
    return ConceptTag(concept, match.game_id, action, (action, action), None, {})


def test_the_events_table_names_the_concepts_at_each_event_and_marks_planted_ones() -> None:
    events = tuple(make_event(i, HOME, HOME_MIDFIELDER, (50, 34), (60, 34)) for i in range(3))
    moment = PlantedMoment(ConceptId.LINE_BREAKING_PASS, 1, ActionId(1), ActionId(2))
    match = Match(GAME, HOME, AWAY, events, planted=(moment,))
    tags = [
        tag_at(match, ConceptId.SWITCH_OF_PLAY, 1),
        tag_at(match, ConceptId.SWITCH_OF_PLAY, 2),
        tag_at(match, ConceptId.LINE_BREAKING_PASS, 2),
    ]

    rows = text_of(events_table(match, league(), match.events, tags=tags)).splitlines()[3:6]

    assert rows[0].split("│")[-2].strip() == ""
    assert "switch of play" in rows[1]
    assert "switch of play, line breaking pass (planted)" in rows[2]


def test_the_summary_counts_each_teams_goals_passes_threat_and_concepts() -> None:
    events = (
        make_event(0, HOME, HOME_MIDFIELDER, (50, 34), (60, 34)),
        make_event(1, HOME, HOME_MIDFIELDER, (60, 34), (70, 34), result=Result.FAIL),
        make_event(2, AWAY, AWAY_MIDFIELDER, (35, 34), (45, 34)),
        make_event(3, AWAY, AWAY_MIDFIELDER, (90, 34), (105, 34), ActionType.SHOT),
    )
    match = Match(GAME, HOME, AWAY, events)
    tags = [tag_at(match, ConceptId.COUNTER_PRESS, 2)]

    text = text_of(summary_table(match, league(), tags, [0.01, -0.02, 0.03, None]))

    rows = {line.split("│")[1].strip(): line.split("│")[2:4] for line in text.splitlines()[3:-1]}
    cells = {name: [cell.strip() for cell in values] for name, values in rows.items()}
    assert cells["goals"] == ["0", "1"]
    assert cells["shots"] == ["0", "1"]
    assert cells["passes (completed)"] == ["2 (50%)", "1 (100%)"]
    assert cells["possessions"] == ["1", "1"]
    assert cells["threat added"] == ["-0.01", "+0.03"]
    assert cells["counter press"] == ["0", "1"]
    assert cells["switch of play"] == ["0", "0"]


def test_the_summary_leaves_out_threat_without_a_model() -> None:
    match = simulated()

    assert "threat added" not in text_of(summary_table(match, league(), []))


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


def drawn_at(lines: list[str], x: float, y: float) -> str:
    """The character drawn for a point on the pitch, given a replay picture's lines."""
    column = min(int(x / 105 * 53), 52)
    row = min(int((68 - y) / 68 * 17), 16)
    return lines[2 + row][1 + column]


def test_a_replay_frame_trails_the_ball_from_where_the_action_started() -> None:
    match = six_event_match()  # pass #0 from (40, 34) to (60, 30), with a 3 s flight
    one_second_in = lead_up_frames(match, PLANTED_PASS, seconds=8, fps=1)[1]

    lines = text_of(replay_picture(match, one_second_in, HOME)).splitlines()

    assert lines[0] == "00:01"
    assert lines[-1] == REPLAY_LEGEND
    assert drawn_at(lines, *one_second_in.ball) == "@"
    assert drawn_at(lines, 44, 33.2) == "·"
    assert drawn_at(lines, 56, 31) == " "
    assert "*" not in "".join(lines[:-1])


def test_the_question_frame_gives_no_path_away() -> None:
    match = six_event_match()

    lines = text_of(replay_picture(match, frame_at(match, ActionId(2)), HOME)).splitlines()

    drawn = "".join(lines[1:-1])
    assert "·" not in drawn
    assert "*" not in drawn
    assert drawn_at(lines, 70, 30) == "@"


def test_a_replay_frame_can_show_the_whole_path_to_its_target() -> None:
    match = six_event_match()

    picture = replay_picture(match, frame_at(match, ActionId(0)), HOME, show_target=True)

    lines = text_of(picture).splitlines()
    assert drawn_at(lines, 60, 30) == "*"
    assert drawn_at(lines, 50, 32) == "·"
    assert drawn_at(lines, 40, 34) == "@"


def test_replay_marks_stay_with_the_watching_team_when_the_ball_changes_hands() -> None:
    match = six_event_match()
    away_on_the_ball = frame_at(match, ActionId(3))

    drawn = "".join(text_of(replay_picture(match, away_on_the_ball, HOME)).splitlines()[1:-1])

    assert "G" in drawn
    assert "K" in drawn
