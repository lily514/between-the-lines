import json
from typing import cast

import numpy as np
import pytest

from btl.api.models import YourTeam
from btl.api.payloads import catch_up_text, question_payload, your_result
from btl.concepts.phase import PhaseOfPlay
from btl.league.league import generate_league
from btl.learn.candidates import Candidate
from btl.learn.concept_map import load_concept_map
from btl.learn.evidence import Delivered, EvidencePack, build_pack, question_view
from btl.learn.knowledge import Delivery
from btl.learn.matches import CatchUp
from btl.learn.questions import Form, build_question
from btl.learn.report import Goal
from btl.learn.selector import Prompt
from btl.learn.session import Asked
from btl.schema.ids import ActionId
from btl.schema.vocab import ConceptId
from tests.fixtures.learning import designed_with_candidates, threat_model

OUTCOME_NAMES = {
    "lines_broken",
    "gap_m",
    "xt_before",
    "xt_after",
    "threat_added",
    "receiver",
    "receiver_zone",
    "seconds_to_regain",
    "metres_from_goal",
    "pressers",
}
HIDDEN = {
    "correct",
    "correct_key",
    "outcome",
    "reveal_path",
    "reveal_line",
    "chosen",
    "explanation",
}
HOME, AWAY = generate_league(np.random.default_rng(0)).clubs[:2]
ASKED_LATER = Delivered(Delivery.DEFERRED, 1, 2000.0, PhaseOfPlay.DEAD_BALL, "goal kick")
NO_CATCH_UP = CatchUp(0, 0, None)


def asked_for(candidate: Candidate, level: int, delivery: Delivery, seed: int) -> Asked | None:
    match, ctx, _ = designed_with_candidates(seed)
    question = build_question(
        candidate, level, delivery, ctx, threat_model(), np.random.default_rng(0)
    )
    if question is None:
        return None
    delivered = Delivered(delivery, candidate.period_id, candidate.time_seconds, candidate.phase)
    if delivery is Delivery.DEFERRED:
        delivered = ASKED_LATER
    pack = build_pack(
        question,
        delivered,
        ctx,
        threat_model(),
        generate_league(np.random.default_rng(0)),
        load_concept_map(),
    )
    prompt = Prompt(candidate, level, delivered)
    return Asked(pack, question_view(pack), "Where now?", match, prompt)


def keys_in(value: object) -> set[str]:
    """Every key at any depth of parsed JSON."""
    if isinstance(value, dict):
        mapping = cast(dict[str, object], value)
        return set(mapping) | {key for child in mapping.values() for key in keys_in(child)}
    if isinstance(value, list):
        return {key for item in cast(list[object], value) for key in keys_in(item)}
    return set()


def threat_displays(pack: EvidencePack) -> set[str]:
    """Threat figures, which are distinctive enough to search for in the payload's text."""
    facts = [*pack.outcome.values()] + [f for o in pack.options for f in o.outcome.values()]
    return {fact.display for fact in facts if "%" in fact.display}


@pytest.mark.parametrize("seed", range(40))
def test_a_question_payload_never_holds_the_answer_or_an_outcome(seed: int) -> None:
    _, _, candidates = designed_with_candidates(seed)
    for concept in (ConceptId.LINE_BREAKING_PASS, ConceptId.COUNTER_PRESS):
        for candidate in [c for c in candidates if c.tag.concept is concept][:2]:
            for level in (1, 2, 3):
                for delivery in Delivery:
                    asked = asked_for(candidate, level, delivery, seed)
                    if asked is None:
                        continue
                    payload = question_payload(asked, 1, HOME, AWAY, None, NO_CATCH_UP)
                    text = payload.model_dump_json()
                    names = keys_in(json.loads(text))

                    assert not names & OUTCOME_NAMES
                    assert not names & HIDDEN
                    assert not any(display in text for display in threat_displays(asked.pack))
                    if asked.pack.form is Form.PREDICT:
                        assert payload.picture.path == []


def test_a_question_payload_says_when_the_moment_happened_and_when_it_is_asked() -> None:
    _, _, candidates = designed_with_candidates(0)
    candidate = next(c for c in candidates if c.tag.concept is ConceptId.COUNTER_PRESS)
    asked = asked_for(candidate, 1, Delivery.DEFERRED, 0)
    assert asked is not None

    payload = question_payload(asked, 2, HOME, AWAY, AWAY.team_id, NO_CATCH_UP)

    assert payload.occurred.period == candidate.period_id
    assert payload.occurred.seconds == candidate.time_seconds
    assert payload.occurred.clock == asked.pack.timing.occurred_at
    assert payload.delivered.delivery == "deferred"
    assert (payload.delivered.period, payload.delivered.seconds) == (1, 2000.0)
    assert payload.delivered.clock == "33:20"
    assert (payload.delivered.phase, payload.delivered.restart) == ("dead ball", "goal kick")
    assert (payload.match_number, payload.home, payload.away) == (2, HOME.name, AWAY.name)
    assert (payload.home_code, payload.away_code, payload.your_team) == (
        HOME.short_name,
        AWAY.short_name,
        "away",
    )


@pytest.mark.parametrize(
    ("side", "home_goals", "away_goals", "result"),
    [("home", 2, 1, "won"), ("away", 2, 1, "lost"), ("away", 0, 0, "drew"), (None, 3, 0, None)],
)
def test_the_result_is_said_from_the_viewer_s_side(
    side: YourTeam, home_goals: int, away_goals: int, result: str | None
) -> None:
    assert your_result(side, home_goals, away_goals) == result


def test_the_catch_up_names_each_goal_and_the_score() -> None:
    scored = Goal(ActionId(5), 1, 900.0, "15:00", home=False, scorer="Someone", own_goal=False)
    own = Goal(ActionId(9), 1, 1200.0, "20:00", home=True, scorer="Someone", own_goal=True)

    assert catch_up_text(CatchUp(0, 0, None), HOME, AWAY) is None
    assert catch_up_text(CatchUp(0, 0, ()), HOME, AWAY) == "No goals. It's still 0\N{EN DASH}0."
    assert catch_up_text(CatchUp(1, 1, (scored, own)), HOME, AWAY) == (
        f"{AWAY.name} scored at 15:00. {HOME.name} scored at 20:00, an own goal. "
        "It's 1\N{EN DASH}1."
    )
