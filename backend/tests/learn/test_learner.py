from btl.learn.bkt import BktModel
from btl.learn.concept_map import load_concept_map
from btl.learn.knowledge import Delivery
from btl.learn.learner import MATCHES_PER_SESSION, Attempt, LearnerState
from btl.learn.pace import Pace
from btl.learn.questions import Asks, Form
from tests.fixtures.learning import ACTIVE, COUNTER_PRESS, LINE_BREAKING


def attempt(correct: bool, match_number: int = 1, action_id: int = 100) -> Attempt:
    return Attempt(
        match_number=match_number,
        action_id=action_id,
        concept=LINE_BREAKING,
        form=Form.PREDICT,
        asks=Asks.WHERE_TO_PASS,
        level=2,
        delivery=Delivery.LIVE,
        difficulty=0.5,
        options=3,
        chosen="B",
        correct=correct,
        pack_id="0123456789abcdef",
        answered_at="2026-10-08T12:00:00+00:00",
    )


def test_mastery_is_always_replayed_from_the_answers() -> None:
    model = BktModel(load_concept_map())
    state = LearnerState("lily", seed=7).answered(attempt(True)).answered(attempt(True))

    replayed = state.model_state(model, ACTIVE)
    by_hand = model.initial_state(ACTIVE)
    for answer in state.attempts:
        by_hand, _ = model.update(by_hand, answer.observation())

    assert model.mastery(replayed, LINE_BREAKING) == model.mastery(by_hand, LINE_BREAKING)
    assert model.mastery(replayed, LINE_BREAKING) > 0.7
    assert model.mastery(replayed, COUNTER_PRESS) == 0.15


def test_an_attempt_becomes_the_observation_a_model_reads() -> None:
    observation = attempt(False).observation()

    assert observation.concepts == (LINE_BREAKING,)
    assert not observation.correct
    assert (observation.options, observation.level, observation.delivery) == (3, 2, Delivery.LIVE)


def test_a_session_is_three_matches_and_remembers_what_was_asked() -> None:
    state = LearnerState("lily", seed=7).answered(attempt(True, action_id=12))

    assert state.asked_in(1) == {(LINE_BREAKING, 12)}
    assert state.asked_in(2) == frozenset()
    for _ in range(MATCHES_PER_SESSION):
        assert not state.finished
        state = state.next_match()
    assert state.finished and state.match_number == 4


def test_a_pace_set_before_any_answer_applies_at_once() -> None:
    state = LearnerState("lily", 7).with_pace(Pace.RARELY)

    assert (state.pace, state.pace_next) == (Pace.RARELY, None)


def test_a_pace_set_part_way_through_a_match_waits_for_the_next_one() -> None:
    state = LearnerState("lily", 7).answered(attempt(True)).with_pace(Pace.OFF)

    assert (state.pace, state.pace_next) == (Pace.NORMAL, Pace.OFF)
    after = state.next_match()
    assert (after.pace, after.pace_next) == (Pace.OFF, None)
    assert state.with_pace(Pace.NORMAL).pace_next is None
