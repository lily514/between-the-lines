"""Scene fixtures: one real moment per active concept, for the page's animated scenes.

The page draws each concept as a scene with three layers, every label a template over the
moment's evidence fields. The fixture gives it everything it needs, from the engine, so the
browser computes no football: the evidence pack with every evidence field filled, the snapshot
at the key frame (the pack's picture), the play's path with the time of each touch, and the
question each level would ask about the moment, worded by the template Tutor.

Moments come from seed 7's three designed matches, scored with a small threat model fitted the
same way every time (`fixture_course`), so `btl scene-fixtures` and the test that checks the
committed files agree to the byte. A concept's moment is the candidate nearest the middle of
the difficulty range, among those that tell the concept's story best.
"""

import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict

import numpy as np

from btl.concepts.phase import PhaseOfPlay
from btl.league.league import generate_league
from btl.learn.candidates import AskedWhen, Candidate
from btl.learn.concept_map import ConceptKey
from btl.learn.evidence import Delivered, EvidencePack, build_pack, question_view, turned
from btl.learn.knowledge import Delivery
from btl.learn.questions import build_question
from btl.learn.session import LEAGUE_SEED, Course, PreparedMatch, prepare_match
from btl.schema.ids import ActionId
from btl.schema.scoreboard import match_clock
from btl.schema.vocab import ConceptId
from btl.tutor.slots import fill, question_values
from btl.tutor.templates import TemplateTutor
from btl.value.xt import fit_on_simulated_matches

FIXTURE_SEED = 7
# The small, deterministic fit the fixtures are scored with; the same one the tests use.
FIXTURE_MODEL_MATCHES = 20
MIDDLE_DIFFICULTY = 0.5
# After the moment's last action, how long the ball takes to arrive, when nothing follows it.
ARRIVES_AFTER = 1.0

Fixture = dict[str, object]


def fixture_course() -> Course:
    """The course the fixtures are built from: the template Tutor and a 20-match threat fit."""
    league = generate_league(np.random.default_rng(LEAGUE_SEED))
    threat = fit_on_simulated_matches(league, LEAGUE_SEED, FIXTURE_MODEL_MATCHES, seed=0)
    return Course(threat, TemplateTutor())


def scene_fixtures(course: Course, seed: int = FIXTURE_SEED) -> dict[ConceptKey, Fixture]:
    """One fixture per active concept, from the viewer seed's three matches, in map order."""
    prepared = [prepare_match(course, seed, number) for number in (1, 2, 3)]
    return {key: scene_fixture(course, prepared, key) for key in course.active}


def scene_fixture(course: Course, prepared: Sequence[PreparedMatch], key: ConceptKey) -> Fixture:
    """The fixture for one concept: its chosen moment, pack, snapshot, path and questions.

    Raises:
        LookupError: If no match holds a moment of the concept with a question at level 1.
    """
    concept = course.concept_map.concept(key)
    choices = [
        (match, candidate)
        for match in prepared
        for candidate in match.candidates
        if candidate.concept == key
    ]
    prefer = PREFERRED.get(concept.detector or ConceptId.SWITCH_OF_PLAY, lambda _: True)
    told = [(m, c) for m, c in choices if prefer(c)] or choices
    for match, candidate in sorted(told, key=lambda mc: abs(mc[1].difficulty - MIDDLE_DIFFICULTY)):
        packs = {level: _pack(course, match, candidate, level) for level in (1, 2, 3)}
        pack = packs[1]
        if pack is None:
            continue
        return {
            "concept": key,
            "name": concept.name,
            "strand": concept.strand,
            "detector": concept.detector,
            "evidence_fields": list(concept.evidence_fields),
            "match": {
                "seed": match.seed,
                "home": match.home.name,
                "away": match.away.name,
                "home_code": match.home.short_name,
                "away_code": match.away.short_name,
            },
            "moment": {
                "action_id": candidate.tag.action_id,
                "span": list(candidate.tag.span),
                "clock": match_clock(match.ctx.events[candidate.tag.action_id]),
                "difficulty": candidate.difficulty,
                "phase": candidate.phase.value,
                "evidence": dict(candidate.tag.evidence),
            },
            "pack": asdict(pack),
            "snapshot": {
                "action_id": pack.picture.action_id,
                "markers": [asdict(marker) for marker in pack.picture.markers],
                "ball": list(pack.picture.ball),
            },
            "path": _timed_path(course, match, candidate, pack.picture.action_id),
            "questions": {
                str(level): _question(built) for level, built in packs.items() if built is not None
            },
        }
    raise LookupError(f"no moment of {key} with a question in seed {FIXTURE_SEED}'s matches")


