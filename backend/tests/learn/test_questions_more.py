"""Questions about the concepts that joined in Milestone 5: tackles, shots, and transitions."""

import numpy as np
import pytest

from btl.concepts.ball_win import BallWin, WonWith
from btl.concepts.base import MatchContext, match_context
from btl.concepts.counter_attack import CounterAttack
from btl.concepts.phase import PhaseOfPlay, phase_timeline
from btl.concepts.shot import ChanceFrom, Shot, ShotZone
from btl.league.league import generate_league
from btl.learn.candidates import ASKED_WHEN, AskedWhen, Candidate
from btl.learn.concept_map import load_concept_map
from btl.learn.evidence import build_pack
from btl.learn.knowledge import Delivery
from btl.learn.questions import (
    AFTER_WINNING_IT,
    ANY_FAST_ATTACK,
    CHANCE_SOURCES,
    DEEP_WINS_ARE_JUST_AS_USEFUL,
    SHOT_OUTCOMES,
    SHOT_ZONES,
    WHICH_THIRD,
    WHY_A_COUNTER,
    WHY_THE_THIRD_MATTERS,
    WON_WITH,
    Asks,
    Form,
    Question,
    build_question,
)
from btl.learn.selector import BANDS
from btl.schema.match import Match
from btl.schema.possession import SHOTS as ALL_SHOTS
from btl.schema.vocab import ActionType, ConceptId, Result
from tests.fixtures.concepts import chance_and_shot, lost_and_won_back, won_and_carried
from tests.fixtures.learning import (
    SHOTS,
    TACKLES,
    TRANSITIONS,
    designed_with_candidates,
    threat_model,
)
from tests.learn.test_evidence import ASKED_LATER

DEFERRED = Delivery.DEFERRED
LEAGUE = generate_league(np.random.default_rng(0))


def ball_win(match: Match, index: int = 0) -> tuple[MatchContext, Candidate]:
    ctx = match_context(match)
    tag = BallWin().detect(ctx)[index]
    assert tag.difficulty is not None
    return ctx, Candidate(TACKLES, tag, tag.difficulty, PhaseOfPlay.TRANSITION, 1, 0.0)


def shot(match: Match) -> tuple[MatchContext, Candidate]:
    ctx = match_context(match)
    (tag,) = Shot().detect(ctx)
    assert tag.difficulty is not None
    asked_when = ASKED_WHEN[tag.concept](tag)
    return ctx, Candidate(SHOTS, tag, tag.difficulty, PhaseOfPlay.SETTLED, 1, 0.0, asked_when)


def ask(ctx: MatchContext, candidate: Candidate, level: int) -> Question:
    question = build_question(
        candidate, level, DEFERRED, ctx, threat_model(), np.random.default_rng(0)
    )
    assert question is not None
    return question


def answer(question: Question) -> str:
    return next(o.label for o in question.options if o.correct)


def packed(ctx: MatchContext, question: Question):
    return build_pack(question, ASKED_LATER, ctx, threat_model(), LEAGUE, load_concept_map())


# ---------------------------------------------------------------- Tackles and turnovers


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
    counted: list[tuple[float, float]] = []
    for candidate in wins[::7]:
        pack = packed(ctx, ask(ctx, candidate, 3))
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


# ---------------------------------------------------------------- Shots and goals


def test_level_one_asks_what_came_of_the_shot() -> None:
    saved = chance_and_shot((95.0, 30.0), (105.0, 34.0), saved=True)
    scored = chance_and_shot((101.0, 36.0), (105.0, 37.0), result=Result.SUCCESS)
    wide = chance_and_shot((80.0, 34.0), (105.0, 40.0))

    questions = [ask(*shot(match), 1) for match in (saved, scored, wide)]

    assert all((q.form, q.asks) == (Form.IDENTIFY, Asks.ON_TARGET) for q in questions)
    assert [answer(q) for q in questions] == ["Saved", "Scored", "Off target"]
    assert all({o.label for o in q.options} == set(SHOT_OUTCOMES.values()) for q in questions)


