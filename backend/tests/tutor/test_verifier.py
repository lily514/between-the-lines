"""The Verifier's contract: each bad wording is rejected for exactly its own reason, and the
template Tutor's wording always passes."""

import pytest

from btl.learn.evidence import EvidencePack, PackOption, question_view
from btl.learn.grader import Grade
from btl.learn.questions import Asks
from btl.tutor.templates import TemplateTutor
from btl.tutor.verifier import (
    CHECKS,
    MAX_QUESTION_WORDS,
    FeedbackText,
    verify_feedback,
    verify_question,
)
from tests.fixtures.packs import every_kind, first_of

TUTOR = TemplateTutor()
PASS_QUESTION = "{player} has the ball for {team}. Where should the pass go?"
RESTART_QUESTION = (
    "The ball has gone over the {out_line}, last touched by {last_touch_team}. What happens now?"
)
COMPARE = (
    "The pass to {answer.target} went through {answer.lines_broken} lines and changed the chance "
    "of scoring by {answer.threat_added}, against {chosen.threat_added} for {chosen.target}."
)
TAKEAWAY = "Look for the pass that goes through a line, not around it."
# Fifteen words, none of them repeated back to back however often the sentence is.
LONG_SENTENCE = " Look up, scan the pitch and pick the pass that hurts the defending side."


def pass_pack() -> EvidencePack:
    return first_of(Asks.WHERE_TO_PASS)


def worse_pick(pack: EvidencePack) -> PackOption:
    """A wrong option whose pass added less threat than the right one."""
    best = next(option for option in pack.options if option.correct)
    worse = [
        option
        for option in pack.options
        if not option.correct
        and float(option.outcome["threat_added"].value) < float(best.outcome["threat_added"].value)
    ]
    return worse[0]


def restart_pack_with_a_corner() -> EvidencePack:
    for seed in range(40):
        for pack in every_kind(seed):
            corner = any(option.label.startswith("Corner") for option in pack.options)
            if pack.asks is Asks.WHAT_RESTART and corner:
                return pack
    raise LookupError("no restart question with a corner option")


def question_reasons(text: str, pack: EvidencePack) -> tuple[str, ...]:
    return verify_question(text, question_view(pack)).reasons


def wrong_pass_reasons(explanation: str, takeaway: str = TAKEAWAY, misconception: int | None = 0):
    pack = pass_pack()
    grade = Grade(correct=False, chosen=worse_pick(pack).key)
    return verify_feedback(FeedbackText(explanation, takeaway, misconception), pack, grade).reasons


def test_good_wording_passes() -> None:
    assert question_reasons(PASS_QUESTION, pass_pack()) == ()
    assert question_reasons(RESTART_QUESTION, restart_pack_with_a_corner()) == ()
    assert wrong_pass_reasons(COMPARE) == ()


@pytest.mark.parametrize(
    ("text", "reason"),
    [
        ("{player} has the ball for {team}. Can they find {receiver}?", "slots"),
        ("{player} has the ball for {team} with 3 defenders close. Where now?", "bare_number"),
        ("{player} has the ball for {team} with two defenders close. Where now?", "bare_number"),
        ("{player} has the ball for {team} against Gortham Rovers. Where now?", "names"),
        ("{player} has the ball for {team}. What are the odds of a pass forward?", "vocabulary"),
        ("{player} has the ball for {team}. Should the pass go to {B.label}?", "hint"),
        ("{player} has the ball for {team}. Is option B the pass?", "hint"),
        ("{player} has the ball for {team}. " + LONG_SENTENCE * 4, "length"),
    ],
    ids=[
        "an outcome slot",
        "a digit",
        "a number word",
        "an invented club",
        "betting",
        "an option slot",
        "an option letter",
        "too long",
    ],
)
def test_a_bad_question_is_rejected_for_exactly_its_reason(text: str, reason: str) -> None:
    assert question_reasons(text, pass_pack()) == (reason,)


def test_a_question_that_names_an_option_s_word_gives_a_hint() -> None:
    pack = restart_pack_with_a_corner()
    text = (
        "The ball has gone over the {out_line}, last touched by {last_touch_team}. Is it a corner?"
    )

    assert question_reasons(text, pack) == ("hint",)


def test_football_phrases_that_look_like_numbers_pass() -> None:
    text = (
        "{player} has the ball for {team} in their own half, just before half-time. "
        "Where should the pass go?"
    )

    assert question_reasons(text, pass_pack()) == ()


