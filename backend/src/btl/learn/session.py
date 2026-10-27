"""A viewing session: one viewer watching their three matches, answering as they go.

This joins every piece of the learning loop. For each match it simulates the match (the same
for every viewer), finds candidate moments and the phases of play, and lets the live selector
walk through it. Each question the selector asks becomes an evidence pack, worded by the
Tutor, answered by the viewer, graded, recorded, and explained.

The viewer is anything with the `Viewer` methods: the terminal, a scripted demo viewer, later
a web page. The record is saved after every answer, so a session can stop at any point and
carry on: replaying a match with the answers already given leads the selector to exactly the
same place.
"""

import zlib
from collections.abc import Callable, Collection, Sequence
from dataclasses import dataclass, field, replace
from typing import Protocol

import numpy as np

from btl.concepts.base import MatchContext, match_context
from btl.concepts.phase import PhaseTimeline, phase_timeline
from btl.league.league import Club, League, generate_league, season_fixtures
from btl.learn.bkt import BktModel, BktState
from btl.learn.candidates import (
    Candidate,
    designed_lineups,
    find_candidates,
    play_designed_match,
)
from btl.learn.concept_map import ConceptKey, ConceptMap, load_concept_map
from btl.learn.evidence import Delivered, EvidencePack, QuestionView, build_pack, question_view
from btl.learn.grader import Answer, ChoiceAnswer, ChoiceGrader, Grade
from btl.learn.learner import Attempt, LearnerState
from btl.learn.pace import Pace
from btl.learn.questions import active_concepts, build_question
from btl.learn.selector import Prompt, run_match
from btl.schema.ids import TeamId
from btl.schema.match import Match
from btl.sim.lineup import Lineup
from btl.store.base import LearnerStore, Stored
from btl.tutor.base import History, Tutor
from btl.tutor.slots import feedback_values, fill, question_values
from btl.value.xt import ThreatModel, rate_match

LEAGUE_SEED = 0


@dataclass(frozen=True, slots=True)
class Asked:
    """A question as the viewer meets it: the pack, its view, and the worded question.

    ``prompt`` is the selector's decision: the moment, and when and in what phase it is asked.
    ``previous`` is when the match's previous question was asked, where the viewer left off;
    None for its first.
    """

    pack: EvidencePack
    view: QuestionView
    text: str
    match: Match
    prompt: Prompt
    previous: Delivered | None = None


@dataclass(frozen=True, slots=True)
class Told:
    """What the viewer is told after answering."""

    pack: EvidencePack
    grade: Grade
    verdict: str
    explanation: str
    takeaway: str
    source: str
    update: str
    mastery: dict[str, float]
    misconception: str | None = None


@dataclass(frozen=True, slots=True)
class MatchStart:
    """A match about to be watched."""

    match_number: int
    home: str
    away: str
    mastery: dict[str, float]


class Viewer(Protocol):
    """Whoever watches: shown each match, asked each question, told each answer."""

    def begin(self, start: MatchStart) -> None:
        """A match is starting."""
        ...

    def ask(self, asked: Asked) -> Answer:
        """Answer a question."""
        ...

    def tell(self, told: Told) -> None:
        """Hear the feedback on the last answer."""
        ...

    def end(self, mastery: dict[str, float], asked: int) -> None:
        """The match is over."""
        ...


