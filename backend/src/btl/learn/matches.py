"""A viewer's matches as a list: what's coming, the one they're part-way through, and the finished.

This is what the Matches screen shows. A match's state comes only from the viewer's record:
the match being watched is in progress once they have answered something in it, and upcoming
before that. A match tells only what the viewer has already seen: nothing about an upcoming
one beyond its clubs and date, and for one in progress, the score at the last moment they
answered about. As each question comes, `catch_up` gives the score and the goals scored since
the viewer's last answer.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from enum import StrEnum

from btl.league.calendar import Matchday, matchday
from btl.learn.candidates import Candidate
from btl.learn.evidence import Delivered
from btl.learn.learner import MATCHES_PER_SESSION, LearnerState
from btl.learn.report import Goal
from btl.learn.session import Course, PreparedMatch
from btl.schema.ids import ActionId, TeamId
from btl.schema.scoreboard import goals, match_clock
from btl.schema.vocab import ConceptId


class MatchState(StrEnum):
    """Where a match stands for the viewer."""

    UPCOMING = "upcoming"
    IN_PROGRESS = "in_progress"
    FINISHED = "finished"


@dataclass(frozen=True, slots=True)
class Score:
    """Goals for each side, and the match clock they stand at (None at full time)."""

    home: int
    away: int
    clock: str | None


@dataclass(frozen=True, slots=True)
class ViewerMatch:
    """One of the viewer's matches.

    ``score`` is None for an upcoming match. ``questions`` counts the questions answered in it.
    """

    match_number: int
    matchday: Matchday
    home_id: TeamId
    away_id: TeamId
    state: MatchState
    score: Score | None
    questions: int


def viewer_matches(
    course: Course,
    state: LearnerState,
    prepare: Callable[[int, int, TeamId | None], PreparedMatch],
) -> tuple[ViewerMatch, ...]:
    """Every one of the viewer's matches, in order.

    Args:
        course: What every viewer shares.
        state: The viewer's record.
        prepare: Gives the prepared match for a session seed, match number and club; only
            matches the viewer has started are prepared.
    """
    return tuple(
        _viewer_match(course, state, number, prepare)
        for number in range(1, MATCHES_PER_SESSION + 1)
    )


def _viewer_match(
    course: Course,
    state: LearnerState,
    number: int,
    prepare: Callable[[int, int, TeamId | None], PreparedMatch],
) -> ViewerMatch:
    home, away, _ = course.fixture(state.seed, number, state.club)
    answered = [a for a in state.attempts if a.match_number == number]
    if number < state.match_number:
        match_state = MatchState.FINISHED
    elif number == state.match_number and answered:
        match_state = MatchState.IN_PROGRESS
    else:
        match_state = MatchState.UPCOMING
    score = None
    if match_state is not MatchState.UPCOMING:
        match = prepare(state.seed, number, state.club).match
        if match_state is MatchState.FINISHED:
            scored, at = goals(match), None
        else:
            last = max(a.action_id for a in answered)
            scored, at = goals(match, ActionId(last)), match_clock(match.events[last])
        score = Score(scored[match.home_team_id], scored[match.away_team_id], at)
    return ViewerMatch(
        match_number=number,
        matchday=matchday(number),
        home_id=home.team_id,
        away_id=away.team_id,
        state=match_state,
        score=score,
        questions=len(answered),
    )


@dataclass(frozen=True, slots=True)
class CatchUp:
    """The score when a question comes, and the goals since the viewer's last answer.

    ``goals`` is None for the first question of a match: there was no answer to catch up from.
    """

    home: int
    away: int
    goals: tuple[Goal, ...] | None


@dataclass(frozen=True, slots=True)
class ScoreTime:
    """When a question's score stands, and the action it counts goals up to, if not all so far."""

    period_id: int
    seconds: float
    up_to: ActionId | None = None


def score_as_of(candidate: Candidate, delivered: Delivered) -> ScoreTime:
    """When a question's score is taken: as it is asked, or just before a shot.

    A shot's result is its answer, so its question shows the score as it stood before the shot,
    whatever has happened since.
    """
    if candidate.tag.concept is ConceptId.SHOT:
        return ScoreTime(candidate.period_id, candidate.time_seconds, candidate.tag.action_id)
    return ScoreTime(delivered.period_id, delivered.time_seconds)


def catch_up(
    match_goals: Sequence[Goal],
    last_answered: ActionId | None,
    period_id: int,
    seconds: float,
    up_to: ActionId | None = None,
) -> CatchUp:
    """What the viewer needs to know as a question comes: the score, and goals they missed.

    Args:
        match_goals: Every goal in the match, from `btl.learn.report.match_goals`.
        last_answered: The moment of the viewer's last answer in this match, if any.
        period_id: When the question is asked: its period.
        seconds: And its seconds into that period.
        up_to: Count only goals from actions before this one, when the question's own moment
            must stay out of the score.
    """
    so_far = [
        g
        for g in match_goals
        if (g.period_id, g.seconds) <= (period_id, seconds)
        and (up_to is None or g.action_id < up_to)
    ]
    missed = None
    if last_answered is not None:
        missed = tuple(g for g in so_far if g.action_id > last_answered)
    return CatchUp(
        home=sum(g.home for g in so_far),
        away=sum(not g.home for g in so_far),
        goals=missed,
    )
