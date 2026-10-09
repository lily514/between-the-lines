from collections.abc import Callable
from dataclasses import dataclass, field
from itertools import pairwise

import pytest

from btl.concepts.base import ConceptTag
from btl.concepts.phase import PhaseOfPlay, PhaseTimeline, Segment, phase_timeline
from btl.learn.bkt import BktModel
from btl.learn.candidates import Candidate
from btl.learn.concept_map import ConceptKey, Thresholds, load_concept_map
from btl.learn.knowledge import Delivery
from btl.learn.questions import active_concepts
from btl.learn.selector import (
    BREAK_CAP,
    IN_PLAY_CAP,
    MINIMUM_PER_MATCH,
    SPACING,
    Prompt,
    level_for,
    run_match,
)
from btl.schema.event import Event
from btl.schema.ids import ActionId, GameId
from btl.schema.vocab import ActionType, ConceptId
from tests.fixtures.learning import COUNTER_PRESS, LINE_BREAKING, designed_with_candidates
from tests.fixtures.matches import HOME, HOME_MIDFIELDER, make_event

SETTLED, TRANSITION = PhaseOfPlay.SETTLED, PhaseOfPlay.TRANSITION
THRESHOLDS = Thresholds(unlock=0.8, mastery=0.95)
DETECTORS = {LINE_BREAKING: ConceptId.LINE_BREAKING_PASS, COUNTER_PRESS: ConceptId.COUNTER_PRESS}
MINUTE = 60.0


@dataclass
class Scenario:
    """A hand-built match: candidates, dead balls and breaks, at chosen times."""

    candidates: list[Candidate] = field(default_factory=list[Candidate])
    segments: list[Segment] = field(default_factory=list[Segment])
    events: list[Event] = field(default_factory=list[Event])
    mastery: dict[ConceptKey, float] = field(
        default_factory=lambda: {LINE_BREAKING: 0.15, COUNTER_PRESS: 0.15}
    )
    asked: list[Prompt] = field(default_factory=list[Prompt])

    def moment(
        self,
        minute: float,
        difficulty: float,
        phase: PhaseOfPlay = SETTLED,
        concept: ConceptKey = LINE_BREAKING,
        period: int = 1,
    ) -> Candidate:
        action = ActionId(len(self.events))
        self.events.append(make_event(action, HOME, HOME_MIDFIELDER, (50, 34), (60, 34)))
        tag = ConceptTag(DETECTORS[concept], GameId(1), action, (action, action), difficulty, {})
        candidate = Candidate(concept, tag, difficulty, phase, period, minute * MINUTE)
        self.candidates.append(candidate)
        return candidate

    def dead_ball(
        self, minute: float, seconds: float = 25.0, restart: ActionType = ActionType.GOALKICK
    ) -> None:
        action = ActionId(len(self.events))
        self.events.append(
            make_event(action, HOME, HOME_MIDFIELDER, (5, 34), (40, 34), action_type=restart)
        )
        start = minute * MINUTE
        self.segments.append(
            Segment(PhaseOfPlay.DEAD_BALL, 1, start, start + seconds, action, action)
        )

    def breaks(self) -> None:
        for period, kind in ((1, PhaseOfPlay.HALF_TIME), (2, PhaseOfPlay.FULL_TIME)):
            self.segments.append(Segment(kind, period, 2700.0, 2700.0, ActionId(0), ActionId(0)))

    def run(self, ask: Callable[[Prompt], bool] | None = None) -> list[Prompt]:
        def record(prompt: Prompt) -> bool:
            if ask is not None and not ask(prompt):
                return False
            self.asked.append(prompt)
            return True

        concept_map = load_concept_map()
        run_match(
            sorted(self.candidates, key=lambda c: (c.period_id, c.time_seconds)),
            PhaseTimeline(tuple(sorted(self.segments, key=lambda s: (s.period_id, s.start))), ()),
            self.events,
            concept_map,
            active_concepts(concept_map),
            THRESHOLDS,
            lambda concept: self.mastery[concept],
            record,
        )
        return self.asked


def minutes(prompts: list[Prompt]) -> list[float]:
    return [p.delivered.time_seconds / MINUTE for p in prompts]


@pytest.mark.parametrize(
    ("mastery", "level"), [(0.0, 1), (0.39, 1), (0.4, 2), (0.69, 2), (0.7, 3), (0.99, 3)]
)
def test_the_level_follows_mastery(mastery: float, level: int) -> None:
    assert level_for(mastery) == level


def test_a_beginner_is_asked_live_about_an_easy_moment_but_not_a_hard_one() -> None:
    scene = Scenario()
    scene.moment(10, difficulty=0.8)
    easy = scene.moment(30, difficulty=0.2)

    (prompt,) = scene.run()

    assert prompt.candidate is easy and prompt.level == 1
    assert prompt.delivered.delivery is Delivery.LIVE
    assert prompt.delivered.phase is SETTLED


def test_a_moment_in_a_transition_waits_for_the_next_long_dead_ball() -> None:
    scene = Scenario()
    scene.moment(10, difficulty=0.2, phase=TRANSITION, concept=COUNTER_PRESS)
    scene.dead_ball(11, seconds=12)
    scene.dead_ball(14, seconds=25, restart=ActionType.CORNER_CROSSED)

    (prompt,) = scene.run()

    assert prompt.delivered.delivery is Delivery.DEFERRED
    assert prompt.delivered.phase is PhaseOfPlay.DEAD_BALL
    assert (minutes([prompt]), prompt.delivered.restart) == ([14], "corner")


def test_questions_are_spaced_at_least_eight_minutes_apart() -> None:
    scene = Scenario()
    for minute in (10, 13, 19):
        scene.moment(minute, difficulty=0.2)

    assert minutes(scene.run()) == [10, 19]
    assert SPACING == 8 * MINUTE


