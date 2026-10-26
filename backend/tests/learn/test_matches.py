from dataclasses import replace
from functools import cache

from btl.learn.learner import MATCHES_PER_SESSION, LearnerState
from btl.learn.matches import MatchState, catch_up, viewer_matches
from btl.learn.report import Goal
from btl.learn.session import Course, PreparedMatch, prepare_match
from btl.schema.ids import ActionId, TeamId
from btl.schema.scoreboard import goals, match_clock
from btl.tutor.templates import TemplateTutor
from tests.api.test_app import SEED, demo_attempts
from tests.fixtures.learning import threat_model


@cache
def course() -> Course:
    return Course(threat_model(), TemplateTutor())


@cache
def prepare(seed: int, number: int, club: TeamId | None) -> PreparedMatch:
    return prepare_match(course(), seed, number, club)


def test_a_new_viewer_s_matches_are_all_upcoming_with_no_score() -> None:
    matches = viewer_matches(course(), LearnerState("new", SEED), prepare)

    assert [m.match_number for m in matches] == list(range(1, MATCHES_PER_SESSION + 1))
    assert [m.matchday.number for m in matches] == [1, 2, 3]
    assert {m.state for m in matches} == {MatchState.UPCOMING}
    assert all(m.score is None and m.questions == 0 for m in matches)


def test_the_clubs_are_the_viewer_s_fixtures() -> None:
    matches = viewer_matches(course(), LearnerState("new", SEED), prepare)

    for m in matches:
        home, away, _ = course().fixture(SEED, m.match_number)
        assert (m.home_id, m.away_id) == (home.team_id, away.team_id)


def test_a_match_part_way_through_shows_the_score_at_the_last_answer_only() -> None:
    in_first = [a for a in demo_attempts() if a.match_number == 1]
    state = LearnerState("part", SEED, attempts=tuple(in_first[:2]))

    first, second, _ = viewer_matches(course(), state, prepare)

    assert first.state is MatchState.IN_PROGRESS
    assert first.questions == 2
    match = prepare(SEED, 1, None).match
    last = max(a.action_id for a in in_first[:2])
    scored = goals(match, ActionId(last))
    assert first.score is not None
    assert (first.score.home, first.score.away) == (
        scored[match.home_team_id],
        scored[match.away_team_id],
    )
    assert first.score.clock == match_clock(match.events[last])
    assert second.state is MatchState.UPCOMING and second.score is None


def test_finished_matches_show_the_full_time_score_and_questions_answered() -> None:
    state = replace(LearnerState("done", SEED, attempts=demo_attempts()), match_number=3)

    first, second, third = viewer_matches(course(), state, prepare)

    for finished in (first, second):
        match = prepare(SEED, finished.match_number, None).match
        scored = goals(match)
        assert finished.state is MatchState.FINISHED
        assert finished.score is not None and finished.score.clock is None
        assert (finished.score.home, finished.score.away) == (
            scored[match.home_team_id],
            scored[match.away_team_id],
        )
        assert finished.questions == sum(
            a.match_number == finished.match_number for a in demo_attempts()
        )
    assert third.state is MatchState.IN_PROGRESS


def test_an_upcoming_match_is_never_prepared() -> None:
    prepared: list[int] = []

    def counting(seed: int, number: int, club: TeamId | None) -> PreparedMatch:
        prepared.append(number)
        return prepare(seed, number, club)

    viewer_matches(course(), LearnerState("new", SEED, match_number=2), counting)

    assert prepared == [1]


def goal(action: int, period: int, seconds: float, home: bool) -> Goal:
    return Goal(ActionId(action), period, seconds, "00:00", home, "Someone", own_goal=False)


GOALS = (goal(10, 1, 600.0, True), goal(50, 1, 2000.0, False), goal(90, 2, 300.0, True))


def test_the_first_question_has_a_score_and_nothing_to_catch_up_on() -> None:
    caught = catch_up(GOALS, None, 1, 2100.0)

    assert (caught.home, caught.away, caught.goals) == (1, 1, None)


def test_a_later_question_catches_up_on_the_goals_since_the_last_answer() -> None:
    caught = catch_up(GOALS, ActionId(20), 2, 400.0)

    assert (caught.home, caught.away) == (2, 1)
    assert caught.goals == GOALS[1:]


def test_goals_after_the_question_are_never_told() -> None:
    caught = catch_up(GOALS, ActionId(20), 1, 2100.0)

    assert caught.goals == (GOALS[1],)
    assert (caught.home, caught.away) == (1, 1)
