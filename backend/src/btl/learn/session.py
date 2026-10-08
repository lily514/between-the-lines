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

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Protocol

import numpy as np

from btl.concepts.base import match_context
from btl.concepts.phase import phase_timeline
from btl.league.league import Club, League, generate_league, season_fixtures
from btl.learn.bkt import BktModel, BktState
from btl.learn.candidates import MATCH_DESIGN, find_candidates
from btl.learn.concept_map import ConceptKey, ConceptMap, load_concept_map
from btl.learn.evidence import EvidencePack, QuestionView, build_pack, question_view
from btl.learn.grader import Answer, ChoiceAnswer, ChoiceGrader, Grade
from btl.learn.learner import Attempt, LearnerState
from btl.learn.questions import active_concepts, build_question
from btl.learn.selector import Prompt, run_match
from btl.plant.planter import simulate_with_moments
from btl.schema.match import Match
from btl.store.base import LearnerStore, Stored
from btl.tutor.base import Tutor
from btl.tutor.slots import feedback_values, fill, question_values
from btl.value.xt import ThreatModel, rate_match

LEAGUE_SEED = 0


@dataclass(frozen=True, slots=True)
class Asked:
    """A question as the viewer meets it: the pack, its view, and the worded question."""

    pack: EvidencePack
    view: QuestionView
    text: str
    match: Match


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

    def bars(self, state: LearnerState) -> dict[str, float]:
        """Mastery of each active concept after the viewer's answers, by concept name."""
        model = self.model
        replayed = state.model_state(model, self.active)
        return {name: model.mastery(replayed, key) for key, name in self.names().items()}

    def fixture(self, seed: int, match_number: int) -> tuple[Club, Club, int]:
        """The clubs and the match seed for one of a viewer's matches."""
        fixtures = season_fixtures(self.league)
        home, away = fixtures[(seed * 7 + match_number) % len(fixtures)]
        return self.league.club(home), self.league.club(away), seed * 1000 + match_number


def start_session(store: LearnerStore, viewer_id: str, seed: int) -> Stored:
    """The viewer's record: read it, or create it with this seed if it is new."""
    stored = store.get(viewer_id)
    if stored is None:
        state = LearnerState(viewer_id, seed)
        stored = Stored(state, store.create(state))
    return stored


def watch_match(
    course: Course,
    store: LearnerStore,
    viewer_id: str,
    viewer: Viewer,
    now: Callable[[], str],
) -> LearnerState:
    """Watch the viewer's next match, asking questions as the selector decides.

    Answers already given in this match, before a stop, are replayed rather than asked again.

    Args:
        course: What every viewer shares.
        store: Where the record is kept; it is saved after every answer.
        viewer_id: Whose session it is.
        viewer: Who answers.
        now: The time of each answer, as ISO 8601.

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
    home, away, seed = course.fixture(state.seed, number)
    match = simulate_with_moments(home, away, seed, MATCH_DESIGN)
    ctx = match_context(match, rate_match(course.threat, match))
    timeline = phase_timeline(match)
    candidates = find_candidates(ctx, timeline, course.concept_map, course.active)
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

    def ask(prompt: Prompt) -> bool:
        nonlocal state, etag
        candidate = prompt.candidate
        question = build_question(
            candidate, prompt.level, prompt.delivered.delivery, ctx, course.threat, rng
        )
        if question is None:
            return False
        if len(history) - len(earlier) < len(recorded):
            # Already answered before a stop: replay it without asking.
            history.append(recorded[len(history) - len(earlier)])
            return True
        pack = build_pack(
            question, prompt.delivered, ctx, course.threat, course.league, course.concept_map
        )
        view = question_view(pack)
        text = fill(course.tutor.question(view).text, question_values(view))
        answer = viewer.ask(Asked(pack, view, text, match))
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
        )
        before = mastery_state()
        history.append(attempt)
        state = state.answered(attempt)
        etag = store.put(state, etag)
        _, update = model.update(before, attempt.observation())
        feedback = course.tutor.feedback(pack, grade)
        values = feedback_values(pack, grade.chosen)
        viewer.tell(
            Told(
                pack=pack,
                grade=grade,
                verdict=grade.verdict,
                explanation=fill(feedback.explanation, values),
                takeaway=feedback.takeaway,
                source=feedback.source,
                update=model.explain(update),
                mastery=bars(),
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
    )
    state = state.next_match()
    store.put(state, etag)
    viewer.end(bars(), len(prompts))
    return state


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
