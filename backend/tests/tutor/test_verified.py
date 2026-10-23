"""The Tutor the viewer meets: the model's words when they pass, a repair, or the template."""

import json
from collections.abc import Iterator

import pytest

from btl.learn.evidence import question_view
from btl.learn.grader import Grade
from btl.learn.questions import Asks
from btl.tutor.foundry import FoundryTutor
from btl.tutor.model import FakeClient, ModelError
from btl.tutor.prompts import PROMPT_VERSION
from btl.tutor.templates import TemplateTutor
from btl.tutor.verified import CALL_BUDGET, CheckRecord, Fallback, VerifiedTutor
from tests.fixtures.packs import first_of

PACK = first_of(Asks.WHERE_TO_PASS)
VIEW = question_view(PACK)
WRONG = next(o for o in PACK.options if not o.correct)
RIGHT = Grade(correct=True, chosen=PACK.correct_key)
TEMPLATE = TemplateTutor()

GOOD_QUESTION = json.dumps({"text": "{player} is on the ball for {team}. Where should it go?"})
BAD_QUESTION = json.dumps({"text": "{player} is on the ball for {team}. Is option B right?"})
GOOD_EXPLANATION = (
    "The pass to {answer.target} went through {answer.lines_broken} lines and changed the chance "
    "of scoring by {answer.threat_added}, against {chosen.threat_added} for {chosen.target}."
)
CONFIRM = "The pass to {answer.target} went through {answer.lines_broken} lines."


def feedback_reply(explanation: str = GOOD_EXPLANATION, misconception: int | None = 1) -> str:
    """The model's JSON reply; ``misconception`` counts from 1, as the prompt numbers them."""
    return json.dumps(
        {
            "explanation": explanation,
            "takeaway": "Look for the gap.",
            "misconception": misconception,
        }
    )


def wrong_grade() -> Grade:
    worse = min(
        (o for o in PACK.options if not o.correct),
        key=lambda o: float(o.outcome["threat_added"].value),
    )
    return Grade(correct=False, chosen=worse.key)


class Clock:
    """Seconds that pass as the script says, one value per reading."""

    def __init__(self, *readings: float) -> None:
        self._readings: Iterator[float] = iter(readings)
        self._last = 0.0

    def __call__(self) -> float:
        self._last = next(self._readings, self._last)
        return self._last


def tutor(
    *replies: str | ModelError, clock: Clock | None = None
) -> tuple[VerifiedTutor, FakeClient, list[CheckRecord]]:
    fake = FakeClient(list(replies))
    records: list[CheckRecord] = []
    verified = VerifiedTutor(
        FoundryTutor(fake), TEMPLATE, records.append, clock=clock or Clock(0.0)
    )
    return verified, fake, records


def test_a_question_that_passes_first_time_is_used() -> None:
    verified, fake, records = tutor(GOOD_QUESTION)

    assert verified.question(VIEW).text == json.loads(GOOD_QUESTION)["text"]
    assert len(fake.requests) == 1 and fake.requests[0].timeout == CALL_BUDGET
    assert [(r.kind, r.attempt, r.passed, r.reasons) for r in records] == [
        ("question", 1, True, ())
    ]
    assert records[0].prompt_version == PROMPT_VERSION and records[0].model == "fake-model"


def test_a_question_that_fails_is_repaired_once_with_the_reasons() -> None:
    verified, fake, records = tutor(BAD_QUESTION, GOOD_QUESTION, clock=Clock(0.0, 0.0, 2.5))

    assert verified.question(VIEW).text == json.loads(GOOD_QUESTION)["text"]
    first, repair = fake.requests
    assert "hint" not in first.prompt and "- hint:" in repair.prompt
    assert repair.timeout == CALL_BUDGET - 2.5
    assert [(r.attempt, r.passed, r.reasons) for r in records] == [
        (1, False, ("hint",)),
        (2, True, ()),
    ]


@pytest.mark.parametrize(
    ("replies", "calls"),
    [
        ((BAD_QUESTION, BAD_QUESTION), 2),
        ((ModelError("timed out"),), 1),
        (("not JSON",), 1),
    ],
    ids=["fails twice", "timeout", "malformed"],
)
def test_a_question_falls_back_to_the_template(
    replies: tuple[str | ModelError, ...], calls: int
) -> None:
    verified, fake, records = tutor(*replies)

    assert verified.question(VIEW) == TEMPLATE.question(VIEW)
    assert len(fake.requests) == calls == len(records)
    assert not any(record.passed for record in records)