def test_level_two_asks_where_from_and_level_three_how_the_chance_came() -> None:
    from_a_cross = chance_and_shot(
        (101.0, 36.0), (105.0, 34.0), made_by=ActionType.CROSS, saved=True
    )
    from_a_dribble = chance_and_shot(
        (80.0, 34.0), (105.0, 34.0), made_by=ActionType.DRIBBLE, saved=True
    )
    free_kick = chance_and_shot(
        (80.0, 34.0), (105.0, 34.0), kind=ActionType.SHOT_FREEKICK, saved=True
    )

    where = ask(*shot(from_a_cross), 2)
    how_cross, how_dribble, how_free_kick = (
        ask(*shot(match), 3) for match in (from_a_cross, from_a_dribble, free_kick)
    )

    assert where.asks is Asks.WHERE_FROM and answer(where) == SHOT_ZONES[ShotZone.SIX_YARD_BOX]
    assert answer(ask(*shot(from_a_dribble), 2)) == SHOT_ZONES[ShotZone.OUTSIDE_THE_BOX]
    assert how_cross.asks is Asks.HOW_THE_CHANCE_CAME
    assert answer(how_cross) == CHANCE_SOURCES[ChanceFrom.CROSS]
    assert answer(how_dribble) == CHANCE_SOURCES[ChanceFrom.DRIBBLE]
    assert answer(how_free_kick) == CHANCE_SOURCES[ChanceFrom.FREE_KICK]
    assert all(len({o.label for o in q.options}) == 3 for q in (how_cross, how_dribble))


def test_a_shot_is_only_ever_reviewed_and_its_picture_stops_before_the_shot() -> None:
    ctx, candidate = shot(chance_and_shot((95.0, 30.0), (105.0, 34.0), saved=True))

    assert candidate.asked_when is AskedWhen.AFTERWARDS
    for level in (1, 2, 3):
        pack = packed(ctx, ask(ctx, candidate, level))
        # The pass arriving, drawn to the shooter, and nothing of where the shot went.
        assert pack.picture.path == ((70.0, 20.0), (95.0, 30.0))
        assert pack.picture.mark is None
        assert pack.picture.ball == (95.0, 30.0)
        assert pack.reveal_path == ((70.0, 20.0), (95.0, 30.0), (105.0, 34.0))
        assert set(pack.context) == {
            "home_team",
            "away_team",
            "team",
            "opponent",
            "score",
            "minute",
            "player",
        }
        assert pack.outcome["shot_outcome"].display == "saved"
        assert pack.outcome["shot_zone"].display == "the penalty area"
        assert pack.outcome["chance_from"].display == "a pass"


def test_a_shot_that_opens_a_possession_shows_no_path_before_answering() -> None:
    ctx, candidate = shot(chance_and_shot((95.0, 30.0), (105.0, 34.0), made_by=None, saved=True))

    pack = packed(ctx, ask(ctx, candidate, 1))

    assert pack.picture.path == ()
    assert pack.reveal_path == ((95.0, 30.0), (105.0, 34.0))


def test_the_shot_facts_count_each_sides_shots_so_far_this_one_included() -> None:
    match, ctx, candidates = designed_with_candidates(0)
    shots = [c for c in candidates if c.tag.concept is ConceptId.SHOT]
    assert len(shots) > 10

    for candidate in shots[::4]:
        pack = packed(ctx, ask(ctx, candidate, 2))
        team = match.events[candidate.tag.action_id].team_id
        before = match.events[: candidate.tag.action_id + 1]
        taken = [e for e in before if e.action_type in ALL_SHOTS]
        ours = [e for e in taken if e.team_id == team]
        assert pack.outcome["shots"].value == len(ours)
        assert pack.outcome["opp_shots"].value == len(taken) - len(ours)
        assert 0 <= float(pack.outcome["shots_on_target"].value) <= len(ours)


@pytest.mark.parametrize("seed", range(10))
def test_every_simulated_shot_gets_a_fair_question_at_every_level(seed: int) -> None:
    _, ctx, candidates = designed_with_candidates(seed)
    shots = [c for c in candidates if c.tag.concept is ConceptId.SHOT]

    assert len(shots) > 10
    for candidate in shots:
        assert candidate.asked_when is AskedWhen.AFTERWARDS
        for level in (1, 2, 3):
            question = ask(ctx, candidate, level)
            assert len(question.options) == 3
            assert sum(o.correct for o in question.options) == 1
            assert len({o.label for o in question.options}) == 3


