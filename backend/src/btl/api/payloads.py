"""Turning the learning loop's objects into the API's shapes.

A question payload is built from the question view and the selector's timing only, never from
the pack, so the right answer and the outcome facts can't reach the browser before the viewer
answers. The feedback payload is the whole pack.
"""

from collections.abc import Mapping

from btl.api.models import (
    Bar,
    DeliveredTime,
    FactOut,
    FeedbackOption,
    FeedbackOut,
    MarkerOut,
    MomentTime,
    Movement,
    OptionOut,
    PictureOut,
    QuestionOut,
    ThresholdsOut,
)
from btl.concepts.phase import PhaseOfPlay
from btl.learn.concept_map import Thresholds
from btl.learn.evidence import Fact, Picture
from btl.learn.knowledge import Delivery
from btl.learn.questions import Form
from btl.learn.session import Asked, Told
from btl.schema.scoreboard import clock


def question_payload(asked: Asked, match_number: int, home: str, away: str) -> QuestionOut:
    """The question as the page shows it: its view, its wording and when it is asked."""
    view, prompt = asked.view, asked.prompt
    candidate, delivered = prompt.candidate, prompt.delivered
    return QuestionOut(
        pack_id=view.pack_id,
        match_number=match_number,
        home=home,
        away=away,
        concept_name=view.concept_name,
        form="predict" if view.form is Form.PREDICT else "identify",
        asks=view.asks.value,
        level=view.level,
        text=asked.text,
        occurred=_moment(candidate.period_id, candidate.time_seconds, candidate.phase),
        delivered=DeliveredTime(
            **_moment(delivered.period_id, delivered.time_seconds, delivered.phase).model_dump(),
            delivery="live" if delivered.delivery is Delivery.LIVE else "deferred",
            restart=delivered.restart,
        ),
        context=_facts(view.context),
        options=[
            OptionOut(
                key=option.key,
                label=option.label,
                neutral=_facts(option.neutral),
                target_at=option.target_at,
            )
            for option in view.options
        ],
        picture=_picture(view.picture),
    )


def feedback_payload(
    told: Told,
    before: Mapping[str, float],
    thresholds: Thresholds,
    match_number: int,
    match_seed: int,
) -> FeedbackOut:
    """The feedback with the whole evidence pack, and how each concept's mastery moved."""
    pack, grade = told.pack, told.grade
    return FeedbackOut(
        pack_id=pack.pack_id,
        correct=grade.correct,
        chosen=grade.chosen,
        correct_key=pack.correct_key,
        verdict=told.verdict,
        explanation=told.explanation,
        takeaway=told.takeaway,
        misconception=told.misconception,
        source=told.source,
        update=told.update,
        concept_name=pack.concept.name,
        level=pack.level,
        match_number=match_number,
        action_id=pack.picture.action_id,
        match_seed=match_seed,
        context=_facts(pack.context),
        outcome=_facts(pack.outcome),
        options=[
            FeedbackOption(
                key=option.key,
                label=option.label,
                correct=option.correct,
                chosen=option.key == grade.chosen,
                neutral=_facts(option.neutral),
                outcome=_facts(option.outcome),
                target_at=option.target_at,
            )
            for option in pack.options
        ],
        picture=_picture(pack.picture),
        reveal_path=list(pack.reveal_path),
        concepts=movements(before, told.mastery),
        thresholds=thresholds_payload(thresholds),
    )


def movements(before: Mapping[str, float], after: Mapping[str, float]) -> list[Movement]:
    """Each concept's mastery before and after, in the order of ``after``."""
    return [Movement(name=name, before=before[name], after=value) for name, value in after.items()]


def bars(mastery: Mapping[str, float]) -> list[Bar]:
    """Each concept's mastery now."""
    return [Bar(name=name, value=value) for name, value in mastery.items()]


def thresholds_payload(thresholds: Thresholds) -> ThresholdsOut:
    """The knowledge model's thresholds, for the ticks on a progress bar."""
    return ThresholdsOut(unlock=thresholds.unlock, mastery=thresholds.mastery)


def _moment(period_id: int, time_seconds: float, phase: PhaseOfPlay) -> MomentTime:
    return MomentTime(
        period=period_id,
        seconds=time_seconds,
        clock=clock(period_id, time_seconds),
        phase=phase.value,
    )


def _facts(facts: Mapping[str, Fact]) -> dict[str, FactOut]:
    return {name: FactOut(value=fact.value, display=fact.display) for name, fact in facts.items()}


def _picture(picture: Picture) -> PictureOut:
    return PictureOut(
        action_id=picture.action_id,
        markers=[
            MarkerOut(
                shirt=m.shirt,
                side="attacking" if m.side == "attacking" else "defending",
                home=m.home,
                x=m.x,
                y=m.y,
                role=m.role,
            )
            for m in picture.markers
        ],
        ball=picture.ball,
        path=list(picture.path),
    )
