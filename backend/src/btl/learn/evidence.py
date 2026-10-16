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
import re
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass, replace

from btl.concepts.base import MatchContext
from btl.concepts.phase import PhaseOfPlay
from btl.league.league import League
from btl.learn.candidates import AskedWhen
from btl.learn.concept_map import ConceptKey, ConceptMap
from btl.learn.knowledge import Delivery
from btl.learn.questions import Asks, Form, Option, Question, offside_reference
from btl.schema import PITCH_LENGTH, PITCH_WIDTH
from btl.schema.ids import ActionId, PlayerId, TeamId
from btl.schema.scoreboard import clock, goals
from btl.schema.vocab import ActionType, ConceptId
from btl.value.xt import ThreatModel

PACK_VERSION = 3
# Pressing players count if they stand this close to the ball when it is won back.
PRESSING_DISTANCE = 10.0
COUNT_WORDS = ("no", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine")
RESTART_TYPES = {
    ActionType.THROW_IN: "throw-in",
    ActionType.GOALKICK: "goal kick",
    ActionType.CORNER_CROSSED: "corner",
    ActionType.CORNER_SHORT: "corner",
}
LABEL_SLOT = re.compile(r"\{([a-z_]+)\}")


@dataclass(frozen=True, slots=True)
class Fact:
    """One fact: its value, and the text shown for it, number only (units live in the text)."""

    value: float | str
    display: str


@dataclass(frozen=True, slots=True)
class PackOption:
    """An answer option as shown: its label with names filled in, and its facts.

    ``neutral`` facts may be shown before the viewer answers; ``outcome`` facts only after.
    ``target_at`` is where a pass option's receiver stands, as in the picture.
    """

    key: str
    label: str
    correct: bool
    neutral: Mapping[str, Fact]
    outcome: Mapping[str, Fact]
    target_at: tuple[float, float] | None = None


@dataclass(frozen=True, slots=True)
class Marker:
    """A player on the pitch picture, seen with the team on the ball attacking left to right.

    ``side`` is relative to the ball ("attacking" or "defending"); ``home`` says which club.
    """

    shirt: int
    side: str
    home: bool
    x: float
    y: float
    role: str


@dataclass(frozen=True, slots=True)
class Picture:
    """What the viewer sees: the players, the ball, and the play's path when it is shown.

    ``mark`` is a spot the question is about, such as where the ball went out for a throw-in.
    """

    action_id: ActionId
    markers: tuple[Marker, ...]
    ball: tuple[float, float]
    path: tuple[tuple[float, float], ...]
    mark: tuple[float, float] | None = None


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
    """Everything about one question. Built once; ``pack_id`` is a hash of the rest.

    ``reveal_path`` is the play's real path, for every form, shown after answering, and
    ``reveal_line`` the offside line's x for an offside question. The question view leaves both
    out; a predict question's picture shows at most the action that set it up.
    """

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
    reveal_path: tuple[tuple[float, float], ...]
    reveal_line: float | None = None


@dataclass(frozen=True, slots=True)
class ViewOption:
    """An option as a question shows it: its key, its label, its neutral facts and its place."""

    key: str
    label: str
    neutral: Mapping[str, Fact]
    target_at: tuple[float, float] | None


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
        "score": _text(f"{score[home]}\N{EN DASH}{score[away]}"),
        "minute": _text(clock(event.period_id, event.time_seconds)),
    }
    known, outcome = FACTS[tag.concept](question, ctx, threat, names)
    context.update(known)
    shown = SHOWN.get(tag.concept, _span_if_identify)(question)
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
        options=tuple(_pack_option(option, names, context) for option in question.options),
        correct_key=question.correct_key,
        picture=_picture(question, ctx, league, shown),
        reveal_path=_play_path(tag.span, question.picture, ctx),
        reveal_line=tag.evidence["line (m)"] if tag.concept is ConceptId.OFFSIDE else None,
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
        options=tuple(ViewOption(o.key, o.label, o.neutral, o.target_at) for o in pack.options),
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


def _line_breaking_facts(
    question: Question, ctx: MatchContext, threat: ThreatModel, names: _Names
) -> tuple[dict[str, Fact], dict[str, Fact]]:
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
    # The passer is known before the pass.
    return {"player": _text(names.player(event.player_id))}, outcome


