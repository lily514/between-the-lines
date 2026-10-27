from collections import Counter
from dataclasses import replace

import numpy as np
import pytest

from btl.concepts.base import MatchContext, match_context
from btl.concepts.line_breaking import LineBreakingPass
from btl.concepts.phase import PhaseOfPlay
from btl.learn.candidates import Candidate
from btl.learn.concept_map import load_concept_map
from btl.learn.knowledge import Delivery
from btl.learn.questions import (
    Asks,
    Form,
    Question,
    active_concepts,
    build_question,
    question_form,
)
from btl.schema.ids import PlayerId
from btl.schema.match import Match
from btl.schema.snapshot import PlayerSlot, Positions
from btl.schema.vocab import ConceptId
from btl.value.xt import CELLS_ACROSS, CELLS_ALONG, FitInfo, ThreatModel
from tests.fixtures.concepts import MIDFIELD_LINE
from tests.fixtures.learning import LINE_BREAKING, designed_with_candidates, threat_model
from tests.fixtures.matches import AWAY, GAME, HOME, HOME_MIDFIELDER, make_event

LIVE, DEFERRED = Delivery.LIVE, Delivery.DEFERRED
# A threat grid that grows by 0.01 per column along the pitch, the same across it.
RAMP = ThreatModel(
    grid=tuple(tuple(column / 100 for column in range(CELLS_ALONG)) for _ in range(CELLS_ACROSS)),
    fitted_on=FitInfo(matches=0, seed=0, league_seed=0, actions=0),
)
RECEIVER, BACK, WIDE, SHORT = PlayerId(31), PlayerId(32), PlayerId(33), PlayerId(34)


def pass_picture() -> tuple[MatchContext, Candidate]:
    """#11 passes from (40, 34) to (60, 34), through a 12 m gap in a midfield line at x = 50.

    Teammates: the receiver at (61, 34), one behind at (30, 34), one wide at (40, 50) and one
    a short way forward at (47, 20), still in front of the line.
    """
    teammates = {RECEIVER: (61, 34), BACK: (30, 34), WIDE: (40, 50), SHORT: (47, 20)}
    defenders = tuple(PlayerId(40 + i) for i in range(len(MIDFIELD_LINE)))
    slots = (
        PlayerSlot(HOME_MIDFIELDER, HOME, is_goalkeeper=False),
        *(PlayerSlot(player, HOME, is_goalkeeper=False) for player in teammates),
        *(PlayerSlot(player, AWAY, is_goalkeeper=False) for player in defenders),
    )
    xy = np.array([[(40, 34), *teammates.values(), *MIDFIELD_LINE]], dtype=np.float64)
    event = make_event(0, HOME, HOME_MIDFIELDER, (40, 34), (60, 34))
    match = Match(GAME, HOME, AWAY, (event,), Positions(slots=slots, xy=xy))
    ctx = match_context(match, (0.03,))
    (tag,) = LineBreakingPass().detect(ctx)
    assert tag.difficulty is not None
    candidate = Candidate(LINE_BREAKING, tag, tag.difficulty, PhaseOfPlay.SETTLED, 1, 0.0)
    return ctx, candidate


def ask(level: int, delivery: Delivery = LIVE, seed: int = 0) -> Question:
    ctx, candidate = pass_picture()
    question = build_question(candidate, level, delivery, ctx, RAMP, np.random.default_rng(seed))
    assert question is not None
    return question


def by_target(question: Question) -> dict[PlayerId | None, dict[str, float | str]]:
    return {option.target: dict(option.facts) for option in question.options}


def test_level_two_offers_the_pass_back_and_the_pass_sideways() -> None:
    question = ask(2)

    assert question.form is Form.PREDICT and question.asks is Asks.WHERE_TO_PASS
    assert by_target(question) == {
        RECEIVER: {
            "lines_broken": 1,
            "gap_m": 12.0,
            "threat_added": pytest.approx(0.03),
            "distance_m": 20.0,
            "direction": "forward",
        },
        BACK: {
            "lines_broken": 0,
            "gap_m": 0.0,
            "threat_added": pytest.approx(-0.02),
            "distance_m": 10.0,
            "direction": "backward",
        },
        WIDE: {
            "lines_broken": 0,
            "gap_m": 0.0,
            "threat_added": 0.0,
            "distance_m": 16.0,
            "direction": "sideways",
        },
    }
    assert {option.target for option in question.options if option.correct} == {RECEIVER}


def test_level_three_offers_the_closest_alternatives() -> None:
    question = ask(3)

    # The short forward pass and the sideways one add the most threat without breaking a line.
    assert set(by_target(question)) == {RECEIVER, SHORT, WIDE}


def test_without_two_fair_alternatives_there_is_no_predict_question() -> None:
    ctx, candidate = pass_picture()
    positions = ctx.match.positions
    assert positions is not None
    # Keep the passer and the receiver; drop the three other teammates.
    only_the_receiver = Positions(
        slots=positions.slots[:2] + positions.slots[5:],
        xy=np.delete(positions.xy, [2, 3, 4], axis=1),
    )
    alone = match_context(Match(GAME, HOME, AWAY, ctx.match.events, only_the_receiver), (0.03,))

    assert build_question(candidate, 2, LIVE, alone, RAMP, np.random.default_rng(0)) is None


