"""The evidence pack: everything known about one question, and the only source of its numbers.

Every number the viewer sees comes from a `Fact` in the pack, formatted here by code. The
Tutor writes words around ``{slots}`` that name facts; it never computes or writes a number.

Facts come in two kinds:

- **Context**: what the viewer can know before answering (the clubs, the score, the clock,
  who has the ball, where play stopped).
- **Outcome**: what answers the question, or follows from the answer (lines broken, threat
  added, seconds to win the ball back).

`question_view` is all a question may show or be worded from: context only, with every outcome
fact and the right answer left out. After the viewer answers, the whole pack is used.
"""

import hashlib
import json
import math
from collections.abc import Mapping
from dataclasses import asdict, dataclass, replace

from btl.concepts.base import MatchContext
from btl.concepts.phase import PhaseOfPlay
from btl.league.league import League
from btl.learn.concept_map import ConceptKey, ConceptMap
from btl.learn.knowledge import Delivery
from btl.learn.questions import Asks, Form, Option, Question
from btl.schema import PITCH_LENGTH
from btl.schema.ids import ActionId, PlayerId, TeamId
from btl.schema.scoreboard import clock, goals
from btl.schema.vocab import ConceptId
from btl.value.xt import ThreatModel

PACK_VERSION = 1
# Pressing players count if they stand this close to the ball when it is won back.
PRESSING_DISTANCE = 10.0
COUNT_WORDS = ("no", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine")


@dataclass(frozen=True, slots=True)
class Fact:
    """One fact: its value, and the text shown for it, number only (units live in the text)."""

    value: float | str
    display: str


@dataclass(frozen=True, slots=True)
class PackOption:
    """An answer option as shown: its label with names filled in, and its facts.

    ``neutral`` facts may be shown before the viewer answers; ``outcome`` facts only after.
    """

    key: str
    label: str
    correct: bool
    neutral: Mapping[str, Fact]
    outcome: Mapping[str, Fact]


@dataclass(frozen=True, slots=True)
class Marker:
    """A player on the pitch picture, seen with the team on the ball attacking left to right."""

    shirt: int
    side: str
    x: float
    y: float
    role: str


@dataclass(frozen=True, slots=True)
class Picture:
    """What the viewer sees: the players, the ball, and the play's path when it is shown."""

    action_id: ActionId
    markers: tuple[Marker, ...]
    ball: tuple[float, float]
    path: tuple[tuple[float, float], ...]


@dataclass(frozen=True, slots=True)
class ConceptText:
    """The concept-map text the Tutor may use, unchanged."""

    key: ConceptKey
    name: str
    objective: str
    beginner: str
    intermediate: str
    analyst: str
    misconceptions: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Timing:
    """When the moment happened and when it is asked about."""

    occurred_at: str
    occurred_phase: PhaseOfPlay
    delivered_at: str
    delivered_phase: PhaseOfPlay
    delivery: Delivery
    restart: str | None


@dataclass(frozen=True, slots=True)
class EvidencePack:
    """Everything about one question. Built once; ``pack_id`` is a hash of the rest."""

    pack_id: str
    pack_version: int
    concept: ConceptText
    form: Form
    asks: Asks
    level: int
    timing: Timing
    context: Mapping[str, Fact]
    outcome: Mapping[str, Fact]
    options: tuple[PackOption, ...]
    correct_key: str
    picture: Picture


@dataclass(frozen=True, slots=True)
class ViewOption:
    """An option as a question shows it: its key, its label and its neutral facts."""

    key: str
    label: str
    neutral: Mapping[str, Fact]


@dataclass(frozen=True, slots=True)
class QuestionView:
    """What a question may show or be worded from, before the viewer answers."""

    pack_id: str
    concept_name: str
    form: Form
    asks: Asks
    level: int
    timing: Timing
    context: Mapping[str, Fact]
    options: tuple[ViewOption, ...]
    picture: Picture


@dataclass(frozen=True, slots=True)
class Delivered:
    """When and in what phase of play a question is asked, as decided by the selector."""

    delivery: Delivery
    period_id: int
    time_seconds: float
    phase: PhaseOfPlay
    restart: str | None = None


def build_pack(
    question: Question,
    delivered: Delivered,
    ctx: MatchContext,
    threat: ThreatModel,
    league: League,
    concept_map: ConceptMap,
) -> EvidencePack:
    """Gather everything about a question into one pack.

    Args:
        question: The question, with its options.
        delivered: When it is asked.
        ctx: The match as detectors see it, every action attacking left to right.
        threat: The threat model, for the threat before and after a pass.
        league: For club and player names.
        concept_map: For the concept's text.
    """
    tag = question.candidate.tag
    event = ctx.events[tag.action_id]
    names = _Names(league)
    home, away = ctx.match.home_team_id, ctx.match.away_team_id
    other = away if event.team_id == home else home
    score = goals(ctx.match, before=tag.action_id)
    context: dict[str, Fact] = {
        "home_team": _text(names.club(home)),
        "away_team": _text(names.club(away)),
        "team": _text(names.club(event.team_id)),
        "opponent": _text(names.club(other)),
        "score": _text(f"{score[home]}-{score[away]}"),
        "minute": _text(clock(event.period_id, event.time_seconds)),
    }
    if tag.concept is ConceptId.LINE_BREAKING_PASS:
        # The passer is known before the pass; who wins the ball back is part of the answer.
        context["player"] = _text(names.player(event.player_id))
        outcome = _line_breaking_outcome(question, ctx, threat, names)
    else:
        outcome = _counter_press_outcome(question, ctx)
        outcome["player"] = _text(names.player(event.player_id))
    concept = concept_map.concept(question.candidate.concept)
    pack = EvidencePack(
        pack_id="",
        pack_version=PACK_VERSION,
        concept=ConceptText(
            key=concept.key,
            name=concept.name,
            objective=concept.objective,
            beginner=concept.explanations.beginner,
            intermediate=concept.explanations.intermediate,
            analyst=concept.explanations.analyst,
            misconceptions=concept.misconceptions,
        ),
        form=question.form,
        asks=question.asks,
        level=question.level,
        timing=Timing(
            occurred_at=clock(event.period_id, event.time_seconds),
            occurred_phase=question.candidate.phase,
            delivered_at=clock(delivered.period_id, delivered.time_seconds),
            delivered_phase=delivered.phase,
            delivery=delivered.delivery,
            restart=delivered.restart,
        ),
        context=context,
        outcome=outcome,
        options=tuple(_pack_option(option, names) for option in question.options),
        correct_key=question.correct_key,
        picture=_picture(question, ctx, league),
    )
    return _with_id(pack)


def question_view(pack: EvidencePack) -> QuestionView:
    """The pack as a question may see it: no right answer, no outcome facts."""
    return QuestionView(
        pack_id=pack.pack_id,
        concept_name=pack.concept.name,
        form=pack.form,
        asks=pack.asks,
        level=pack.level,
        timing=pack.timing,
        context=pack.context,
        options=tuple(ViewOption(o.key, o.label, o.neutral) for o in pack.options),
        picture=pack.picture,
    )


def to_json(value: EvidencePack | QuestionView) -> str:
    """A pack or view as JSON, with keys sorted, so equal packs give equal text."""
    return json.dumps(asdict(value), sort_keys=True, ensure_ascii=False)


def _with_id(pack: EvidencePack) -> EvidencePack:
    digest = hashlib.sha256(to_json(pack).encode()).hexdigest()[:16]
    return replace(pack, pack_id=digest)


class _Names:
    def __init__(self, league: League) -> None:
        self._league = league

    def club(self, team_id: TeamId) -> str:
        return self._league.club(team_id).name

    def player(self, player_id: PlayerId) -> str:
        player = self._league.player(player_id)
        return f"#{player.shirt_number} {player.full_name}"


def _line_breaking_outcome(
    question: Question, ctx: MatchContext, threat: ThreatModel, names: _Names
) -> dict[str, Fact]:
    tag = question.candidate.tag
    event = ctx.events[tag.action_id]
    before = threat.value_at(event.start_x, event.start_y)
    after = threat.value_at(event.end_x, event.end_y)
    receiver = next(
        (option.target for option in question.options if option.correct and option.target),
        None,
    )
    outcome = {
        "lines_broken": _count(tag.evidence["lines broken"]),
        "gap_m": _metres(tag.evidence["gap (m)"]),
        "xt_before": _percent(before),
        "xt_after": _percent(after),
        "threat_added": _percent_points(after - before),
        "receiver_zone": _text(_zone(event.end_x)),
    }
    if receiver is not None:
        outcome["receiver"] = _text(names.player(receiver))
    return outcome


def _counter_press_outcome(question: Question, ctx: MatchContext) -> dict[str, Fact]:
    tag = question.candidate.tag
    event = ctx.events[tag.action_id]
    snapshot = ctx.snapshot(event.action_id)
    pressers = (
        sum(
            1
            for p in snapshot.positions
            if p.team_id == event.team_id
            and not p.is_goalkeeper
            and math.dist((p.x, p.y), (event.start_x, event.start_y)) <= PRESSING_DISTANCE
        )
        if snapshot is not None
        else 0
    )
    return {
        "seconds_to_regain": _seconds(tag.evidence["seconds to win back"]),
        "metres_from_goal": _metres(tag.evidence["metres from goal"]),
        "pressers": _count(pressers),
    }


def _pack_option(option: Option, names: _Names) -> PackOption:
    label = option.label
    if option.target is not None:
        label = label.replace("{target}", names.player(option.target))
    neutral: dict[str, Fact] = {}
    outcome: dict[str, Fact] = {}
    for name, value in option.facts.items():
        if name == "distance_m":
            neutral[name] = _metres(float(value))
        elif name == "direction":
            neutral[name] = _text(str(value))
        elif name == "lines_broken":
            outcome[name] = _count(float(value))
        elif name == "gap_m" and float(value) > 0:
            outcome[name] = _metres(float(value))
        elif name == "threat_added":
            outcome[name] = _percent_points(float(value))
    return PackOption(option.key, label, option.correct, neutral, outcome)


def _picture(question: Question, ctx: MatchContext, league: League) -> Picture:
    tag = question.candidate.tag
    event = ctx.events[question.picture]
    snapshot = ctx.snapshot(question.picture)
    markers: list[Marker] = []
    if snapshot is not None:
        for p in snapshot.positions:
            ours = p.team_id == event.team_id
            role = "on the ball" if p.is_actor else ("keeper" if p.is_goalkeeper else "player")
            markers.append(
                Marker(
                    shirt=league.player(p.player_id).shirt_number,
                    side="attacking" if ours else "defending",
                    x=round(p.x, 1),
                    y=round(p.y, 1),
                    role=role,
                )
            )
    path: tuple[tuple[float, float], ...] = ()
    if question.form is Form.IDENTIFY:
        first, last = tag.span
        played = [ctx.events[a] for a in range(first, last + 1)]
        path = (
            *((round(e.start_x, 1), round(e.start_y, 1)) for e in played),
            (round(played[-1].end_x, 1), round(played[-1].end_y, 1)),
        )
    return Picture(
        action_id=question.picture,
        markers=tuple(markers),
        ball=(round(event.start_x, 1), round(event.start_y, 1)),
        path=path,
    )


def _zone(x: float) -> str:
    third = PITCH_LENGTH / 3
    if x >= 2 * third:
        return "final third"
    return "middle third" if x >= third else "defensive third"


def _text(value: str) -> Fact:
    return Fact(value, value)


def _count(value: float) -> Fact:
    whole = int(value)
    return Fact(whole, COUNT_WORDS[whole] if whole < len(COUNT_WORDS) else str(whole))


def _metres(value: float) -> Fact:
    return _measured(value)


def _seconds(value: float) -> Fact:
    return _measured(value)


def _measured(value: float) -> Fact:
    """To one decimal, as the detectors round, dropping a trailing ".0": "11.9", "12"."""
    shown = f"{value:.1f}"
    return Fact(value, shown[:-2] if shown.endswith(".0") else shown)


def _percent(probability: float) -> Fact:
    return Fact(probability, f"{_significant(probability * 100)}%")


def _percent_points(change: float) -> Fact:
    sign = "-" if change < 0 else "+"
    return Fact(change, f"{sign}{_significant(abs(change) * 100)}%")


def _significant(value: float) -> str:
    """Two significant figures, since threat values span 0.1% to 30%: "0.29", "4.1", "12"."""
    return f"{value:.0f}" if value >= 10 else f"{value:.2g}"