def _counter_press_facts(
    question: Question, ctx: MatchContext, threat: ThreatModel, names: _Names
) -> tuple[dict[str, Fact], dict[str, Fact]]:
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
    outcome = {
        "seconds_to_regain": _seconds(tag.evidence["seconds to win back"]),
        "metres_from_goal": _metres(tag.evidence["metres from goal"]),
        "pressers": _count(pressers),
        # Who wins the ball back is part of the answer.
        "player": _text(names.player(event.player_id)),
    }
    return {}, outcome


def _restart_facts(
    question: Question, ctx: MatchContext, threat: ThreatModel, names: _Names
) -> tuple[dict[str, Fact], dict[str, Fact]]:
    first, last = question.candidate.tag.span
    out, restart = ctx.events[first], ctx.events[last]
    home, away = ctx.match.home_team_id, ctx.match.away_team_id
    restarting = restart.team_id
    other = away if restarting == home else home
    kind = RESTART_TYPES[restart.action_type]
    if kind == "throw-in":
        line = "touchline"
    else:
        # A corner is taken at the other team's goal line, a goal kick at the team's own.
        defending = other if kind == "corner" else restarting
        line = f"goal line {names.club(defending)} defend"
    context = {
        "player": _text(names.player(out.player_id)),
        # By the Laws the restart goes against the last touch, recorded or not.
        "last_touch_team": _text(names.club(other)),
        "out_line": _text(line),
    }
    outcome = {"restart_type": _text(kind), "restart_team": _text(names.club(restarting))}
    return context, outcome


def _offside_facts(
    question: Question, ctx: MatchContext, threat: ThreatModel, names: _Names
) -> tuple[dict[str, Fact], dict[str, Fact]]:
    tag = question.candidate.tag
    event = ctx.events[tag.action_id]
    line = tag.evidence["line (m)"]
    context = {"player": _text(names.player(event.player_id))}
    outcome: dict[str, Fact] = {}
    if question.asks is Asks.WHO_IS_OFFSIDE:
        # About the attacker in the offside position, who is the answer, so only afterwards.
        answer = next(o for o in question.options if o.correct)
        assert answer.target is not None and answer.end is not None
        receiver, margin = answer.target, answer.end[0] - line
        outcome["attacker"] = _text(names.player(receiver))
    else:
        receiver = PlayerId(int(tag.evidence["player id"]))
        margin = tag.evidence["margin (m)"] * (1 if tag.evidence["offside"] else -1)
        context["attacker"] = _text(names.player(receiver))
    reference = offside_reference(question.candidate, ctx)
    if reference == "halfway":
        reference = "the halfway line"
    side = "level with" if margin == 0 else ("beyond" if margin > 0 else "behind")
    outcome |= {
        "margin_m": _metres(abs(margin)),
        "beyond_or_behind": _text(f"{side} {reference}"),
        "offside_call": _text("offside" if margin > 0 else "onside"),
    }
    return context, outcome


def _foul_facts(
    question: Question, ctx: MatchContext, threat: ThreatModel, names: _Names
) -> tuple[dict[str, Fact], dict[str, Fact]]:
    tag = question.candidate.tag
    foul = ctx.events[tag.action_id]
    home, away = ctx.match.home_team_id, ctx.match.away_team_id
    fouler = names.player(foul.player_id)
    fouled = names.club(away if foul.team_id == home else home)
    evidence = tag.evidence
    if evidence["advantage"]:
        restart = "advantage"
        result = f"The referee let play go on, because {fouled} kept the ball."
    else:
        restart = "penalty" if evidence["penalty"] else "free kick"
        result = f"{fouled} get a {restart}."
    if evidence["booked"] and evidence["promising attack"]:
        booking = "The booking was for stopping a promising attack."
    elif evidence["booked"]:
        booking = f"{fouler} was booked."
    else:
        booking = "There was no booking."
    outcome = {
        "restart_type": _text(restart),
        "box_position": _box_position(evidence["metres from the box"]),
        "foul_outcome": _text(result),
        "booking_note": _text(booking),
    }
    return {"fouler": _text(fouler), "fouled_team": _text(fouled)}, outcome


def _box_position(metres: float) -> Fact:
    if metres < 0:
        return Fact(metres, "inside the penalty area")
    if metres == 0:
        return Fact(metres, "on the penalty area's line")
    return Fact(metres, f"{_measured(metres).display} m outside the penalty area")


