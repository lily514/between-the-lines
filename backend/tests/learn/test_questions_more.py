"""Questions about the concepts that joined in Milestone 5: tackles and turnovers first."""

import numpy as np
import pytest

from btl.concepts.ball_win import BallWin, WonWith
from btl.concepts.base import MatchContext, match_context
from btl.concepts.phase import PhaseOfPlay, phase_timeline
from btl.league.league import generate_league
from btl.learn.candidates import Candidate
from btl.learn.concept_map import load_concept_map
from btl.learn.evidence import build_pack
from btl.learn.knowledge import Delivery
from btl.learn.questions import (
    DEEP_WINS_ARE_JUST_AS_USEFUL,
    WHICH_THIRD,
    WHY_THE_THIRD_MATTERS,
    WON_WITH,
    Asks,
    Form,
    Question,
    build_question,
)
from btl.schema.match import Match
from btl.schema.vocab import ActionType, ConceptId
from tests.fixtures.concepts import lost_and_won_back, won_and_carried
from tests.fixtures.learning import TACKLES, designed_with_candidates, threat_model
from tests.learn.test_evidence import ASKED_LATER

DEFERRED = Delivery.DEFERRED


def ball_win(match: Match, index: int = 0) -> tuple[MatchContext, Candidate]:
    ctx = match_context(match)
    tag = BallWin().detect(ctx)[index]
    assert tag.difficulty is not None
    return ctx, Candidate(TACKLES, tag, tag.difficulty, PhaseOfPlay.TRANSITION, 1, 0.0)


def ask(ctx: MatchContext, candidate: Candidate, level: int) -> Question:
    question = build_question(
        candidate, level, DEFERRED, ctx, threat_model(), np.random.default_rng(0)
    )
    assert question is not None
    return question


def answer(question: Question) -> str:
    return next(o.label for o in question.options if o.correct)


def test_level_one_asks_how_the_ball_was_won() -> None:
    ctx, tackle = ball_win(lost_and_won_back(4, (70.0, 30.0)), index=1)
    keeper = won_and_carried(9, (3.0, 34.0), won_with=ActionType.KEEPER_SAVE)
    ctx_keeper, gathered = ball_win(keeper)

    question = ask(ctx, tackle, 1)

    assert (question.form, question.asks) == (Form.IDENTIFY, Asks.HOW_WON)
    assert answer(question) == WON_WITH[WonWith.TACKLE]
    assert {o.label for o in question.options} == {
        WON_WITH[WonWith.TACKLE],
        WON_WITH[WonWith.INTERCEPTION],
        WON_WITH[WonWith.KEEPER],
    }
    assert answer(ask(ctx_keeper, gathered, 1)) == WON_WITH[WonWith.KEEPER]


@pytest.mark.parametrize(
    ("metres", "third"), [(20.0, 0), (34.9, 0), (35.0, 1), (69.9, 1), (70.0, 2), (95.0, 2)]
)
def test_level_two_asks_which_third_and_level_three_why_it_matters(
    metres: float, third: int
) -> None:
    ctx, candidate = ball_win(won_and_carried(9, (metres, 34.0)))

    where, why = ask(ctx, candidate, 2), ask(ctx, candidate, 3)

    assert where.asks is Asks.WHERE_WON
    assert answer(where) == WHICH_THIRD[third]
    assert {o.label for o in where.options} == set(WHICH_THIRD)
    assert why.asks is Asks.WHY_WHERE_MATTERS
    assert answer(why) == WHY_THE_THIRD_MATTERS[third]
    assert DEEP_WINS_ARE_JUST_AS_USEFUL in {o.label for o in why.options}
    assert len({o.label for o in why.options}) == 3


def test_the_distractor_is_the_maps_own_misconception() -> None:
    tackles = load_concept_map().concept(TACKLES)

    assert DEEP_WINS_ARE_JUST_AS_USEFUL + "." in tackles.misconceptions


def test_a_ball_win_is_never_asked_live() -> None:
    ctx, candidate = ball_win(won_and_carried(9, (30.0, 34.0)))

    for level in (1, 2, 3):
        for delivery in Delivery:
            question = build_question(
                candidate, level, delivery, ctx, threat_model(), np.random.default_rng(0)
            )
            assert question is not None and question.form is Form.IDENTIFY


def test_the_facts_count_recoveries_in_the_attacking_third_so_far() -> None:
    match, ctx, candidates = designed_with_candidates(0)
    wins = [c for c in candidates if c.tag.concept is ConceptId.BALL_WIN]
    league = generate_league(np.random.default_rng(0))
    counted: list[tuple[float, float]] = []
    for candidate in wins[::7]:
        pack = build_pack(
            ask(ctx, candidate, 3), ASKED_LATER, ctx, threat_model(), league, load_concept_map()
        )
        high = float(pack.outcome["high_recoveries"].value)
        average = float(pack.outcome["avg_high_recoveries"].value)
        counted.append((high, average))
        team = match.events[candidate.tag.action_id].team_id
        expected = sum(
            1
            for c in wins
            if c.tag.action_id <= candidate.tag.action_id
            and c.tag.evidence["metres from own goal"] >= 70
            and match.events[c.tag.action_id].team_id == team
        )
        assert high == expected
        assert pack.outcome["recovery_type"].display in {w.label for w in WonWith}
        assert pack.outcome["pitch_third"].display in {
            "own third",
            "middle third",
            "attacking third",
        }
        assert set(pack.context) == {
            "home_team",
            "away_team",
            "team",
            "opponent",
            "score",
            "minute",
        }

    assert counted[-1][0] >= counted[0][0]
    assert any(average != high for high, average in counted)


@pytest.mark.parametrize("seed", range(10))
def test_every_simulated_ball_win_happens_in_a_transition_and_gets_a_fair_question(
    seed: int,
) -> None:
    match, ctx, candidates = designed_with_candidates(seed)
    timeline = phase_timeline(match)
    wins = [c for c in candidates if c.tag.concept is ConceptId.BALL_WIN]

    assert len(wins) > 20
    for candidate in wins:
        assert candidate.phase is PhaseOfPlay.TRANSITION
        assert timeline.phase_of(candidate.tag.action_id) is PhaseOfPlay.TRANSITION
        for level in (1, 2, 3):
            question = ask(ctx, candidate, level)
            assert len(question.options) == 3
            assert sum(o.correct for o in question.options) == 1
            assert len({o.label for o in question.options}) == 3
