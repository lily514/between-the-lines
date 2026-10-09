import ast
from pathlib import Path

import numpy as np
import pytest

from btl.concepts.phase import PhaseOfPlay
from btl.league.league import generate_league
from btl.learn.concept_map import load_concept_map
from btl.learn.evidence import Delivered, EvidencePack, build_pack, question_view
from btl.learn.grader import ChoiceAnswer, ChoiceGrader, Grade
from btl.learn.knowledge import Delivery
from btl.learn.questions import build_question
from btl.schema.vocab import ConceptId
from btl.tutor.slots import (
    SlotError,
    feedback_values,
    fill,
    question_values,
    slot_names,
)
from btl.tutor.templates import ASKING, TemplateTutor
from tests.fixtures.learning import designed_with_candidates, threat_model

TUTOR = TemplateTutor()
FORBIDDEN = ("btl.sim", "btl.value", "btl.concepts", "btl.plant")


def packs(seed: int) -> list[EvidencePack]:
    """A few moments of each concept, at every level, asked live and at a stoppage or break."""
    _, ctx, candidates = designed_with_candidates(seed)
    league = generate_league(np.random.default_rng(0))
    built: list[EvidencePack] = []
    for concept in (ConceptId.LINE_BREAKING_PASS, ConceptId.COUNTER_PRESS):
        for candidate in [c for c in candidates if c.tag.concept is concept][:2]:
            for level in (1, 2, 3):
                for delivered in (
                    Delivered(
                        Delivery.LIVE, candidate.period_id, candidate.time_seconds, candidate.phase
                    ),
                    Delivered(Delivery.DEFERRED, 1, 2000.0, PhaseOfPlay.DEAD_BALL, "goal kick"),
                    Delivered(Delivery.DEFERRED, 1, 2700.0, PhaseOfPlay.HALF_TIME),
                    Delivered(Delivery.DEFERRED, 2, 2700.0, PhaseOfPlay.FULL_TIME),
                ):
                    question = build_question(
                        candidate,
                        level,
                        delivered.delivery,
                        ctx,
                        threat_model(),
                        np.random.default_rng(level),
                    )
                    assert question is not None
                    built.append(
                        build_pack(
                            question, delivered, ctx, threat_model(), league, load_concept_map()
                        )
                    )
    return built


@pytest.mark.parametrize("seed", range(3))
def test_every_question_fills_from_the_question_view_alone(seed: int) -> None:
    for pack in packs(seed):
        view = question_view(pack)

        text = fill(TUTOR.question(view).text, question_values(view))

        assert "{" not in text and text.endswith("?")


@pytest.mark.parametrize("seed", range(3))
def test_every_feedback_fills_whichever_option_was_picked(seed: int) -> None:
    for pack in packs(seed):
        for option in pack.options:
            grade = ChoiceGrader().grade(pack, ChoiceAnswer(option.key))

            feedback = TUTOR.feedback(pack, grade)
            text = fill(feedback.explanation, feedback_values(pack, option.key))

            assert "{" not in text
            assert feedback.source == "template"
            assert ("mix-up" in text) is not grade.correct


def test_the_explanation_follows_the_viewers_level() -> None:
    by_level = {
        pack.level: TUTOR.feedback(pack, Grade(True, pack.correct_key)).explanation
        for pack in packs(0)
        if pack.concept.key == "counter_press"
    }

    assert len(set(by_level.values())) == 3
    assert by_level[1].startswith("After losing the ball")


def test_a_question_asked_later_says_when_it_happened() -> None:
    texts = {
        (pack.timing.delivered_phase, pack.timing.delivery): TUTOR.question(
            question_view(pack)
        ).text
        for pack in packs(0)
    }

    assert texts[PhaseOfPlay.DEAD_BALL, Delivery.DEFERRED].startswith(
        "Play has stopped for a {restart}. Back at {occurred_at}: "
    )
    assert texts[PhaseOfPlay.HALF_TIME, Delivery.DEFERRED].startswith("Half-time.")
    assert texts[PhaseOfPlay.FULL_TIME, Delivery.DEFERRED].startswith("Full time.")
    live = [t for (_, delivery), t in texts.items() if delivery is Delivery.LIVE]
    assert all(not t.startswith(("Play has stopped", "Half-time", "Full time")) for t in live)


def test_question_wording_never_names_an_outcome() -> None:
    outcome_names = {"lines_broken", "gap_m", "threat_added", "seconds_to_regain", "receiver"}

    for wording in ASKING.values():
        assert not slot_names(wording) & outcome_names


def test_a_slot_with_nothing_to_fill_it_is_an_error() -> None:
    with pytest.raises(SlotError, match=r"\{answer\}"):
        fill("It was {answer}.", {"team": "Kendal Kestrels"})


def test_the_verdict_is_written_by_code() -> None:
    assert Grade(True, "A").verdict == "Right read."
    assert Grade(False, "B").verdict == "Good instinct, not this one."


def test_the_grader_checks_the_key_against_the_pack() -> None:
    pack = packs(0)[0]
    wrong = next(o.key for o in pack.options if not o.correct)

    assert ChoiceGrader().grade(pack, ChoiceAnswer(pack.correct_key)).correct
    assert not ChoiceGrader().grade(pack, ChoiceAnswer(wrong)).correct
    with pytest.raises(ValueError, match="no option 'D'"):
        ChoiceGrader().grade(pack, ChoiceAnswer("D"))


def test_the_tutor_never_imports_what_computes_numbers() -> None:
    tutor = Path(__file__).parents[2] / "src" / "btl" / "tutor"
    for module in tutor.glob("*.py"):
        tree = ast.parse(module.read_text())
        imported = [
            name
            for node in ast.walk(tree)
            for name in (
                [node.module or ""]
                if isinstance(node, ast.ImportFrom)
                else [alias.name for alias in node.names]
                if isinstance(node, ast.Import)
                else []
            )
        ]
        assert not [name for name in imported if name.startswith(FORBIDDEN)], module.name