def to_text(fixture: Fixture) -> str:
    """A fixture as the committed JSON: keys sorted, two-space indent, a newline at the end."""
    return json.dumps(fixture, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def _pack(
    course: Course, match: PreparedMatch, candidate: Candidate, level: int
) -> EvidencePack | None:
    live = candidate.asked_when is AskedWhen.AT_THE_STOPPAGE or (
        candidate.phase is PhaseOfPlay.SETTLED and candidate.asked_when is AskedWhen.IN_PLAY
    )
    delivery = Delivery.LIVE if live else Delivery.DEFERRED
    question = build_question(
        candidate, level, delivery, match.ctx, course.threat, np.random.default_rng(level)
    )
    if question is None:
        return None
    if live:
        phase = (
            PhaseOfPlay.DEAD_BALL
            if candidate.asked_when is AskedWhen.AT_THE_STOPPAGE
            else candidate.phase
        )
        delivered = Delivered(delivery, candidate.period_id, candidate.time_seconds, phase)
    else:
        delivered = Delivered(
            delivery, candidate.period_id, candidate.time_seconds + 60.0, PhaseOfPlay.DEAD_BALL
        )
    return build_pack(
        question, delivered, match.ctx, course.threat, course.league, course.concept_map
    )


def _question(pack: EvidencePack) -> dict[str, object]:
    view = question_view(pack)
    return {
        "asks": pack.asks.value,
        "form": pack.form.value,
        "text": fill(TemplateTutor().question(view).text, question_values(view)),
        "options": [option.label for option in view.options],
        "correct": pack.correct_key,
    }


def _timed_path(
    course: Course, match: PreparedMatch, candidate: Candidate, picture: ActionId
) -> list[dict[str, object]]:
    """Each touch of the play, in the picture's direction, with seconds from the first."""
    ctx = match.ctx
    first, last = candidate.tag.span
    team = ctx.events[picture].team_id
    started = ctx.events[first].time_seconds
    points: list[dict[str, object]] = []
    for action in range(first, last + 1):
        event = ctx.events[action]
        x, y = turned(event.start_x, event.start_y, event.team_id, team)
        points.append(
            {
                "action_id": event.action_id,
                "at": round(event.time_seconds - started, 2),
                "x": x,
                "y": y,
                "action": event.action_type.spadl_name,
                "result": event.result.spadl_name,
                "side": "attacking" if event.team_id == team else "defending",
                "shirt": course.league.player(event.player_id).shirt_number,
            }
        )
    end = ctx.events[last]
    after = ctx.events[last + 1] if last + 1 < len(ctx.events) else None
    arrives = (
        after.time_seconds
        if after is not None and after.period_id == end.period_id
        else end.time_seconds + ARRIVES_AFTER
    )
    x, y = turned(end.end_x, end.end_y, end.team_id, team)
    points.append(
        {
            "action_id": end.action_id,
            "at": round(arrives - started, 2),
            "x": x,
            "y": y,
            "action": "end",
        }
    )
    return points


def _offside_call(candidate: Candidate) -> bool:
    return bool(candidate.tag.evidence["offside"])


def _over_the_goal_line(candidate: Candidate) -> bool:
    return bool(candidate.tag.evidence["over a goal line"])


def _stops_play(candidate: Candidate) -> bool:
    return not candidate.tag.evidence["advantage"]


def _in_the_middle_third(candidate: Candidate) -> bool:
    return 35.0 <= candidate.tag.evidence["metres from own goal"] < 70.0


def _won_by_an_outfield_player(candidate: Candidate) -> bool:
    return candidate.tag.evidence["won (m from own goal)"] >= OUTFIELD_WIN


# A ball won this far from the team's own goal was won by an outfield player, not the keeper.
OUTFIELD_WIN = 20.0
# Which moments tell a concept's story best on the page, when the match offers a choice.
PREFERRED: Mapping[ConceptId, Callable[[Candidate], bool]] = {
    ConceptId.OFFSIDE: _offside_call,
    ConceptId.RESTART: _over_the_goal_line,
    ConceptId.FOUL: _stops_play,
    ConceptId.BALL_WIN: _in_the_middle_third,
    ConceptId.COUNTER_ATTACK: _won_by_an_outfield_player,
}
