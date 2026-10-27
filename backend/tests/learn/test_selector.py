from collections.abc import Callable
from dataclasses import dataclass, field
from itertools import pairwise

import pytest

from btl.concepts.base import ConceptTag
from btl.concepts.phase import PhaseOfPlay, PhaseTimeline, Segment, phase_timeline
from btl.learn.bkt import BktModel
from btl.learn.candidates import AskedWhen, Candidate
from btl.learn.concept_map import ConceptKey, Thresholds, load_concept_map
from btl.learn.knowledge import Delivery
from btl.learn.pace import Pace
from btl.learn.questions import active_concepts
from btl.learn.selector import (
    BREAK_CAP,
    IN_PLAY_CAP,
    MINIMUM_PER_MATCH,
    SPACING,
    TIER0_CAP,
    TIER0_MATCH_CAP,
    Prompt,
    level_for,
    run_match,
)
from btl.schema.event import Event
from btl.schema.ids import ActionId, GameId
from btl.schema.vocab import ActionType, ConceptId
from tests.fixtures.learning import (
    COUNTER_PRESS,
    FOULS,
    LINE_BREAKING,
    OFFSIDE,
    RESTARTS,
    SHOTS,
    TACKLES,
    designed_with_candidates,
)
from tests.fixtures.matches import HOME, HOME_MIDFIELDER, make_event

SETTLED, TRANSITION = PhaseOfPlay.SETTLED, PhaseOfPlay.TRANSITION
THRESHOLDS = Thresholds(unlock=0.8, mastery=0.95)
DETECTORS = {
    LINE_BREAKING: ConceptId.LINE_BREAKING_PASS,
    COUNTER_PRESS: ConceptId.COUNTER_PRESS,
    RESTARTS: ConceptId.RESTART,
    OFFSIDE: ConceptId.OFFSIDE,
    FOULS: ConceptId.FOUL,
    TACKLES: ConceptId.BALL_WIN,
    SHOTS: ConceptId.SHOT,
}
MINUTE = 60.0