@dataclass(frozen=True)
class Course:
    """Everything that is the same for every viewer: the curriculum, the model, the league."""

    threat: ThreatModel
    tutor: Tutor
    concept_map: ConceptMap = field(default_factory=load_concept_map)
    league: League = field(default_factory=lambda: generate_league(np.random.default_rng(0)))

    @property
    def model(self) -> BktModel:
        """The knowledge model in use."""
        return BktModel(self.concept_map)

    @property
    def active(self) -> tuple[ConceptKey, ...]:
        """The concepts the app can ask about."""
        return active_concepts(self.concept_map)

    def names(self) -> dict[ConceptKey, str]:
        """Each active concept's name, for progress bars."""
        return {key: self.concept_map.concept(key).name for key in self.active}

    def mastery(self, state: LearnerState) -> dict[ConceptKey, float]:
        """Mastery of each active concept after the viewer's answers, by concept key."""
        model = self.model
        replayed = state.model_state(model, self.active)
        return {key: model.mastery(replayed, key) for key in self.active}

    def bars(self, state: LearnerState) -> dict[str, float]:
        """Mastery of each active concept after the viewer's answers, by concept name."""
        names = self.names()
        return {names[key]: value for key, value in self.mastery(state).items()}

    def fixture(
        self, seed: int, match_number: int, club: TeamId | None = None
    ) -> tuple[Club, Club, int]:
        """The clubs and the match seed for one of a viewer's matches.

        With a club, the match is one of that club's fixtures; without one, any fixture.
        """
        fixtures = season_fixtures(self.league)
        if club is not None:
            fixtures = tuple(pair for pair in fixtures if club in pair)
        home, away = fixtures[(seed * 7 + match_number) % len(fixtures)]
        return self.league.club(home), self.league.club(away), seed * 1000 + match_number


@dataclass(frozen=True)
class PreparedMatch:
    """One of a viewer's matches, ready to watch: the same for every viewer with that seed.

    Preparing it is the slow part of watching a match, and it never depends on the viewer's
    answers, so a server can prepare it once and reuse it.
    """

    home: Club
    away: Club
    seed: int
    match: Match
    ctx: MatchContext
    timeline: PhaseTimeline
    candidates: tuple[Candidate, ...]
    lineups: tuple[Lineup, Lineup]


def prepare_match(
    course: Course, seed: int, match_number: int, club: TeamId | None = None
) -> PreparedMatch:
    """Simulate a viewer's match and find its phases of play and candidate moments.

    Args:
        course: What every viewer shares.
        seed: The viewer's session seed.
        match_number: Which of the viewer's matches.
        club: The club the viewer supports, if they chose one.
    """
    home, away, match_seed = course.fixture(seed, match_number, club)
    match = play_designed_match(home, away, match_seed)
    ctx = match_context(match, rate_match(course.threat, match))
    timeline = phase_timeline(match)
    candidates = find_candidates(ctx, timeline, course.concept_map, course.active)
    lineups = designed_lineups(home, away)
    return PreparedMatch(home, away, match_seed, match, ctx, timeline, candidates, lineups)


def seed_for_viewer(viewer_id: str) -> int:
    """The session seed a viewer gets unless one is chosen: the same every time for a name."""
    return zlib.crc32(viewer_id.encode()) % 10_000


def start_session(
    store: LearnerStore, viewer_id: str, seed: int, introduced: Collection[ConceptKey] = ()
) -> Stored:
    """The viewer's record: read it, or create it with this seed if it is new.

    ``introduced`` is what a new viewer has already met: the welcome covers every active
    concept, so the page passes them all; a record that exists keeps its own.
    """
    stored = store.get(viewer_id)
    if stored is None:
        state = LearnerState(viewer_id, seed).with_introduced(introduced)
        stored = Stored(state, store.create(state))
    return stored


def mark_introduced(
    store: LearnerStore, viewer_id: str, concepts: Collection[ConceptKey]
) -> Stored:
    """Record that the viewer has had a First look at these concepts.

    Raises:
        ValueError: If there is no such viewer.
    """
    stored = store.get(viewer_id)
    if stored is None:
        raise ValueError(f"no learner {viewer_id!r}; start a session first")
    state = stored.state.with_introduced(concepts)
    if state == stored.state:
        return stored
    return Stored(state, store.put(state, stored.etag))


class ClubLockedError(Exception):
    """The viewer has started watching, so the club whose fixtures they watch can't change."""