def _pack_option(option: Option, names: _Names, context: Mapping[str, Fact]) -> PackOption:
    label = option.label
    neutral: dict[str, Fact] = {}
    if option.target is not None:
        label = label.replace("{target}", names.player(option.target))
        neutral["target"] = _text(names.player(option.target))
    label = LABEL_SLOT.sub(lambda slot: context[slot.group(1)].display, label)
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
    target_at = None if option.end is None else (round(option.end[0], 1), round(option.end[1], 1))
    return PackOption(option.key, label, option.correct, neutral, outcome, target_at)


def _picture(
    question: Question,
    ctx: MatchContext,
    league: League,
    shown: tuple[ActionId, ActionId] | None,
) -> Picture:
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
                    home=p.team_id == ctx.match.home_team_id,
                    x=round(p.x, 1),
                    y=round(p.y, 1),
                    role=role,
                )
            )
    return Picture(
        action_id=question.picture,
        markers=tuple(markers),
        ball=(round(event.start_x, 1), round(event.start_y, 1)),
        path=() if shown is None else _play_path(shown, question.picture, ctx),
        mark=_out_point(question, ctx),
    )


def _span_if_identify(question: Question) -> tuple[ActionId, ActionId] | None:
    return question.candidate.tag.span if question.form is Form.IDENTIFY else None


def _action_out(question: Question) -> tuple[ActionId, ActionId] | None:
    # The action that sent the ball out, but not the restart, which is the answer.
    first = question.candidate.tag.span[0]
    return (first, first)


def _foul_shown(question: Question) -> tuple[ActionId, ActionId] | None:
    # After advantage, the play that went on; at a stoppage, just the foul's spot.
    after = question.candidate.asked_when is AskedWhen.AFTERWARDS
    return question.candidate.tag.span if after else None


def _out_point(question: Question, ctx: MatchContext) -> tuple[float, float] | None:
    """Where the ball went out for a throw-in, in the picture's direction.

    For a corner or a goal kick, event data says only where it is taken, not where along the
    goal line the ball crossed.
    """
    if question.candidate.tag.concept is not ConceptId.RESTART:
        return None
    restart = ctx.events[question.candidate.tag.span[1]]
    if restart.action_type is not ActionType.THROW_IN:
        return None
    team = ctx.events[question.picture].team_id
    return _turned(restart.start_x, restart.start_y, restart.team_id, team)


def _play_path(
    span: tuple[ActionId, ActionId], picture: ActionId, ctx: MatchContext
) -> tuple[tuple[float, float], ...]:
    """The play's path in the picture's direction: its team attacking towards x = 105.

    The context gives each action in its own team's direction, so a play that changes hands
    (a counter-press) has the other team's actions turned round to match.
    """
    first, last = span
    team = ctx.events[picture].team_id
    played = [ctx.events[a] for a in range(first, last + 1)]
    return (
        *(_turned(e.start_x, e.start_y, e.team_id, team) for e in played),
        _turned(played[-1].end_x, played[-1].end_y, played[-1].team_id, team),
    )


def _turned(x: float, y: float, team_id: TeamId, towards: TeamId) -> tuple[float, float]:
    """A point in ``team_id``'s direction, seen in ``towards``'s, rounded for the pack."""
    if team_id != towards:
        x, y = PITCH_LENGTH - x, PITCH_WIDTH - y
    return (round(x, 1), round(y, 1))


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


# Each concept's facts, as (context, outcome): what is known before answering, and what answers.
FACTS: Mapping[
    ConceptId,
    Callable[
        [Question, MatchContext, ThreatModel, _Names],
        tuple[dict[str, Fact], dict[str, Fact]],
    ],
] = {
    ConceptId.LINE_BREAKING_PASS: _line_breaking_facts,
    ConceptId.COUNTER_PRESS: _counter_press_facts,
    ConceptId.RESTART: _restart_facts,
    ConceptId.OFFSIDE: _offside_facts,
    ConceptId.FOUL: _foul_facts,
}
# The stretch of play a question shows before the viewer answers, for each concept that
# doesn't follow the rule: the whole play for an identify question, none for a predict one.
SHOWN: Mapping[ConceptId, Callable[[Question], tuple[ActionId, ActionId] | None]] = {
    ConceptId.RESTART: _action_out,
    ConceptId.FOUL: _foul_shown,
}