@dataclass
class Scenario:
    """A hand-built match: candidates, dead balls and breaks, at chosen times."""

    candidates: list[Candidate] = field(default_factory=list[Candidate])
    segments: list[Segment] = field(default_factory=list[Segment])
    events: list[Event] = field(default_factory=list[Event])
    # The basics start mastered, so only the two concepts under test are on the frontier, and
    # counter-pressing, which waits for tackles, is open.
    mastery: dict[ConceptKey, float] = field(
        default_factory=lambda: {
            LINE_BREAKING: 0.15,
            COUNTER_PRESS: 0.15,
            TACKLES: 0.99,
            SHOTS: 0.99,
            RESTARTS: 0.99,
            OFFSIDE: 0.99,
            FOULS: 0.99,
        }
    )
    asked: list[Prompt] = field(default_factory=list[Prompt])
    pace: Pace = Pace.NORMAL

    def moment(
        self,
        minute: float,
        difficulty: float,
        phase: PhaseOfPlay = SETTLED,
        concept: ConceptKey = LINE_BREAKING,
        period: int = 1,
        asked_when: AskedWhen = AskedWhen.IN_PLAY,
    ) -> Candidate:
        action = ActionId(len(self.events))
        self.events.append(make_event(action, HOME, HOME_MIDFIELDER, (50, 34), (60, 34)))
        tag = ConceptTag(DETECTORS[concept], GameId(1), action, (action, action), difficulty, {})
        candidate = Candidate(concept, tag, difficulty, phase, period, minute * MINUTE, asked_when)
        self.candidates.append(candidate)
        return candidate

    def dead_ball(
        self,
        minute: float,
        seconds: float = 25.0,
        restart: ActionType = ActionType.GOALKICK,
        after: ActionId | None = None,
    ) -> None:
        """A dead ball, stopped after ``after`` (by default, an action of its own)."""
        action = ActionId(len(self.events))
        self.events.append(
            make_event(action, HOME, HOME_MIDFIELDER, (5, 34), (40, 34), action_type=restart)
        )
        start = minute * MINUTE
        stopped = action if after is None else after
        self.segments.append(
            Segment(PhaseOfPlay.DEAD_BALL, 1, start, start + seconds, stopped, action)
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
            self.pace,
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
    scene = Scenario()
    scene.mastery |= {LINE_BREAKING: 0.97, COUNTER_PRESS: 0.97}
    for minute in (10, 25, 40):
        scene.moment(minute, difficulty=0.8)

    prompts = scene.run()

    assert [(p.level, minutes([p])[0]) for p in prompts] == [(3, 10)]


def test_a_queued_basic_gives_up_its_place_to_a_rarer_concepts_moment() -> None:
    scene = Scenario()
    # Tackles stays high enough to keep counter-pressing open, so its moment is a hard one.
    scene.mastery |= {TACKLES: 0.85, SHOTS: 0.15}
    scene.moment(10, 0.8, TRANSITION, TACKLES)
    scene.moment(11, 0.2, SETTLED, SHOTS, asked_when=AskedWhen.AFTERWARDS)
    # The queue is full of basics when the match's one line-breaking review comes along.
    scene.moment(12, 0.2, TRANSITION, LINE_BREAKING)
    scene.moment(13, 0.2, TRANSITION, COUNTER_PRESS)
    scene.dead_ball(20)
    scene.dead_ball(30)
    scene.dead_ball(40)

    prompts = scene.run()

    assert [p.candidate.concept for p in prompts] == [LINE_BREAKING, COUNTER_PRESS]


def test_a_queued_moment_no_longer_wanted_gives_up_its_place() -> None:
    scene = Scenario()
    scene.mastery |= {TACKLES: 0.15}
    scene.moment(10, 0.2, TRANSITION, TACKLES)
    scene.moment(11, 0.2, TRANSITION, LINE_BREAKING)
    scene.dead_ball(20)
    scene.dead_ball(30)

    def master_tackles_first(prompt: Prompt) -> bool:
        scene.mastery[TACKLES] = 0.97
        return True

    prompts = scene.run(master_tackles_first)

    assert [p.candidate.concept for p in prompts] == [TACKLES, LINE_BREAKING]


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
    # Live means in settled play, or in the dead ball straight after a restart or a foul.
    assert all(
        p.candidate.phase is SETTLED
        or (
            p.delivered.phase is PhaseOfPlay.DEAD_BALL
            and p.candidate.asked_when is AskedWhen.AT_THE_STOPPAGE
        )
        for p in prompts
        if p.delivered.delivery is Delivery.LIVE
    )
    in_play = [p for p in prompts if p.delivered.phase in (SETTLED, PhaseOfPlay.DEAD_BALL)]
    assert len(in_play) <= IN_PLAY_CAP
    times = [(p.delivered.period_id - 1) * 2700 + p.delivered.time_seconds for p in in_play]
    assert all(later - earlier >= SPACING for earlier, later in pairwise(times))
    for kind in (PhaseOfPlay.HALF_TIME, PhaseOfPlay.FULL_TIME):
        assert sum(p.delivered.phase is kind for p in prompts) <= BREAK_CAP


def beginner_on_the_basics() -> Scenario:
    scene = Scenario()
    scene.mastery |= {RESTARTS: 0.15, OFFSIDE: 0.15, FOULS: 0.15}
    scene.mastery |= {LINE_BREAKING: 0.99, COUNTER_PRESS: 0.99}
    return scene


def test_a_restart_is_asked_live_at_its_own_stoppage_however_short() -> None:
    scene = beginner_on_the_basics()
    scene.moment(10, 0.1, TRANSITION, RESTARTS, asked_when=AskedWhen.AT_THE_STOPPAGE)

    (prompt,) = scene.run()

    assert prompt.delivered.delivery is Delivery.LIVE
    assert prompt.delivered.phase is PhaseOfPlay.DEAD_BALL
    assert prompt.delivered.restart is None
    assert minutes([prompt]) == [10]


def test_a_restart_that_cannot_be_asked_then_is_never_asked() -> None:
    scene = beginner_on_the_basics()
    scene.moment(10, 0.1, SETTLED, OFFSIDE)
    scene.moment(12, 0.1, SETTLED, RESTARTS, asked_when=AskedWhen.AT_THE_STOPPAGE)
    scene.breaks()

    prompts = scene.run()

    assert [p.candidate.concept for p in prompts] == [OFFSIDE]


def test_play_that_went_on_after_a_foul_is_only_reviewed_later() -> None:
    scene = beginner_on_the_basics()
    scene.moment(10, 0.1, SETTLED, FOULS, asked_when=AskedWhen.AFTERWARDS)
    scene.dead_ball(20)

    (prompt,) = scene.run()

    assert prompt.delivered.delivery is Delivery.DEFERRED
    assert minutes([prompt]) == [20]


def test_each_basic_concept_is_capped_and_so_are_all_of_them_together() -> None:
    scene = beginner_on_the_basics()
    stoppage, afterwards = AskedWhen.AT_THE_STOPPAGE, AskedWhen.AFTERWARDS
    # Four restarts: two are asked, then the concept is capped.
    for minute in (5, 14, 23, 32):
        scene.moment(minute, 0.1, SETTLED, RESTARTS, asked_when=stoppage)
    # Two offside calls live, which fills the in-play cap, and a third saved for the break.
    scene.moment(23.5, 0.1, SETTLED, OFFSIDE)
    scene.moment(32.5, 0.1, SETTLED, OFFSIDE)
    scene.moment(40, 0.1, TRANSITION, OFFSIDE)
    # Advantage after a foul, reviewed at half-time: the fifth basic question of the match.
    scene.moment(42, 0.1, SETTLED, FOULS, asked_when=afterwards)
    scene.moment(50, 0.1, SETTLED, FOULS, period=2, asked_when=afterwards)
    scene.breaks()

    prompts = scene.run()

    concepts = [p.candidate.concept for p in prompts]
    assert concepts.count(RESTARTS) == TIER0_CAP
    assert concepts.count(OFFSIDE) == TIER0_CAP
    assert len(concepts) == TIER0_MATCH_CAP == 5
    assert concepts.count(FOULS) == 1
    assert prompts[-1].delivered.phase is PhaseOfPlay.HALF_TIME


def test_a_review_at_the_stoppage_its_moment_caused_names_no_restart() -> None:
    scene = Scenario()
    caused = scene.moment(10, 0.2, TRANSITION)
    scene.dead_ball(10.2, restart=ActionType.FREEKICK_SHORT, after=caused.tag.action_id)
    other = Scenario()
    other.moment(10, 0.2, TRANSITION)
    other.dead_ball(20, restart=ActionType.FREEKICK_SHORT)

    (named_not,) = scene.run()
    (named,) = other.run()

    assert named_not.delivered.restart is None
    assert named.delivered.restart == "free kick"


def test_a_shot_review_never_names_the_stoppage_it_is_asked_at() -> None:
    scene = Scenario()
    scene.mastery |= {SHOTS: 0.15}
    scene.moment(10, 0.2, SETTLED, SHOTS, asked_when=AskedWhen.AFTERWARDS)
    # The kickoff after a later goal, which the shot had nothing to do with.
    scene.dead_ball(20, seconds=40, restart=ActionType.PASS)

    (prompt,) = scene.run()

    assert prompt.candidate.concept == SHOTS
    assert prompt.delivered.delivery is Delivery.DEFERRED
    assert prompt.delivered.restart is None


def test_a_stoppage_asks_only_its_own_restart_and_the_review_waits() -> None:
    scene = Scenario()
    scene.mastery |= {RESTARTS: 0.15}
    scene.moment(10, 0.2, TRANSITION, COUNTER_PRESS)
    scene.dead_ball(14, seconds=25, restart=ActionType.THROW_IN)
    scene.moment(14 + 5 / 60, 0.1, TRANSITION, RESTARTS, asked_when=AskedWhen.AT_THE_STOPPAGE)
    scene.dead_ball(30, seconds=25)

    prompts = scene.run()

    assert [(p.candidate.concept, p.delivered.delivery) for p in prompts] == [
        (RESTARTS, Delivery.LIVE),
        (COUNTER_PRESS, Delivery.DEFERRED),
    ]
    assert minutes(prompts)[1] == 30


def test_a_settled_moment_near_the_whistle_is_saved_for_the_break() -> None:
    scene = Scenario()
    scene.moment(44.75, difficulty=0.2)
    scene.breaks()

    (prompt,) = scene.run()

    assert prompt.delivered.delivery is Delivery.DEFERRED
    assert prompt.delivered.phase is PhaseOfPlay.HALF_TIME


def test_a_restart_near_the_whistle_is_not_asked() -> None:
    scene = beginner_on_the_basics()
    scene.moment(44.8, 0.1, TRANSITION, RESTARTS, asked_when=AskedWhen.AT_THE_STOPPAGE)
    scene.breaks()

    assert scene.run() == []


def test_a_review_waits_for_the_break_rather_than_a_dead_ball_near_the_whistle() -> None:
    scene = Scenario()
    scene.moment(40, 0.2, TRANSITION, COUNTER_PRESS)
    scene.dead_ball(44.6, seconds=20)
    scene.breaks()

    (prompt,) = scene.run()

    assert prompt.delivered.phase is PhaseOfPlay.HALF_TIME


def test_rarely_asks_at_most_one_question_while_the_match_is_on() -> None:
    scene = Scenario(pace=Pace.RARELY)
    for minute in range(5, 90, 9):
        scene.moment(minute, difficulty=0.2)

    assert len(scene.run()) == 1


def test_off_asks_nothing_at_all_not_even_at_the_breaks() -> None:
    scene = Scenario(pace=Pace.OFF)
    scene.moment(10, difficulty=0.2)
    scene.moment(20, 0.2, TRANSITION, COUNTER_PRESS)
    scene.breaks()

    assert scene.run() == []
