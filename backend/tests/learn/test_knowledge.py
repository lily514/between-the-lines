"""The contract every knowledge model must keep. A new model joins by being added to MODELS."""

from collections.abc import Callable
from dataclasses import replace
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

from btl.learn.bkt import BktModel
from btl.learn.concept_map import ConceptKey, load_concept_map
from btl.learn.knowledge import Delivery, KnowledgeModel, Observation, replay

ACTIVE = (ConceptKey("line_breaking_pass"), ConceptKey("counter_press"))

# Each model has its own state type, so the suite holds them as KnowledgeModel[Any].
MODELS: dict[str, Callable[[], KnowledgeModel[Any]]] = {
    "bkt": lambda: BktModel(load_concept_map()),
}

observations = st.builds(
    Observation,
    concepts=st.sampled_from(ACTIVE).map(lambda concept: (concept,)),
    correct=st.booleans(),
    options=st.integers(min_value=2, max_value=5),
    difficulty=st.floats(min_value=0, max_value=1),
    level=st.sampled_from((1, 2, 3)),
    delivery=st.sampled_from(Delivery),
)
histories = st.lists(observations, max_size=25)


@pytest.fixture(params=sorted(MODELS), scope="module")
def model(request: pytest.FixtureRequest) -> KnowledgeModel[Any]:
    name: str = request.param
    return MODELS[name]()


@given(history=histories)
def test_mastery_always_stays_between_0_and_1(
    model: KnowledgeModel[Any], history: list[Observation]
) -> None:
    state = model.initial_state(ACTIVE)
    for observation in history:
        state, update = model.update(state, observation)
        for change in update.changes:
            assert 0 <= change.after <= 1
            assert change.after == model.mastery(state, change.concept)


@given(history=histories, last=observations)
def test_a_correct_answer_never_lowers_mastery(
    model: KnowledgeModel[Any], history: list[Observation], last: Observation
) -> None:
    state = replay(model, ACTIVE, history)
    right = replace(last, correct=True)

    _, update = model.update(state, right)

    assert all(change.after >= change.before for change in update.changes)


@given(history=histories)
def test_the_same_answers_always_give_the_same_mastery(
    model: KnowledgeModel[Any], history: list[Observation]
) -> None:
    once = replay(model, ACTIVE, history)
    again = replay(model, ACTIVE, history)

    assert [model.mastery(once, c) for c in ACTIVE] == [model.mastery(again, c) for c in ACTIVE]


@given(history=histories)
def test_replaying_the_answers_matches_updating_one_at_a_time(
    model: KnowledgeModel[Any], history: list[Observation]
) -> None:
    state = model.initial_state(ACTIVE)
    for observation in history:
        state, _ = model.update(state, observation)

    replayed = replay(model, ACTIVE, history)

    assert [model.mastery(state, c) for c in ACTIVE] == [model.mastery(replayed, c) for c in ACTIVE]


@given(history=histories, last=observations)
def test_the_explanation_quotes_the_numbers_before_and_after(
    model: KnowledgeModel[Any], history: list[Observation], last: Observation
) -> None:
    state = replay(model, ACTIVE, history)

    _, update = model.update(state, last)
    sentence = model.explain(update)

    for change in update.changes:
        assert f"{round(change.before * 100)}%" in sentence
        assert f"{round(change.after * 100)}%" in sentence


def test_thresholds_unlock_before_mastery(model: KnowledgeModel[Any]) -> None:
    assert 0 < model.thresholds.unlock < model.thresholds.mastery < 1


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"concepts": ()}, "at least one concept"),
        ({"options": 1}, "at least 2 options"),
        ({"difficulty": 1.5}, "from 0 to 1"),
        ({"level": 4}, "level must be one of"),
    ],
)
def test_an_observation_no_question_could_produce_is_rejected(
    changes: dict[str, object], message: str
) -> None:
    valid = Observation((ACTIVE[0],), True, 3, 0.5, 1, Delivery.LIVE)

    with pytest.raises(ValueError, match=message):
        replace(valid, **changes)
