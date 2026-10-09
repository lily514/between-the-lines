import json
import re
from typing import cast

import numpy as np
import pytest

from btl.concepts.phase import PhaseOfPlay
from btl.league.league import League, generate_league
from btl.learn.candidates import Candidate
from btl.learn.concept_map import load_concept_map
from btl.learn.evidence import (
    COUNT_WORDS,
    Delivered,
    EvidencePack,
    build_pack,
    question_view,
    to_json,
)
from btl.learn.knowledge import Delivery
from btl.learn.questions import Asks, Form, active_concepts, build_question
from btl.schema.frames import seen_by
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
ASKED_LATER = Delivered(Delivery.DEFERRED, 1, 2000.0, PhaseOfPlay.DEAD_BALL, "goal kick")


def league() -> League:
    return generate_league(np.random.default_rng(0))


def pack_for(
    candidate: Candidate, level: int, delivery: Delivery, seed: int = 0, rng_seed: int = 0
) -> EvidencePack:
    _, ctx, _ = designed_with_candidates(seed)
    question = build_question(
        candidate, level, delivery, ctx, threat_model(), np.random.default_rng(rng_seed)
    )
    assert question is not None
    delivered = Delivered(delivery, candidate.period_id, candidate.time_seconds, candidate.phase)
    if delivery is Delivery.DEFERRED:
        delivered = ASKED_LATER
    return build_pack(question, delivered, ctx, threat_model(), league(), load_concept_map())


def sample_packs(seed: int) -> list[EvidencePack]:
    """Every form: a few candidates of each concept, at each level, live and deferred."""
    _, _, candidates = designed_with_candidates(seed)
    packs: list[EvidencePack] = []
    for concept in (ConceptId.LINE_BREAKING_PASS, ConceptId.COUNTER_PRESS):
        for candidate in [c for c in candidates if c.tag.concept is concept][:3]:
            for level in (1, 2, 3):
                for delivery in Delivery:
                    packs.append(pack_for(candidate, level, delivery, seed))
    return packs


def keys_in(value: object) -> set[str]:
    """Every key at any depth of parsed JSON."""
    if isinstance(value, dict):
        mapping = cast(dict[str, object], value)
        return set(mapping) | {key for child in mapping.values() for key in keys_in(child)}
    if isinstance(value, list):
        return {key for item in cast(list[object], value) for key in keys_in(item)}
    return set()


def first_line_break(seed: int = 0) -> Candidate:
    _, _, candidates = designed_with_candidates(seed)
    return next(c for c in candidates if c.tag.concept is ConceptId.LINE_BREAKING_PASS)


def test_the_same_question_always_gives_the_same_pack_and_id() -> None:
    candidate = first_line_break()

    once = pack_for(candidate, 2, Delivery.LIVE)
    again = pack_for(candidate, 2, Delivery.LIVE)

    assert once == again and to_json(once) == to_json(again)
    assert re.fullmatch(r"[0-9a-f]{16}", once.pack_id)
    assert pack_for(candidate, 3, Delivery.LIVE).pack_id != once.pack_id


@pytest.mark.parametrize("seed", range(3))
def test_a_question_view_never_holds_the_answer_or_an_outcome(seed: int) -> None:
    for pack in sample_packs(seed):
        view = json.loads(to_json(question_view(pack)))
        names = keys_in(view)

        assert not names & OUTCOME_NAMES, pack.asks
        assert not names & {"correct", "correct_key", "outcome", "reveal_path"}
        assert all("{" not in option["label"] for option in view["options"])


@pytest.mark.parametrize("seed", range(3))
def test_every_active_concept_gets_every_evidence_field_its_text_needs(seed: int) -> None:
    concept_map = load_concept_map()
    packs = sample_packs(seed)

    for key in active_concepts(concept_map):
        fields = set(concept_map.concept(key).evidence_fields)
        for pack in (p for p in packs if p.concept.key == key):
            assert fields <= set(pack.context) | set(pack.outcome), (key, pack.asks)


@pytest.mark.parametrize("seed", range(3))
def test_every_display_agrees_with_its_value(seed: int) -> None:
    for pack in sample_packs(seed):
        facts = [*pack.context.items(), *pack.outcome.items()]
        facts += [item for o in pack.options for item in (*o.neutral.items(), *o.outcome.items())]
        for name, fact in facts:
            if isinstance(fact.value, str):
                assert fact.display == fact.value
            elif name in {"lines_broken", "pressers"}:
                assert fact.display == COUNT_WORDS[int(fact.value)]
            elif name in {"xt_before", "xt_after", "threat_added"}:
                shown = float(fact.display.rstrip("%"))
                assert shown == pytest.approx(fact.value * 100, rel=0.05, abs=0.005), name
            else:
                assert float(fact.display) == pytest.approx(fact.value, abs=0.05), name