@pytest.mark.parametrize(
    ("explanation", "reason"),
    [
        (COMPARE + " {not_a_fact}", "slots"),
        (COMPARE + " It went through two lines.", "bare_number"),
        (COMPARE + " It is what Gortham do.", "names"),
        (COMPARE + " It was a safe bet.", "vocabulary"),
        ("Correct: " + COMPARE, "verdict"),
        ("It went through {lines_broken} lines, against {chosen.threat_added}.", "grounded"),
        ("The answer was {answer}, not {chosen}.", "grounded"),
        ("The pass to {answer.target} changed the chance by {answer.threat_added}.", "grounded"),
        (COMPARE + " {chosen.threat_added} is more than {answer.threat_added}.", "comparison"),
        (COMPARE + " {answer.threat_added} is better than {chosen.threat_added}.", "comparison"),
        (COMPARE + LONG_SENTENCE * 6, "length"),
        (COMPARE + " It went into the gap the gap.", "echo"),
    ],
    ids=[
        "an unknown slot",
        "a number word",
        "an invented club",
        "betting",
        "a verdict",
        "no answer",
        "no outcome",
        "no chosen fact after a wrong pass",
        "a comparison the wrong way round",
        "a comparison code can't check",
        "too long",
        "words said twice",
    ],
)
def test_bad_feedback_is_rejected_for_exactly_its_reason(explanation: str, reason: str) -> None:
    assert wrong_pass_reasons(explanation) == (reason,)


def test_a_comparison_the_facts_bear_out_passes() -> None:
    assert (
        wrong_pass_reasons(COMPARE + " {answer.threat_added} is more than {chosen.threat_added}.")
        == ()
    )


def test_the_takeaway_is_one_short_sentence() -> None:
    assert wrong_pass_reasons(COMPARE, takeaway="Look for the gap. Then pass.") == ("length",)
    assert wrong_pass_reasons(COMPARE, takeaway=LONG_SENTENCE * 2) == ("length",)


def test_a_misconception_must_exist_and_only_follows_a_wrong_answer() -> None:
    pack = pass_pack()
    count = len(pack.concept.misconceptions)
    right = Grade(correct=True, chosen=pack.correct_key)
    confirm = "The pass to {answer.target} went through {answer.lines_broken} lines."

    assert wrong_pass_reasons(COMPARE, misconception=count) == ("misconception",)
    assert wrong_pass_reasons(COMPARE, misconception=None) == ()
    assert verify_feedback(FeedbackText(confirm, TAKEAWAY, 0), pack, right).reasons == (
        "misconception",
    )


def test_a_value_written_out_beside_its_slot_is_an_echo() -> None:
    pack = restart_pack_with_a_corner()
    grade = Grade(correct=False, chosen=next(o.key for o in pack.options if not o.correct))
    team = pack.outcome["restart_team"].display
    said_twice = FeedbackText(f"The answer was {{answer}}, to {{restart_team}} ({team}).", "x", 0)

    assert verify_feedback(said_twice, pack, grade).reasons == ("echo",)


def test_a_whole_sentence_fact_inside_another_sentence_is_an_echo() -> None:
    pack = first_of(Asks.AFTER_THE_FOUL)
    wrong = next(o for o in pack.options if not o.correct)
    grade = Grade(correct=False, chosen=wrong.key)
    split = FeedbackText("The answer was {answer}, since {foul_outcome} and that was all.", "x", 0)
    whole = FeedbackText("The answer was {answer}. {foul_outcome}", "x", 0)

    assert verify_feedback(split, pack, grade).reasons == ("echo",)
    assert verify_feedback(whole, pack, grade).reasons == ()


def test_every_check_has_a_case_that_fails_it() -> None:
    covered = {"slots", "bare_number", "names", "vocabulary", "hint", "verdict", "grounded"}
    covered |= {"comparison", "misconception", "echo", "length"}

    assert covered == set(CHECKS)
    assert len(PASS_QUESTION.split()) < MAX_QUESTION_WORDS


@pytest.mark.parametrize("seed", range(40))
def test_the_template_tutor_s_wording_passes_every_check(seed: int) -> None:
    for pack in every_kind(seed):
        view = question_view(pack)
        question = TUTOR.question(view).text
        assert verify_question(question, view).failures == (), (pack.asks, question)
        for option in pack.options:
            grade = Grade(correct=option.correct, chosen=option.key)
            feedback = TUTOR.feedback(pack, grade)
            index = (
                None
                if feedback.misconception is None
                else pack.concept.misconceptions.index(feedback.misconception)
            )
            text = FeedbackText(feedback.explanation, feedback.takeaway, index)
            assert verify_feedback(text, pack, grade).failures == (), (pack.asks, feedback)


def test_braces_that_are_not_a_slot_are_rejected() -> None:
    text = "Was he past the {second-last defender}? {player} has the ball for {team}."

    assert question_reasons(text, pass_pack()) == ("slots",)


def test_a_sentence_may_start_after_a_whole_sentence_fact() -> None:
    pack = first_of(Asks.AFTER_THE_FOUL)
    grade = Grade(correct=False, chosen=next(o.key for o in pack.options if not o.correct))
    text = FeedbackText(
        "The answer was {answer}. {booking_note} If play had gone on, fine.", "x", 0
    )

    assert verify_feedback(text, pack, grade).reasons == ()