# ---------------------------------------------------------------- Transitions


def counter_attack(match: Match) -> tuple[MatchContext, Candidate]:
    ctx = match_context(match)
    (tag,) = CounterAttack().detect(ctx)
    assert tag.difficulty is not None
    return ctx, Candidate(TRANSITIONS, tag, tag.difficulty, PhaseOfPlay.TRANSITION, 1, 0.0)


def test_the_three_levels_ask_what_next_how_long_and_why() -> None:
    ctx, candidate = counter_attack(won_and_carried(9, (30.0, 34.0)))

    what_next, how_long, why = (ask(ctx, candidate, level) for level in (1, 2, 3))

    assert (what_next.form, what_next.asks) == (Form.IDENTIFY, Asks.WHAT_NEXT_AFTER_WINNING)
    assert answer(what_next) == AFTER_WINNING_IT[0]
    assert how_long.asks is Asks.SECONDS_TO_BOX
    assert {o.label: o.correct for o in how_long.options} == {
        "Under 8 s": False,
        "8 to 10 s": True,
        "10 s or more": False,
    }
    assert why.asks is Asks.WHY_A_COUNTER_ATTACK
    assert answer(why) == WHY_A_COUNTER[0]
    assert ANY_FAST_ATTACK in {o.label for o in why.options}


def test_the_counter_attack_distractor_is_the_maps_own_misconception() -> None:
    transitions = load_concept_map().concept(TRANSITIONS)

    assert ANY_FAST_ATTACK + "." in transitions.misconceptions


def test_a_counter_attack_is_never_asked_live_and_shows_only_the_win_before_answering() -> None:
    ctx, candidate = counter_attack(won_and_carried(9, (30.0, 34.0)))

    for level in (1, 2, 3):
        for delivery in Delivery:
            question = build_question(
                candidate, level, delivery, ctx, threat_model(), np.random.default_rng(0)
            )
            assert question is not None and question.form is Form.IDENTIFY
        pack = packed(ctx, ask(ctx, candidate, level))
        assert pack.picture.path == ()
        assert pack.picture.ball == (30.0, 34.0)
        assert pack.reveal_path == ((30.0, 34.0), (30.0, 34.0), (92.0, 40.0), (105.0, 34.0))
        assert set(pack.context) == {
            "home_team",
            "away_team",
            "team",
            "opponent",
            "score",
            "minute",
        }
        assert pack.outcome["seconds_to_box"].display == "9"
        assert pack.outcome["won_metres_from_own_goal"].display == "30"


def test_the_facts_count_the_teams_shots_from_transitions_and_settled_play_so_far() -> None:
    match, ctx, candidates = designed_with_candidates(0)
    counters = [c for c in candidates if c.tag.concept is ConceptId.COUNTER_ATTACK]
    timeline = phase_timeline(match)
    assert len(counters) >= 3

    for candidate in counters:
        pack = packed(ctx, ask(ctx, candidate, 3))
        team = match.events[candidate.tag.action_id].team_id
        shots = [
            e
            for e in match.events[: candidate.tag.span[1] + 1]
            if e.action_type in ALL_SHOTS and e.team_id == team
        ]
        from_transitions = sum(
            timeline.phase_of(e.action_id) is PhaseOfPlay.TRANSITION for e in shots
        )
        assert pack.outcome["transition_shots"].value == from_transitions
        assert pack.outcome["settled_shots"].value == len(shots) - from_transitions


@pytest.mark.parametrize("seed", range(10))
def test_every_designed_match_has_a_counter_attack_for_each_level(seed: int) -> None:
    _, ctx, candidates = designed_with_candidates(seed)
    counters = [c for c in candidates if c.tag.concept is ConceptId.COUNTER_ATTACK]

    for level, (low, high) in BANDS.items():
        assert any(low <= c.difficulty <= high for c in counters), level
    for candidate in counters:
        assert candidate.phase is PhaseOfPlay.TRANSITION
        for level in (1, 2, 3):
            question = ask(ctx, candidate, level)
            assert sum(o.correct for o in question.options) == 1
            assert len({o.label for o in question.options}) == 3