def choose_club(course: Course, store: LearnerStore, viewer_id: str, club: TeamId) -> Stored:
    """Make ``club`` the viewer's team, before they have answered anything.

    Raises:
        ValueError: If there is no such viewer or club.
        ClubLockedError: If the viewer has answered a question or finished a match.
    """
    if club not in {each.team_id for each in course.league.clubs}:
        raise ValueError(f"no club with id {club}")
    stored = store.get(viewer_id)
    if stored is None:
        raise ValueError(f"no learner {viewer_id!r}; start a session first")
    if stored.state.club == club:
        return stored
    if not stored.state.can_choose_club:
        raise ClubLockedError(viewer_id)
    state = replace(stored.state, club=club)
    return Stored(state, store.put(state, stored.etag))


def choose_pace(store: LearnerStore, viewer_id: str, pace: Pace) -> Stored:
    """Set how often the viewer wants questions: now, or from their next match if one is under way.

    Raises:
        ValueError: If there is no such viewer.
    """
    stored = store.get(viewer_id)
    if stored is None:
        raise ValueError(f"no learner {viewer_id!r}; start a session first")
    state = stored.state.with_pace(pace)
    return Stored(state, store.put(state, stored.etag))


def watch_match(
    course: Course,
    store: LearnerStore,
    viewer_id: str,
    viewer: Viewer,
    now: Callable[[], str],
    prepare: Callable[[int, int, TeamId | None], PreparedMatch] | None = None,
) -> LearnerState:
    """Watch the viewer's next match, asking questions as the selector decides.

    Answers already given in this match, before a stop, are replayed rather than asked again.

    Args:
        course: What every viewer shares.
        store: Where the record is kept; it is saved after every answer.
        viewer_id: Whose session it is.
        viewer: Who answers.
        now: The time of each answer, as ISO 8601.
        prepare: Gives the prepared match for a session seed, match number and club; by
            default `prepare_match`, every time. A server passes a cached one.

    Returns:
        The record after the match.

    Raises:
        ValueError: If the viewer has no record, or has watched every match.
    """
    stored = store.get(viewer_id)
    if stored is None:
        raise ValueError(f"no learner {viewer_id!r}; start a session first")
    if stored.state.finished:
        raise ValueError(f"{viewer_id!r} has watched every match")
    state, etag = stored.state, stored.etag
    number = state.match_number
    if prepare is None:
        prepared = prepare_match(course, state.seed, number, state.club)
    else:
        prepared = prepare(state.seed, number, state.club)
    home, away, seed, match = prepared.home, prepared.away, prepared.seed, prepared.match
    ctx, timeline, candidates = prepared.ctx, prepared.timeline, prepared.candidates
    model = course.model
    earlier = [a for a in state.attempts if a.match_number < number]
    recorded = [a for a in state.attempts if a.match_number == number]
    history: list[Attempt] = list(earlier)
    rng = np.random.default_rng(seed)

    replayed: dict[int, BktState] = {}

    def mastery_state() -> BktState:
        # The selector reads mastery at every candidate; replay only when an answer is added.
        if len(history) not in replayed:
            replayed.clear()
            replayed[len(history)] = LearnerState(
                viewer_id, state.seed, attempts=tuple(history)
            ).model_state(model, course.active)
        return replayed[len(history)]

    def mastery(concept: ConceptKey) -> float:
        return model.mastery(mastery_state(), concept)

    def bars() -> dict[str, float]:
        current = mastery_state()
        return {name: model.mastery(current, key) for key, name in course.names().items()}

    viewer.begin(MatchStart(number, home.name, away.name, bars()))
    previous: Delivered | None = None

    def ask(prompt: Prompt) -> bool:
        nonlocal state, etag, previous
        candidate = prompt.candidate
        question = build_question(
            candidate, prompt.level, prompt.delivered.delivery, ctx, course.threat, rng
        )
        if question is None:
            return False
        if len(history) - len(earlier) < len(recorded):
            # Already answered before a stop: replay it without asking.
            history.append(recorded[len(history) - len(earlier)])
            previous = prompt.delivered
            return True
        pack = build_pack(
            question, prompt.delivered, ctx, course.threat, course.league, course.concept_map
        )
        view = question_view(pack)
        text = fill(course.tutor.question(view).text, question_values(view))
        answer = viewer.ask(Asked(pack, view, text, match, prompt, previous))
        previous = prompt.delivered
        grade = ChoiceGrader().grade(pack, answer)
        attempt = Attempt(
            match_number=number,
            action_id=candidate.tag.action_id,
            concept=candidate.concept,
            form=question.form,
            asks=question.asks,
            level=question.level,
            delivery=prompt.delivered.delivery,
            difficulty=candidate.difficulty,
            options=len(question.options),
            chosen=answer.key,
            correct=grade.correct,
            pack_id=pack.pack_id,
            answered_at=now(),
            asked_in=prompt.delivered.period_id,
        )
        before = mastery_state()
        history.append(attempt)
        state = state.answered(attempt)
        etag = store.put(state, etag)
        _, update = model.update(before, attempt.observation())
        feedback = course.tutor.feedback(pack, grade, _history(history[:-1], attempt.concept))
        values = feedback_values(pack, grade.chosen)
        viewer.tell(
            Told(
                pack=pack,
                grade=grade,
                verdict=grade.verdict,
                explanation=fill(feedback.explanation, values),
                takeaway=fill(feedback.takeaway, values),
                source=feedback.source,
                update=model.explain(update),
                mastery=bars(),
                misconception=None
                if feedback.misconception is None
                else fill(feedback.misconception, values),
            )
        )
        return True

    prompts = run_match(
        candidates,
        timeline,
        match.events,
        course.concept_map,
        course.active,
        model.thresholds,
        mastery,
        ask,
        state.pace,
    )
    state = state.next_match()
    store.put(state, etag)
    viewer.end(bars(), len(prompts))
    return state


