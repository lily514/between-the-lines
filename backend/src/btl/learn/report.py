"""The scouting report at halftime and full time: the score, the radar, and how the viewer did.

A report covers one of the viewer's matches up to a break. At halftime it covers the first
half only: goals scored in it, and the questions asked in it or at the break. At full time it
covers the whole match. It never looks past its break, so a halftime report can't hint at the
second half.

- **Radar:** one value per strand, the mean mastery of the strand's concepts asked about now,
  at kick-off and at the break. A strand with no such concept has no value ("Not yet"), never
  zero.
- **Concepts:** each concept asked about now, before and after, with its level word.
- **Scout's note:** a sentence or two in words, from the levels; it never states a number.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from statistics import fmean

from btl.learn.bkt import BktState
from btl.learn.concept_map import ConceptKey
from btl.learn.curriculum import strand_name
from btl.learn.learner import Attempt, LearnerState
from btl.learn.levels import level_word
from btl.learn.session import Course, PreparedMatch
from btl.schema.ids import TeamId
from btl.schema.match import Match
from btl.schema.possession import SHOTS
from btl.schema.scoreboard import match_clock
from btl.schema.vocab import Result


class Break(StrEnum):
    """Which break a report is for."""

    HALFTIME = "halftime"
    FULL_TIME = "full_time"


@dataclass(frozen=True, slots=True)
class StrandValue:
    """A strand on the radar: mastery at kick-off and now, or None if nothing in it is asked."""

    key: str
    name: str
    concepts: int
    kickoff: float | None
    now: float | None


@dataclass(frozen=True, slots=True)
class ConceptMove:
    """One concept asked about now: mastery and level word at kick-off and now."""

    key: ConceptKey
    name: str
    strand: str
    before: float
    after: float
    level_before: str
    level: str
    mastered: bool


@dataclass(frozen=True, slots=True)
class Goal:
    """A goal: when, for which side, and who scored (the player whose shot it was)."""

    clock: str
    home: bool
    scorer: str
    own_goal: bool


@dataclass(frozen=True, slots=True)
class AnswerLine:
    """A question answered in the report's span: the moment's clock, the concept, right or not."""

    clock: str
    concept: str
    correct: bool


@dataclass(frozen=True, slots=True)
class Report:
    """A scouting report for one of the viewer's matches at one break."""

    match_number: int
    at: Break
    home_id: TeamId
    away_id: TeamId
    home_goals: int
    away_goals: int
    goals: tuple[Goal, ...]
    strands: tuple[StrandValue, ...]
    concepts: tuple[ConceptMove, ...]
    answers: tuple[AnswerLine, ...]
    note: str


def report(
    course: Course, state: LearnerState, prepared: PreparedMatch, number: int, at: Break
) -> Report:
    """The report for match ``number`` at a break.

    The caller checks the viewer has reached that break: this covers whatever the record holds.

    Args:
        course: What every viewer shares.
        state: The viewer's record.
        prepared: The match, as prepared for this viewer.
        number: Which of the viewer's matches.
        at: Halftime or full time.
    """
    match = prepared.match
    in_span = [a for a in state.attempts if a.match_number == number and _in_span(a, match, at)]
    earlier = [a for a in state.attempts if a.match_number < number]
    model = course.model
    kickoff = LearnerState(state.viewer_id, state.seed, attempts=tuple(earlier)).model_state(
        model, course.active
    )
    now = LearnerState(state.viewer_id, state.seed, attempts=(*earlier, *in_span)).model_state(
        model, course.active
    )
    concepts = tuple(_move(course, kickoff, now, key) for key in course.active)
    goals = _goals(course, match, at)
    return Report(
        match_number=number,
        at=at,
        home_id=match.home_team_id,
        away_id=match.away_team_id,
        home_goals=sum(goal.home for goal in goals),
        away_goals=sum(not goal.home for goal in goals),
        goals=goals,
        strands=_strands(course, concepts),
        concepts=concepts,
        answers=tuple(
            AnswerLine(
                clock=match_clock(match.events[a.action_id]),
                concept=course.concept_map.concept(a.concept).name,
                correct=a.correct,
            )
            for a in in_span
        ),
        note=scout_note(concepts, len(in_span), at),
    )


def scout_note(concepts: Sequence[ConceptMove], answered: int, at: Break) -> str:
    """The scout's note: what moved, and what to work on next, in words only."""
    span = "this half" if at is Break.HALFTIME else "this match"
    if answered == 0:
        opening = f"No questions {span}, so nothing new to report."
    else:
        moved = [c for c in concepts if c.after > c.before]
        best = max(moved, key=lambda c: c.after - c.before, default=None)
        if best is None:
            opening = f"A tough {span}: every read is something to build on."
        else:
            was, now = best.level_before.lower(), best.level.lower()
            if was == now:
                opening = f"{best.name} moved forward {span}, still {now}."
            else:
                opening = f"{best.name} went from {was} to {now} {span}."
    learning = [c for c in concepts if not c.mastered]
    if not learning:
        return f"{opening} Everything asked about now is mastered."
    focus = min(learning, key=lambda c: c.after)
    return f"{opening} Next to work on: {focus.name}, {focus.level.lower()}."


def _in_span(attempt: Attempt, match: Match, at: Break) -> bool:
    if at is Break.FULL_TIME:
        return True
    asked_in = attempt.asked_in
    if asked_in is None:
        asked_in = match.events[attempt.action_id].period_id
    return asked_in == 1


def _move(course: Course, kickoff: BktState, now: BktState, key: ConceptKey) -> ConceptMove:
    model = course.model
    concept = course.concept_map.concept(key)
    before, after = model.mastery(kickoff, key), model.mastery(now, key)
    return ConceptMove(
        key=key,
        name=concept.name,
        strand=concept.strand,
        before=before,
        after=after,
        level_before=level_word(before, model.thresholds),
        level=level_word(after, model.thresholds),
        mastered=after >= model.thresholds.mastery,
    )


def _strands(course: Course, concepts: Sequence[ConceptMove]) -> tuple[StrandValue, ...]:
    values: list[StrandValue] = []
    for key in course.concept_map.strands:
        inside = [c for c in concepts if c.strand == key]
        values.append(
            StrandValue(
                key=key,
                name=strand_name(key),
                concepts=len(inside),
                kickoff=fmean(c.before for c in inside) if inside else None,
                now=fmean(c.after for c in inside) if inside else None,
            )
        )
    return tuple(values)


def _goals(course: Course, match: Match, at: Break) -> tuple[Goal, ...]:
    home = match.home_team_id
    goals: list[Goal] = []
    for event in match.events:
        if at is Break.HALFTIME and event.period_id > 1:
            break
        scored = event.action_type in SHOTS and event.result is Result.SUCCESS
        own_goal = event.result is Result.OWNGOAL
        if not (scored or own_goal):
            continue
        for_home = (event.team_id == home) != own_goal
        scorer = course.league.player(event.player_id).full_name
        goals.append(Goal(match_clock(event), for_home, scorer, own_goal))
    return tuple(goals)
