from importlib import resources

import pytest

from btl.learn.bkt import BktModel, BktParams, BktState
from btl.learn.concept_map import ConceptKey, load_concept_map, parse_concept_map
from btl.learn.knowledge import Delivery, Observation, replay

LINE_BREAKING = ConceptKey("line_breaking_pass")


def answer(correct: bool, *, options: int = 3, delivery: Delivery = Delivery.LIVE) -> Observation:
    return Observation((LINE_BREAKING,), correct, options, 0.5, 2, delivery)


def bkt() -> BktModel:
    return BktModel(load_concept_map())


def test_four_right_answers_climb_as_the_plan_worked_out() -> None:
    # Tier 2: prior 0.15, learn 0.15, slip 0.10; three options, so a guess is right 1 in 3.
    model = bkt()
    state = model.initial_state([LINE_BREAKING])
    climb = [model.mastery(state, LINE_BREAKING)]
    for _ in range(4):
        state, _ = model.update(state, answer(True))
        climb.append(model.mastery(state, LINE_BREAKING))

    assert climb == pytest.approx([0.15, 0.424, 0.716, 0.891, 0.963], abs=0.001)


def test_the_first_answer_follows_bayes_then_learning_by_hand() -> None:
    model = bkt()

    _, update = model.update(model.initial_state([LINE_BREAKING]), answer(True))
    (change,) = update.changes

    after_answer = 0.15 * 0.9 / (0.15 * 0.9 + 0.85 / 3)
    assert change.details["after answer"] == pytest.approx(after_answer)
    assert change.after == pytest.approx(after_answer + (1 - after_answer) * 0.15)


def test_a_wrong_answer_from_a_low_start_still_rises_and_says_why() -> None:
    model = bkt()

    _, update = model.update(model.initial_state([LINE_BREAKING]), answer(False))
    (change,) = update.changes

    assert change.before < change.after < 0.2
    assert "you've just seen the explanation" in model.explain(update)


def test_a_wrong_answer_from_a_high_start_falls() -> None:
    model = bkt()

    _, update = model.update(BktState({LINE_BREAKING: 0.8}), answer(False))
    (change,) = update.changes

    assert change.after < 0.5
    assert model.explain(update).startswith("Not this time. Someone who understands line-breaking")


def test_fewer_options_make_a_right_answer_count_for_less() -> None:
    model = bkt()
    start = model.initial_state([LINE_BREAKING])

    _, three = model.update(start, answer(True, options=3))
    _, two = model.update(start, answer(True, options=2))

    assert two.changes[0].after < three.changes[0].after
    assert "1 time in 2" in model.explain(two)


def test_bkt_ignores_when_the_question_was_asked() -> None:
    model = bkt()
    history = [answer(True), answer(False), answer(True)]
    deferred = [answer(a.correct, delivery=Delivery.DEFERRED) for a in history]

    live_state = replay(model, [LINE_BREAKING], history)
    deferred_state = replay(model, [LINE_BREAKING], deferred)

    assert model.mastery(live_state, LINE_BREAKING) == model.mastery(deferred_state, LINE_BREAKING)


def test_a_concept_without_answers_sits_at_its_tiers_prior() -> None:
    model = bkt()
    empty = model.initial_state([])

    assert model.mastery(empty, ConceptKey("possession")) == 0.4
    assert model.mastery(empty, LINE_BREAKING) == 0.15


def test_a_concepts_override_replaces_its_tier_default() -> None:
    model = with_override("prior: 0.5")

    assert model.params(LINE_BREAKING) == BktParams(prior=0.5, learn=0.15, slip=0.1)


def test_parameters_of_exactly_0_or_1_are_rejected() -> None:
    with pytest.raises(ValueError, match="slip must be strictly between 0 and 1"):
        BktParams(prior=0.2, learn=0.2, slip=0.0)


def test_a_question_where_guessing_is_as_good_as_knowing_is_rejected() -> None:
    model, sloppy = bkt(), with_override("slip: 0.6")

    model.update(model.initial_state([LINE_BREAKING]), answer(True, options=2))
    with pytest.raises(ValueError, match="the answer says nothing"):
        sloppy.update(sloppy.initial_state([LINE_BREAKING]), answer(True, options=2))


def with_override(parameters: str) -> BktModel:
    """The shipped map, with line-breaking passes given their own BKT parameters."""
    text = resources.files("btl.learn").joinpath("concept_map.yaml").read_text(encoding="utf-8")
    entry = "  - id: line_breaking_pass\n"
    assert entry in text
    return BktModel(
        parse_concept_map(
            text.replace(entry, f"{entry}    learner_models: {{bkt: {{{parameters}}}}}\n")
        )
    )