# How many earlier answers on the concept the Tutor is told about.
RECENT_ANSWERS = 5


def _history(earlier: Sequence[Attempt], concept: ConceptKey) -> History:
    """The viewer's answers on one concept before this one, for the Tutor: right or wrong."""
    on_concept = [attempt for attempt in earlier if attempt.concept == concept]
    last_wrong = next((a.asks.value for a in reversed(on_concept) if not a.correct), None)
    return History(tuple(a.correct for a in on_concept[-RECENT_ANSWERS:]), last_wrong)


@dataclass
class DemoViewer:
    """A scripted viewer who gets better: some right in match 1, more in 2, all in 3.

    In match ``n`` it answers correctly when the question's number in that match (from 0)
    leaves no remainder when divided by ``4 - n``: one in three, then one in two, then all. A
    wrong answer is the first wrong option. It records what it saw, for tests and transcripts.
    """

    seen: list[Told] = field(default_factory=list[Told])
    asked: list[Asked] = field(default_factory=list[Asked])
    starts: list[MatchStart] = field(default_factory=list[MatchStart])
    on_tell: Callable[[Told], None] | None = None
    on_begin: Callable[[MatchStart], None] | None = None
    on_ask: Callable[[Asked, str], None] | None = None
    _in_match: int = 0

    def begin(self, start: MatchStart) -> None:
        """Note the match."""
        self.starts.append(start)
        self._in_match = 0
        if self.on_begin is not None:
            self.on_begin(start)

    def ask(self, asked: Asked) -> Answer:
        """Answer by the script."""
        self.asked.append(asked)
        match_number = self.starts[-1].match_number
        right = self._in_match % (4 - match_number) == 0
        self._in_match += 1
        keys: Sequence[str] = [o.key for o in asked.pack.options if o.correct == right]
        if self.on_ask is not None:
            self.on_ask(asked, keys[0])
        return ChoiceAnswer(keys[0])

    def tell(self, told: Told) -> None:
        """Remember the feedback."""
        self.seen.append(told)
        if self.on_tell is not None:
            self.on_tell(told)

    def end(self, mastery: dict[str, float], asked: int) -> None:
        """Nothing to do."""