def test_no_more_than_four_questions_while_the_match_is_on() -> None:
    scene = Scenario()
    for minute in range(5, 90, 9):
        scene.moment(minute, difficulty=0.2)

    assert len(scene.run()) == IN_PLAY_CAP


def test_breaks_ask_up_to_two_queued_questions_whatever_the_spacing() -> None:
    scene = Scenario()
    scene.moment(40, difficulty=0.2, phase=TRANSITION)
    scene.moment(43, difficulty=0.2, phase=TRANSITION, concept=COUNTER_PRESS)
    scene.breaks()

    prompts = scene.run()

    assert [p.delivered.phase for p in prompts] == [PhaseOfPlay.HALF_TIME] * BREAK_CAP
    assert [p.candidate.concept for p in prompts] == [LINE_BREAKING, COUNTER_PRESS]


def test_a_queued_question_is_re_levelled_to_mastery_when_asked() -> None:
    scene = Scenario()
    scene.moment(10, difficulty=0.2)
    scene.moment(20, difficulty=0.35, phase=TRANSITION)
    scene.dead_ball(30)

    def answer_and_learn(prompt: Prompt) -> bool:
        scene.mastery[LINE_BREAKING] = 0.5
        return True

    prompts = scene.run(answer_and_learn)

    assert [(p.level, p.delivered.delivery) for p in prompts] == [
        (1, Delivery.LIVE),
        (2, Delivery.DEFERRED),
    ]


def test_a_queued_question_is_dropped_once_its_concept_is_mastered() -> None:
    scene = Scenario()
    scene.moment(10, difficulty=0.2, phase=TRANSITION)
    scene.moment(12, difficulty=0.2, phase=TRANSITION, concept=COUNTER_PRESS)
    scene.dead_ball(20)
    scene.dead_ball(30)

    def master_line_breaking(prompt: Prompt) -> bool:
        scene.mastery[LINE_BREAKING] = 0.97
        return True

    # Line-breaking is mastered as soon as the first question is answered, so counter-press,
    # queued second, is asked next; nothing else remains.
    prompts = scene.run(master_line_breaking)

    assert [p.candidate.concept for p in prompts] == [LINE_BREAKING, COUNTER_PRESS]


def test_one_answer_changes_the_very_next_decision() -> None:
    scene = Scenario()
    scene.moment(10, difficulty=0.2)
    scene.moment(20, difficulty=0.2)
    hard = scene.moment(30, difficulty=0.65)

    def learn_fast(prompt: Prompt) -> bool:
        scene.mastery[LINE_BREAKING] = 0.6
        return True

    prompts = scene.run(learn_fast)

    # After the first answer the viewer is at level 2: the easy moment at 20 no longer fits,
    # the harder one at 30 does.
    assert [p.candidate.time_seconds / MINUTE for p in prompts] == [10, 30]
    assert prompts[-1].candidate is hard and prompts[-1].level == 2


def test_the_breaks_make_sure_of_two_questions_ignoring_difficulty() -> None:
    scene = Scenario()
    scene.moment(10, difficulty=0.9)
    scene.moment(20, difficulty=0.95)
    scene.breaks()

    prompts = scene.run()

    assert len(prompts) == MINIMUM_PER_MATCH
    assert all(p.delivered.phase is PhaseOfPlay.HALF_TIME for p in prompts)
    assert [p.candidate.difficulty for p in prompts] == [0.9, 0.95]


def test_with_everything_mastered_review_is_occasional_and_hard() -> None:
    scene = Scenario(mastery={LINE_BREAKING: 0.97, COUNTER_PRESS: 0.97})
    for minute in (10, 25, 40):
        scene.moment(minute, difficulty=0.8)

    prompts = scene.run()

    assert [(p.level, minutes([p])[0]) for p in prompts] == [(3, 10)]


def test_a_question_that_could_not_be_asked_does_not_count() -> None:
    scene = Scenario()
    scene.moment(10, difficulty=0.2)
    scene.moment(12, difficulty=0.2)

    prompts = scene.run(lambda prompt: prompt.candidate.time_seconds > 11 * MINUTE)

    assert minutes(prompts) == [12]


@pytest.mark.parametrize("seed", range(40))
def test_in_simulated_matches_no_question_is_ever_asked_during_a_transition(seed: int) -> None:
    match, _, candidates = designed_with_candidates(seed)
    concept_map = load_concept_map()
    active = active_concepts(concept_map)
    model = BktModel(concept_map)
    mastery = {key: model.params(key).prior for key in active}

    def answer_right(prompt: Prompt) -> bool:
        concept = prompt.candidate.concept
        mastery[concept] = min(0.99, mastery[concept] + 0.15)
        return True

    prompts = run_match(
        candidates,
        phase_timeline(match),
        match.events,
        concept_map,
        active,
        model.thresholds,
        lambda key: mastery[key],
        answer_right,
    )

    assert len(prompts) >= MINIMUM_PER_MATCH
    assert all(p.delivered.phase is not TRANSITION for p in prompts)
    assert all(
        p.candidate.phase is SETTLED for p in prompts if p.delivered.delivery is Delivery.LIVE
    )
    in_play = [p for p in prompts if p.delivered.phase in (SETTLED, PhaseOfPlay.DEAD_BALL)]
    assert len(in_play) <= IN_PLAY_CAP
    times = [(p.delivered.period_id - 1) * 2700 + p.delivered.time_seconds for p in in_play]
    assert all(later - earlier >= SPACING for earlier, later in pairwise(times))
    for kind in (PhaseOfPlay.HALF_TIME, PhaseOfPlay.FULL_TIME):
        assert sum(p.delivered.phase is kind for p in prompts) <= BREAK_CAP