def test_a_failed_call_is_recorded_with_its_error() -> None:
    verified, _, records = tutor(ModelError("timed out"))

    verified.question(VIEW)

    assert records[0].error == "timed out" and records[0].model is None


def test_no_repair_is_tried_once_the_budget_is_spent() -> None:
    verified, fake, _ = tutor(BAD_QUESTION, GOOD_QUESTION, clock=Clock(0.0, 0.0, CALL_BUDGET + 1))

    assert verified.question(VIEW) == TEMPLATE.question(VIEW)
    assert len(fake.requests) == 1


def test_feedback_that_passes_names_the_model_and_its_mix_up() -> None:
    grade = wrong_grade()
    verified, _, _ = tutor(feedback_reply(misconception=2))

    feedback = verified.feedback(PACK, grade)

    assert feedback.source == "fake-model"
    assert feedback.explanation == GOOD_EXPLANATION
    assert feedback.misconception == PACK.concept.misconceptions[1]


def test_repaired_feedback_says_so() -> None:
    verified, _, _ = tutor(feedback_reply("Correct! " + GOOD_EXPLANATION), feedback_reply())

    assert verified.feedback(PACK, wrong_grade()).source == "fake-model (repaired)"


@pytest.mark.parametrize(
    ("replies", "source"),
    [
        ((feedback_reply("Nice."), feedback_reply("Nice.")), "template (fallback: grounded)"),
        ((ModelError("401"),), "template (fallback: no reply)"),
        (("[]",), "template (fallback: no reply)"),
    ],
    ids=["fails twice", "no reply", "malformed"],
)
def test_feedback_that_falls_back_says_why(
    replies: tuple[str | ModelError, ...], source: str
) -> None:
    grade = wrong_grade()
    verified, _, _ = tutor(*replies)

    feedback = verified.feedback(PACK, grade)
    template = TEMPLATE.feedback(PACK, grade)

    assert feedback.source == source
    assert (feedback.explanation, feedback.misconception) == (
        template.explanation,
        template.misconception,
    )


@pytest.mark.parametrize(
    ("grade", "explanation", "misconception"),
    [
        (None, GOOD_EXPLANATION, 99),
        (RIGHT, CONFIRM, 0),
    ],
    ids=["out of range", "after a right answer"],
)
def test_a_bad_mix_up_pick_is_sent_back_for_repair(
    grade: Grade | None, explanation: str, misconception: int
) -> None:
    graded = grade or wrong_grade()
    fixed = feedback_reply(explanation, None)
    verified, fake, records = tutor(feedback_reply(explanation, misconception), fixed)

    feedback = verified.feedback(PACK, graded)

    assert records[0].reasons == ("misconception",)
    assert "- misconception:" in fake.requests[1].prompt
    assert feedback.source == "fake-model (repaired)" and feedback.misconception is None


def test_a_value_written_out_is_turned_back_into_its_slot_before_checking() -> None:
    player = VIEW.context["player"].display
    verified, _, records = tutor(json.dumps({"text": f"{player} is on the ball. Where now?"}))

    assert verified.question(VIEW).text == "{player} is on the ball. Where now?"
    assert records[0].passed


def test_each_fallback_is_reported_with_its_reasons_and_a_pass_is_not() -> None:
    fake = FakeClient([BAD_QUESTION, BAD_QUESTION, GOOD_QUESTION, ModelError("timed out")])
    fallbacks: list[Fallback] = []
    verified = VerifiedTutor(
        FoundryTutor(fake), TEMPLATE, clock=Clock(0.0), on_fallback=fallbacks.append
    )

    verified.question(VIEW)  # fails twice: the template's
    verified.question(VIEW)  # passes
    verified.feedback(PACK, RIGHT)  # no reply: the template's

    assert fallbacks == [
        Fallback("question", VIEW.pack_id, VIEW.concept_name, ("hint",)),
        Fallback("feedback", PACK.pack_id, PACK.concept.name, ("no reply",)),
    ]
