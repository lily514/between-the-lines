"""Questions about the basics: restarts, offside, and fouls and cards."""

import numpy as np
import pytest

from btl.concepts.base import ConceptTag, MatchContext, match_context
from btl.concepts.foul import FoulCommitted
from btl.concepts.offside import OffsidePass, offside_line
from btl.concepts.phase import PhaseOfPlay
from btl.concepts.restart import BallOutOfPlay
from btl.learn.candidates import ASKED_WHEN, AskedWhen, Candidate
from btl.learn.knowledge import Delivery
from btl.learn.questions import (
    BOOKING_REASONS,
    OFFSIDE_NO,
    OFFSIDE_YES,
    Asks,
    Form,
    Question,
    build_question,
)
from btl.schema.ids import TeamId
from btl.schema.match import Match
from btl.schema.vocab import ActionType, ConceptId, Result
from tests.fixtures.concepts import fouled, out_and_restart, pass_to
from tests.fixtures.learning import (
    FOULS,
    OFFSIDE,
    RESTARTS,
    designed_with_candidates,
    threat_model,
)
from tests.fixtures.matches import AWAY, HOME

LIVE, DEFERRED = Delivery.LIVE, Delivery.DEFERRED
KEYS = {ConceptId.RESTART: RESTARTS, ConceptId.OFFSIDE: OFFSIDE, ConceptId.FOUL: FOULS}


def only_tag(match: Match, concept: ConceptId) -> tuple[MatchContext, Candidate]:
    ctx = match_context(match)
    detector = {
        ConceptId.RESTART: BallOutOfPlay(),
        ConceptId.OFFSIDE: OffsidePass(),
        ConceptId.FOUL: FoulCommitted(),
    }[concept]
    (tag,) = detector.detect(ctx)
    return ctx, as_candidate(tag)


def as_candidate(tag: ConceptTag) -> Candidate:
    assert tag.difficulty is not None
    asked_when = ASKED_WHEN[tag.concept](tag) if tag.concept in ASKED_WHEN else AskedWhen.IN_PLAY
    return Candidate(
        KEYS[tag.concept], tag, tag.difficulty, PhaseOfPlay.SETTLED, 1, 0.0, asked_when
    )


def ask(ctx: MatchContext, candidate: Candidate, level: int, delivery: Delivery = LIVE) -> Question:
    question = build_question(
        candidate, level, delivery, ctx, threat_model(), np.random.default_rng(0)
    )
    assert question is not None
    return question


def answer(question: Question) -> str:
    return next(o.label for o in question.options if o.correct)


@pytest.mark.parametrize(
    ("out", "restart", "right"),
    [
        # {team} made the last action, {opponent} is the other team.
        (
            (HOME, ActionType.PASS, Result.FAIL),
            (AWAY, ActionType.THROW_IN, (60, 0)),
            "Throw-in to {opponent}",
        ),
        (
            (HOME, ActionType.PASS, Result.FAIL),
            (HOME, ActionType.THROW_IN, (60, 68)),
            "Throw-in to {team}",
        ),
        (
            (HOME, ActionType.SHOT, Result.FAIL),
            (AWAY, ActionType.GOALKICK, (99.5, 34)),
            "Goal kick to {opponent}",
        ),
        (
            (HOME, ActionType.CROSS, Result.FAIL),
            (HOME, ActionType.CORNER_CROSSED, (105, 0)),
            "Corner to {team}",
        ),
    ],
)
def test_a_restart_question_predicts_the_restart_and_who_takes_it(
    out: tuple[TeamId, ActionType, Result],
    restart: tuple[TeamId, ActionType, tuple[float, float]],
    right: str,
) -> None:
    ctx, candidate = only_tag(out_and_restart(out, restart), ConceptId.RESTART)

    question = ask(ctx, candidate, 1)

    assert question.form is Form.PREDICT
    assert question.asks is Asks.WHAT_RESTART
    assert answer(question) == right
    assert len({o.label for o in question.options}) == 3