@pytest.mark.parametrize("seed", range(3))
def test_the_right_range_contains_the_number_shown_after_answering(seed: int) -> None:
    measured = {Asks.GAP_WIDTH: "gap_m", Asks.SECONDS_TO_REGAIN: "seconds_to_regain"}
    for pack in sample_packs(seed):
        if pack.asks not in measured:
            continue
        shown = float(pack.outcome[measured[pack.asks]].display)
        (right,) = [o for o in pack.options if o.correct]
        low, _, high = right.label.rstrip(" ms").partition(" to ")
        if right.label.startswith("Under"):
            assert shown < float(right.label.split()[1])
        elif right.label.endswith("or more"):
            assert shown >= float(right.label.split()[0])
        else:
            assert float(low) <= shown < float(high)


def test_pass_options_are_named_and_only_measured_after_answering() -> None:
    pack = pack_for(first_line_break(), 2, Delivery.LIVE)

    assert all(re.fullmatch(r"Pass to #\d+ \S.*", o.label) for o in pack.options)
    assert all(set(o.neutral) == {"target", "distance_m", "direction"} for o in pack.options)
    (right,) = [o for o in pack.options if o.correct]
    assert right.key == pack.correct_key
    assert right.outcome["lines_broken"].value == pack.outcome["lines_broken"].value
    assert pack.outcome["receiver"].display in right.label


def test_a_predict_picture_stops_before_the_pass_and_an_identify_one_shows_the_play() -> None:
    candidate = first_line_break()

    predict = pack_for(candidate, 2, Delivery.LIVE)
    identify = pack_for(candidate, 2, Delivery.DEFERRED)

    assert predict.form is Form.PREDICT and predict.picture.path == ()
    assert identify.form is Form.IDENTIFY and len(identify.picture.path) >= 2
    for pack in (predict, identify):
        assert len(pack.picture.markers) == 22
        assert [m.role for m in pack.picture.markers].count("on the ball") == 1


def test_every_pack_holds_the_real_path_to_reveal_after_answering() -> None:
    candidate = first_line_break()

    predict = pack_for(candidate, 2, Delivery.LIVE)
    identify = pack_for(candidate, 2, Delivery.DEFERRED)

    assert len(predict.reveal_path) >= 2
    assert predict.reveal_path == identify.reveal_path == identify.picture.path


@pytest.mark.parametrize("seed", range(3))
def test_a_path_that_changes_hands_stays_in_the_pictures_direction(seed: int) -> None:
    match, _, candidates = designed_with_candidates(seed)
    presses = [c for c in candidates if c.tag.concept is ConceptId.COUNTER_PRESS][:5]
    assert presses

    for candidate in presses:
        pack = pack_for(candidate, 1, Delivery.DEFERRED, seed)
        team = match.events[pack.picture.action_id].team_id
        seen = seen_by(match, team).events
        first, last = candidate.tag.span
        expected = (
            *(
                (round(seen[a].start_x, 1), round(seen[a].start_y, 1))
                for a in range(first, last + 1)
            ),
            (round(seen[last].end_x, 1), round(seen[last].end_y, 1)),
        )

        assert {match.events[a].team_id for a in range(first, last + 1)} != {team}
        assert pack.reveal_path == pack.picture.path == expected


def test_each_player_says_whether_they_play_for_the_home_club() -> None:
    pack = pack_for(first_line_break(), 2, Delivery.LIVE)
    markers = pack.picture.markers

    assert sum(m.home for m in markers) == 11
    (on_ball,) = [m for m in markers if m.role == "on the ball"]
    assert on_ball.home == (pack.context["team"] == pack.context["home_team"])
    assert all(m.home == on_ball.home for m in markers if m.side == "attacking")


def test_the_timing_says_when_it_happened_and_when_it_is_asked() -> None:
    pack = pack_for(first_line_break(), 1, Delivery.DEFERRED)

    assert pack.timing.occurred_phase is first_line_break().phase
    assert pack.timing.delivered_at == "33:20"
    assert pack.timing.delivered_phase is PhaseOfPlay.DEAD_BALL
    assert pack.timing.delivery is Delivery.DEFERRED
    assert pack.timing.restart == "goal kick"


def test_counter_press_context_does_not_name_who_won_it_back() -> None:
    _, _, candidates = designed_with_candidates(0)
    press = next(c for c in candidates if c.tag.concept is ConceptId.COUNTER_PRESS)

    pack = pack_for(press, 1, Delivery.DEFERRED)

    assert "player" not in pack.context
    assert "player" in pack.outcome
