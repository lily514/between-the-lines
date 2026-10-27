import re
from dataclasses import replace
from functools import cache

import pytest

from btl.learn.concept_map import ConceptKey
from btl.learn.learner import LearnerState
from btl.learn.report import Break, ConceptMove, report, scout_note, strand_values
from btl.learn.session import Course, PreparedMatch, prepare_match
from btl.schema.scoreboard import goals
from btl.tutor.templates import TemplateTutor
from tests.api.test_app import SEED, demo_attempts
from tests.fixtures.learning import threat_model


@cache
def course() -> Course:
    return Course(threat_model(), TemplateTutor())


@cache
def prepared(number: int) -> PreparedMatch:
    return prepare_match(course(), SEED, number)


def finished_state() -> LearnerState:
    return replace(LearnerState("demo", SEED, attempts=demo_attempts()), match_number=4)


@pytest.mark.parametrize("number", [1, 2, 3])
def test_the_full_time_report_has_the_match_s_score_and_every_answer(number: int) -> None:
    made = report(course(), finished_state(), prepared(number), number, Break.FULL_TIME)

    match = prepared(number).match
    scored = goals(match)
    assert (made.home_goals, made.away_goals) == (
        scored[match.home_team_id],
        scored[match.away_team_id],
    )
    assert len(made.goals) == made.home_goals + made.away_goals
    assert len(made.answers) == sum(a.match_number == number for a in demo_attempts())


@pytest.mark.parametrize("number", [1, 2, 3])
def test_a_halftime_report_holds_nothing_from_the_second_half(number: int) -> None:
    state = finished_state()
    match = prepared(number).match

    half = report(course(), state, prepared(number), number, Break.HALFTIME)

    second_half = next(e.action_id for e in match.events if e.period_id == 2)
    by_the_break = goals(match, second_half)
    assert (half.home_goals, half.away_goals) == (
        by_the_break[match.home_team_id],
        by_the_break[match.away_team_id],
    )
    in_match = [a for a in state.attempts if a.match_number == number]
    asked_first = [a for a in in_match if a.asked_in == 1]
    assert len(half.answers) == len(asked_first)
    # Only answers asked by the break move the radar.
    without_second = replace(
        state,
        attempts=tuple(a for a in state.attempts if a.asked_in != 2 or a.match_number != number),
    )
    again = report(course(), without_second, prepared(number), number, Break.HALFTIME)
    assert again == half


def test_a_report_s_kick_off_values_are_before_the_match() -> None:
    made = report(course(), finished_state(), prepared(1), 1, Break.FULL_TIME)
    new = report(course(), LearnerState("new", SEED), prepared(1), 1, Break.FULL_TIME)

    assert [c.before for c in made.concepts] == [c.after for c in new.concepts]


def test_the_radar_averages_each_strand_s_concepts_asked_about_now() -> None:
    made = report(course(), finished_state(), prepared(1), 1, Break.FULL_TIME)

    strands = {s.key: s for s in made.strands}
    assert list(strands) == ["possession", "pressure", "chances", "game_flow"]
    assert [strands[k].concepts for k in strands] == [1, 2, 1, 3]
    flow = [c.after for c in made.concepts if c.strand == "game_flow"]
    assert strands["game_flow"].now == pytest.approx(sum(flow) / len(flow))


def test_a_strand_with_nothing_asked_about_has_no_value_rather_than_zero() -> None:
    made = report(course(), finished_state(), prepared(1), 1, Break.FULL_TIME)
    only_flow = [c for c in made.concepts if c.strand == "game_flow"]

    strands = {s.key: s for s in strand_values(course(), only_flow)}

    assert strands["chances"].concepts == 0
    assert strands["chances"].kickoff is None and strands["chances"].now is None
    assert strands["game_flow"].now is not None


def test_an_attempt_from_before_the_period_was_kept_counts_by_its_moment() -> None:
    state = finished_state()
    unknown = replace(state, attempts=tuple(replace(a, asked_in=None) for a in state.attempts))

    half = report(course(), unknown, prepared(1), 1, Break.HALFTIME)

    match = prepared(1).match
    first = [
        a
        for a in state.attempts
        if a.match_number == 1 and match.events[a.action_id].period_id == 1
    ]
    assert len(half.answers) == len(first)


def move(name: str, before: float, after: float, level_before: str, level: str) -> ConceptMove:
    return ConceptMove(
        ConceptKey(name.lower()),
        name,
        "game_flow",
        before,
        after,
        level_before,
        level,
        after >= 0.95,
    )


def test_the_scout_s_note_names_the_biggest_mover_and_the_next_focus_in_words() -> None:
    concepts = [
        move("Restarts", 0.35, 0.62, "Getting there", "Solid"),
        move("Offside", 0.35, 0.40, "Getting there", "Solid"),
        move("Fouls and cards", 0.35, 0.35, "Getting there", "Getting there"),
    ]

    note = scout_note(concepts, 2, Break.HALFTIME)

    assert note == (
        "Restarts went from getting there to solid this half. "
        "Next to work on: Fouls and cards, getting there."
    )
    assert not re.search(r"\d", note)


def test_with_no_questions_the_note_says_so() -> None:
    concepts = [move("Restarts", 0.35, 0.35, "Getting there", "Getting there")]

    assert scout_note(concepts, 0, Break.FULL_TIME).startswith("No questions this match")