def test_pass_options_carry_a_slot_for_the_receivers_name() -> None:
    assert {option.label for option in ask(2).options} == {"Pass to {target}"}


def test_level_one_asks_how_many_lines_the_pass_broke() -> None:
    question = ask(1)

    assert question.form is Form.IDENTIFY and question.asks is Asks.LINES_BROKEN
    assert {o.label: o.correct for o in question.options} == {
        "None": False,
        "One": True,
        "Two": False,
    }


def test_deferred_line_breaks_are_identified_never_predicted() -> None:
    coarse, narrow = ask(2, DEFERRED), ask(3, DEFERRED)

    assert coarse.asks is Asks.GAP_WIDTH and narrow.asks is Asks.GAP_WIDTH
    assert {o.label: o.correct for o in coarse.options} == {
        "Under 8 m": False,
        "8 to 14 m": True,
        "14 m or more": False,
    }
    narrow_ranges = sorted((float(o.facts["from"]), float(o.facts["to"])) for o in narrow.options)
    assert all(high - low == 3 for low, high in narrow_ranges)
    assert [o.correct for o in narrow.options].count(True) == 1
    (right,) = [o for o in narrow.options if o.correct]
    assert float(right.facts["from"]) <= 12.0 < float(right.facts["to"])


def test_the_true_narrow_range_is_not_always_in_the_same_place() -> None:
    places = Counter(
        sorted(ask(3, DEFERRED, seed).options, key=lambda o: float(o.facts["from"])).index(
            next(o for o in ask(3, DEFERRED, seed).options if o.correct)
        )
        for seed in range(30)
    )

    assert set(places) == {0, 1, 2}


def test_counter_presses_are_never_predicted() -> None:
    _, line_break = pass_picture()
    press = replace(line_break, tag=replace(line_break.tag, concept=ConceptId.COUNTER_PRESS))

    for level in (1, 2, 3):
        for delivery in Delivery:
            assert question_form(press, level, delivery) is Form.IDENTIFY
    assert question_form(line_break, 1, LIVE) is Form.IDENTIFY
    assert question_form(line_break, 2, LIVE) is Form.PREDICT
    assert question_form(line_break, 3, DEFERRED) is Form.IDENTIFY


def test_options_are_shuffled_but_the_same_seed_gives_the_same_order() -> None:
    orders = {tuple(o.target for o in ask(2, seed=seed).options) for seed in range(20)}

    assert len(orders) > 1
    assert ask(2, seed=5) == ask(2, seed=5)
    assert [o.key for o in ask(2).options] == ["A", "B", "C"]


def test_the_active_concepts_are_those_with_questions() -> None:
    assert active_concepts(load_concept_map()) == (
        "tackles",
        "restarts",
        "offside",
        "fouls_and_cards",
        "line_breaking_pass",
        "counter_press",
    )


@pytest.mark.parametrize("seed", range(40))
def test_in_simulated_play_the_right_pass_breaks_most_and_adds_most(seed: int) -> None:
    _, ctx, candidates = designed_with_candidates(seed)
    passes = [c for c in candidates if c.tag.concept is ConceptId.LINE_BREAKING_PASS]
    rng = np.random.default_rng(seed)

    for candidate in passes[::5]:
        for level in (2, 3):
            question = build_question(candidate, level, LIVE, ctx, threat_model(), rng)
            assert question is not None
            (right,) = [o for o in question.options if o.correct]
            for wrong in (o for o in question.options if not o.correct):
                assert float(wrong.facts["lines_broken"]) < float(right.facts["lines_broken"])
                assert float(wrong.facts["threat_added"]) <= float(right.facts["threat_added"])
            assert len({o.target for o in question.options}) == 3


def test_level_three_alternatives_are_closer_to_the_answer_than_level_two() -> None:
    gaps: dict[int, list[float]] = {2: [], 3: []}
    for seed in range(10):
        _, ctx, candidates = designed_with_candidates(seed)
        for candidate in candidates[::5]:
            if candidate.tag.concept is not ConceptId.LINE_BREAKING_PASS:
                continue
            for level in (2, 3):
                question = build_question(
                    candidate, level, LIVE, ctx, threat_model(), np.random.default_rng(0)
                )
                assert question is not None
                (right,) = [o for o in question.options if o.correct]
                gaps[level] += [
                    float(right.facts["threat_added"]) - float(o.facts["threat_added"])
                    for o in question.options
                    if not o.correct
                ]

    assert np.mean(gaps[3]) < np.mean(gaps[2])


@pytest.mark.parametrize("level", [1, 2, 3])
def test_every_simulated_counter_press_gets_a_question(level: int) -> None:
    _, ctx, candidates = designed_with_candidates(0)
    presses = [c for c in candidates if c.tag.concept is ConceptId.COUNTER_PRESS]

    for candidate in presses:
        question = build_question(
            candidate, level, DEFERRED, ctx, threat_model(), np.random.default_rng(0)
        )
        assert question is not None
        assert [o.correct for o in question.options].count(True) == 1
