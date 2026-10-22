import pytest

from btl.learn.evidence import question_view
from btl.learn.grader import Grade
from btl.learn.questions import Asks
from btl.tutor.foundry import FoundryTutor
from btl.tutor.model import FakeClient, ModelError
from btl.tutor.prompts import INSTRUCTIONS
from btl.tutor.verifier import FeedbackText
from tests.fixtures.packs import first_of

PACK = first_of(Asks.WHERE_TO_PASS)
VIEW = question_view(PACK)
WRONG = Grade(correct=False, chosen=next(o.key for o in PACK.options if not o.correct))


def test_a_question_reply_becomes_its_wording() -> None:
    fake = FakeClient(['{"text": "  {player} is on the ball for {team}. Where next?  "}'])

    worded = FoundryTutor(fake).word_question(VIEW, "plain")

    assert worded.text == "{player} is on the ball for {team}. Where next?"
    assert worded.reply.model == "fake-model"
    (request,) = fake.requests
    assert request.instructions == INSTRUCTIONS and request.schema_name == "question"


def test_a_feedback_reply_becomes_feedback_text() -> None:
    reply = (
        '{"explanation": "The answer was {answer}.", "takeaway": "Look up.", "misconception": 1}'
    )

    worded = FoundryTutor(FakeClient([reply])).word_feedback(PACK, WRONG)

    assert worded.feedback == FeedbackText("The answer was {answer}.", "Look up.", 1)


@pytest.mark.parametrize(
    "reply",
    [
        "not JSON",
        '["text"]',
        "{}",
        '{"text": "   "}',
        '{"text": 3}',
    ],
    ids=["not JSON", "not an object", "missing", "empty", "not text"],
)
def test_a_malformed_question_reply_is_a_model_error(reply: str) -> None:
    with pytest.raises(ModelError):
        FoundryTutor(FakeClient([reply])).word_question(VIEW, "plain")


@pytest.mark.parametrize(
    "misconception", ['"1"', "true", "1.5"], ids=["text", "a boolean", "a fraction"]
)
def test_a_misconception_that_isn_t_a_number_is_a_model_error(misconception: str) -> None:
    reply = f'{{"explanation": "x", "takeaway": "y", "misconception": {misconception}}}'

    with pytest.raises(ModelError, match="misconception"):
        FoundryTutor(FakeClient([reply])).word_feedback(PACK, WRONG)


def test_a_failed_call_is_passed_on() -> None:
    with pytest.raises(ModelError, match="timed out"):
        FoundryTutor(FakeClient([ModelError("timed out")])).word_question(VIEW, "plain")
