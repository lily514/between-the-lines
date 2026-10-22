import inspect
import re
from collections.abc import Mapping
from typing import cast

import pytest

from btl.learn.evidence import EvidencePack, question_view
from btl.learn.grader import Grade
from btl.learn.questions import Asks
from btl.tutor.prompts import (
    FEEDBACK_SCHEMA,
    INSTRUCTIONS,
    QUESTION_SCHEMA,
    Repair,
    feedback_request,
    question_request,
)
from btl.tutor.slots import feedback_values, question_values
from btl.tutor.templates import TemplateTutor
from btl.tutor.verifier import Failure
from tests.fixtures.packs import every_kind, first_of

TUTOR = TemplateTutor()


def question_prompt(pack: EvidencePack, repair: Repair | None = None) -> str:
    view = question_view(pack)
    return question_request(view, TUTOR.question(view).text, repair).prompt


def shown_before_answering(pack: EvidencePack) -> str:
    """Every value the question view itself shows, which may appear in its prompt."""
    view = question_view(pack)
    return " ".join([*question_values(view).values(), view.asks.value, view.concept_name]).lower()


@pytest.mark.parametrize("seed", range(40))
def test_a_question_prompt_holds_no_outcome_before_the_viewer_answers(seed: int) -> None:
    for pack in every_kind(seed):
        prompt = question_prompt(pack)
        shown = shown_before_answering(pack)
        facts = {**pack.outcome} | {
            name: fact for option in pack.options for name, fact in option.outcome.items()
        }
        for name, fact in facts.items():
            assert f"{{{name}}}" not in prompt and f".{name}}}" not in prompt, (pack.asks, name)
            value = fact.display.lower()
            hidden = re.search(rf"(?<![\w.]){re.escape(value)}(?![\w.])", prompt.lower())
            assert value in shown or hidden is None, (pack.asks, name, fact.display)
        right = next(option for option in pack.options if option.correct)
        assert "right answer" not in prompt.lower() and f"{right.key}:" not in prompt


def test_no_prompt_can_carry_anything_about_the_viewer() -> None:
    assert list(inspect.signature(question_request).parameters) == ["view", "plain", "repair"]
    assert list(inspect.signature(feedback_request).parameters) == ["pack", "grade", "repair"]


def test_a_question_prompt_lists_its_facts_as_slots_and_its_options_to_avoid() -> None:
    pack = first_of(Asks.WHERE_TO_PASS)
    view = question_view(pack)

    request = question_request(view, TUTOR.question(view).text)

    assert request.instructions == INSTRUCTIONS
    assert (request.schema_name, request.schema) == ("question", QUESTION_SCHEMA)
    assert f"{{player}} = {question_values(view)['player']}" in request.prompt
    assert all(f"- {option.label}" in request.prompt for option in view.options)
    assert "{A." not in request.prompt


def test_a_question_asked_later_says_so() -> None:
    later = next(p for p in every_kind(0) if p.timing.delivery != "live")

    assert "asked later" in question_prompt(later) and "{occurred_at}" in question_prompt(later)


@pytest.mark.parametrize("correct", [True, False])
def test_a_feedback_prompt_has_the_whole_pack_and_the_viewer_s_pick(correct: bool) -> None:
    pack = first_of(Asks.WHERE_TO_PASS)
    option = next(o for o in pack.options if o.correct is correct)
    grade = Grade(correct=correct, chosen=option.key)

    request = feedback_request(pack, grade)

    assert (request.schema_name, request.schema) == ("feedback", FEEDBACK_SCHEMA)
    values = feedback_values(pack, grade.chosen)
    for name in [*pack.outcome, *pack.context]:
        assert f"{{{name}}} = {values[name]}" in request.prompt
    assert all(
        f"{i}. {text}" in request.prompt for i, text in enumerate(pack.concept.misconceptions)
    )
    assert ("The viewer picked it." in request.prompt) is correct
    assert ("citing a {chosen.*} fact" in request.prompt) is not correct


def test_a_repair_shows_the_last_reply_and_every_failed_check() -> None:
    pack = first_of(Asks.WHAT_RESTART)
    failures = [Failure("hint", '"corner" comes from an option\'s label'), Failure("length", "x")]

    prompt = question_prompt(pack, Repair('{"text": "Is it a corner?"}', failures))

    assert '{"text": "Is it a corner?"}' in prompt
    assert '- hint: "corner" comes from an option\'s label' in prompt and "- length: x" in prompt


@pytest.mark.parametrize("schema", [QUESTION_SCHEMA, FEEDBACK_SCHEMA])
def test_each_schema_is_strict(schema: Mapping[str, object]) -> None:
    properties = cast(dict[str, object], schema["properties"])
    assert schema["required"] == list(properties) and schema["additionalProperties"] is False