def test_an_offside_call_is_predicted_live_and_identified_later() -> None:
    ctx, candidate = only_tag(pass_to((83, 30), result=Result.OFFSIDE), ConceptId.OFFSIDE)

    live, later = ask(ctx, candidate, 1), ask(ctx, candidate, 3, DEFERRED)

    assert (live.form, live.asks) == (Form.PREDICT, Asks.FLAG_OR_NOT)
    assert (later.form, later.asks) == (Form.IDENTIFY, Asks.WAS_IT_OFFSIDE)
    assert answer(live) == answer(later) == OFFSIDE_YES


@pytest.mark.parametrize(
    ("receiver", "start", "end", "reason"),
    [
        ((77, 30), (70, 34), (90, 30), "the second-last defender"),
        ((85, 30), (88, 34), (95, 30), "the ball"),
    ],
)
def test_an_onside_answer_gives_the_true_reason(
    receiver: tuple[float, float],
    start: tuple[float, float],
    end: tuple[float, float],
    reason: str,
) -> None:
    ctx, candidate = only_tag(pass_to(receiver, start=start, end=end), ConceptId.OFFSIDE)

    assert answer(ask(ctx, candidate, 1)) == OFFSIDE_NO[reason]


def test_a_foul_is_predicted_at_the_stoppage_and_a_booking_explained_there() -> None:
    ctx, plain = only_tag(fouled((60, 34)), ConceptId.FOUL)
    ctx_booked, booked = only_tag(fouled((60, 34), result=Result.YELLOW_CARD), ConceptId.FOUL)
    ctx_box, in_box = only_tag(fouled((95, 30), then=ActionType.SHOT_PENALTY), ConceptId.FOUL)

    assert answer(ask(ctx, plain, 1)) == "Free kick to {opponent}"
    assert answer(ask(ctx_box, in_box, 1)) == "Penalty to {opponent}"
    assert ask(ctx_booked, booked, 1).asks is Asks.AFTER_THE_FOUL
    why = ask(ctx_booked, booked, 2)
    assert (why.form, why.asks) == (Form.IDENTIFY, Asks.WHY_BOOKED)
    assert answer(why) == BOOKING_REASONS[0]


def test_advantage_is_only_asked_about_at_level_three() -> None:
    ctx, candidate = only_tag(fouled((60, 34), then=ActionType.PASS), ConceptId.FOUL)

    assert candidate.asked_when is AskedWhen.AFTERWARDS
    for level in (1, 2):
        assert (
            build_question(
                candidate, level, DEFERRED, ctx, threat_model(), np.random.default_rng(0)
            )
            is None
        )
    assert ask(ctx, candidate, 3, DEFERRED).asks is Asks.WHY_PLAY_ON


@pytest.mark.parametrize("seed", range(40))
def test_every_level_builds_a_fair_question_about_the_basics(seed: int) -> None:
    _, ctx, candidates = designed_with_candidates(seed)
    built = 0
    for candidate in (c for c in candidates if c.tag.concept in KEYS):
        for level in (1, 2, 3):
            for delivery in (LIVE, DEFERRED):
                question = build_question(
                    candidate, level, delivery, ctx, threat_model(), np.random.default_rng(seed)
                )
                if question is None:
                    continue
                built += 1
                assert len(question.options) == 3
                assert sum(o.correct for o in question.options) == 1
                assert len({(o.label, o.target) for o in question.options}) == 3
                if question.asks is Asks.WHO_IS_OFFSIDE:
                    event = ctx.events[candidate.tag.action_id]
                    snapshot = ctx.snapshot(event.action_id)
                    assert snapshot is not None
                    line = offside_line(snapshot, event)
                    assert line is not None
                    for option in question.options:
                        assert option.end is not None
                        assert (option.end[0] > line) == option.correct
    assert built > 0
