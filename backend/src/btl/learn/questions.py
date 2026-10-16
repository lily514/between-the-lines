"""Questions: what to ask about a candidate moment, and its three answer options.

The form depends on the concept, the viewer's level and when the question is asked:

- A line-breaking pass asked live at level 2 or 3 is a **predict** question: play stops before
  the pass, and the options are passes to three teammates.
- Everything else is an **identify** question about play the viewer has just seen: a
  line-breaking pass asked at level 1 or after a delay, and every counter-press, since a
  counter-press happens during a transition and is never asked live.

Questions get harder as the level rises. Predict questions offer closer alternatives.
Identify questions ask for finer detail: how many lines a pass broke, then how wide its gap
was, first in coarse ranges and then in narrow ones.

This module decides what is asked and what the options are. Wording is the Tutor's job.
Every number comes from a detector or the threat model, never from text.
"""

import math
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum

from numpy.random import Generator

from btl.concepts.base import MatchContext
from btl.concepts.line_breaking import LineBreakingPass
from btl.learn.candidates import Candidate
from btl.learn.concept_map import ConceptKey, ConceptMap
from btl.learn.knowledge import Delivery
from btl.schema.ids import ActionId, PlayerId
from btl.schema.snapshot import PlayerPosition
from btl.schema.vocab import ConceptId
from btl.value.xt import ThreatModel

OPTION_KEYS = ("A", "B", "C")
# A pass within this many metres of level counts as sideways.
SIDEWAYS = 5.0
# Gap-width ranges for level-2 identify questions; level 3 uses narrow ranges of this width.
GAP_EDGES = (8.0, 14.0)
GAP_STEP = 3.0
# Seconds-to-win-back ranges for level-2 identify questions; level 3 uses one-second ranges.
REGAIN_EDGES = (2.0, 3.5)
REGAIN_STEP = 1.0
WHAT_THEY_DID = (
    "Hunted the ball straight back and won it",
    "Dropped back into their shape",
    "Stopped the attack with a foul",
)
LINE_COUNTS = ("None", "One", "Two", "Three")


class Form(StrEnum):
    """Whether the viewer predicts what should happen, or identifies what just did."""

    PREDICT = "predict"
    IDENTIFY = "identify"


class Asks(StrEnum):
    """What a question asks; the Tutor turns it into words."""

    WHERE_TO_PASS = "where to pass"
    LINES_BROKEN = "lines broken"
    GAP_WIDTH = "gap width"
    WHAT_THEY_DID = "what they did"
    SECONDS_TO_REGAIN = "seconds to win back"


@dataclass(frozen=True, slots=True)
class Option:
    """One answer the viewer can pick.

    ``label`` is written by code. A pass option's label holds a ``{target}`` slot for the
    receiver's name, which the evidence pack fills in. ``facts`` are measured, never written:
    for a pass, what it would break and add if it were played. ``end`` is where a pass option's
    receiver stands, seen with the passing team attacking left to right.
    """

    key: str
    label: str
    correct: bool
    target: PlayerId | None = None
    end: tuple[float, float] | None = None
    facts: Mapping[str, float | str] = field(default_factory=dict[str, float | str])


@dataclass(frozen=True, slots=True)
class Question:
    """A question about one candidate moment, with exactly three options, one correct.

    ``picture`` is the action whose snapshot the viewer sees. A predict question shows it
    before the play; an identify question shows the play from ``candidate.tag.span``.
    """

    candidate: Candidate
    form: Form
    asks: Asks
    level: int
    delivery: Delivery
    picture: ActionId
    options: tuple[Option, ...]

    @property
    def correct_key(self) -> str:
        """The key of the right option."""
        return next(option.key for option in self.options if option.correct)


_Unkeyed = tuple[str, bool, PlayerId | None, tuple[float, float] | None, Mapping[str, float | str]]
_Built = tuple[Asks, list[_Unkeyed]] | None


@dataclass(frozen=True, slots=True)
class ConceptQuestions:
    """How one concept is asked.

    ``form`` gives the form for a level and delivery. ``build`` gives what the question asks
    and its options, unshuffled with exactly one correct, or None if no fair set exists.
    """

    form: Callable[[int, Delivery], Form]
    build: Callable[[Candidate, int, Form, MatchContext, ThreatModel, Generator], _Built]


def active_concepts(concept_map: ConceptMap) -> tuple[ConceptKey, ...]:
    """The map's concepts the app can ask about: those whose detector has questions here."""
    return tuple(c.key for c in concept_map.concepts if c.detector in ASKABLE)


def question_form(concept: ConceptId, level: int, delivery: Delivery) -> Form:
    """The form a concept's question takes at a level and delivery."""
    return QUESTIONS[concept].form(level, delivery)


def build_question(
    candidate: Candidate,
    level: int,
    delivery: Delivery,
    ctx: MatchContext,
    threat: ThreatModel,
    rng: Generator,
) -> Question | None:
    """The question for a candidate at a level, with its options shuffled by ``rng``.

    Returns:
        The question, or None if no fair set of options exists: for a predict question, fewer
        than two teammates offer a pass that breaks fewer lines and adds no more threat than
        the real one.
    """
    concept = candidate.tag.concept
    if concept not in QUESTIONS:
        raise ValueError(f"no questions exist for {concept}")
    asking = QUESTIONS[concept]
    form = asking.form(level, delivery)
    built = asking.build(candidate, level, form, ctx, threat, rng)
    if built is None:
        return None
    asks, unkeyed = built
    # A random sort key per option shuffles them with a typed draw.
    order = sorted(range(len(unkeyed)), key=lambda _: rng.random())
    options = tuple(
        Option(key, *unkeyed[index]) for key, index in zip(OPTION_KEYS, order, strict=True)
    )
    return Question(candidate, form, asks, level, delivery, candidate.tag.action_id, options)


def _line_breaking_form(level: int, delivery: Delivery) -> Form:
    return Form.PREDICT if delivery is Delivery.LIVE and level >= 2 else Form.IDENTIFY


def _line_breaking(
    candidate: Candidate,
    level: int,
    form: Form,
    ctx: MatchContext,
    threat: ThreatModel,
    rng: Generator,
) -> _Built:
    if form is Form.PREDICT:
        return _where_to_pass(candidate, level, ctx, threat)
    return _line_breaking_identify(candidate, level, rng)


def _after_the_play(level: int, delivery: Delivery) -> Form:
    # A counter-press happens during a transition, so it is only ever asked after the play.
    return Form.IDENTIFY


def _counter_press(
    candidate: Candidate,
    level: int,
    form: Form,
    ctx: MatchContext,
    threat: ThreatModel,
    rng: Generator,
) -> _Built:
    return _counter_press_identify(candidate, level, rng)


def _where_to_pass(
    candidate: Candidate, level: int, ctx: MatchContext, threat: ThreatModel
) -> _Built:
    event = ctx.events[candidate.tag.action_id]
    snapshot = ctx.snapshot(event.action_id)
    if snapshot is None:
        return None
    start = (event.start_x, event.start_y)
    teammates = [
        p
        for p in snapshot.positions
        if p.team_id == event.team_id and p.player_id != event.player_id and not p.is_goalkeeper
    ]
    if not teammates:
        return None
    receiver = min(teammates, key=lambda p: math.dist((p.x, p.y), (event.end_x, event.end_y)))
    detector = LineBreakingPass()

    def facts(end: tuple[float, float]) -> dict[str, float | str]:
        gaps = detector.lines_broken(snapshot, event.team_id, start, end)
        return {
            "lines_broken": len(gaps),
            "gap_m": round(min(gaps), 1) if gaps else 0.0,
            "threat_added": threat.value_at(*end) - threat.value_at(*start),
            "distance_m": round(math.dist(start, end), 1),
            "direction": _direction(end[0] - start[0]),
        }

    answer_end = (event.end_x, event.end_y)
    answer = facts(answer_end)
    alternatives = [(p, facts((p.x, p.y))) for p in teammates if p.player_id != receiver.player_id]
    fair = [
        (p, f)
        for p, f in alternatives
        if float(f["lines_broken"]) < float(answer["lines_broken"])
        and float(f["threat_added"]) <= float(answer["threat_added"])
    ]
    if len(fair) < 2:
        return None
    if level >= 3:
        chosen = sorted(fair, key=lambda pf: float(pf[1]["threat_added"]), reverse=True)[:2]
    else:
        backward = min(fair, key=lambda pf: pf[0].x)
        rest = [pf for pf in fair if pf[0].player_id != backward[0].player_id]
        sideways = min(rest, key=lambda pf: abs(pf[0].x - event.start_x))
        chosen = [backward, sideways]
    options: list[_Unkeyed] = [
        # Marked where the receiver stands, like the others, so its place gives nothing away.
        ("Pass to {target}", True, receiver.player_id, (receiver.x, receiver.y), answer),
        *(_pass_option(p, f) for p, f in chosen),
    ]
    return Asks.WHERE_TO_PASS, options


def _pass_option(player: PlayerPosition, facts: Mapping[str, float | str]) -> _Unkeyed:
    return ("Pass to {target}", False, player.player_id, (player.x, player.y), facts)


def _direction(forward_metres: float) -> str:
    if forward_metres > SIDEWAYS:
        return "forward"
    return "backward" if forward_metres < -SIDEWAYS else "sideways"


def _line_breaking_identify(
    candidate: Candidate, level: int, rng: Generator
) -> tuple[Asks, list[_Unkeyed]]:
    evidence = candidate.tag.evidence
    if level == 1:
        lines = min(int(evidence["lines broken"]), len(LINE_COUNTS) - 1)
        first = max(0, lines - 2)
        return Asks.LINES_BROKEN, _labelled(LINE_COUNTS[first : first + 3], lines - first)
    gap = evidence["gap (m)"]
    ranges = _ranges(gap, GAP_EDGES if level == 2 else None, GAP_STEP, rng)
    return Asks.GAP_WIDTH, _range_options(ranges, gap, "m")


def _counter_press_identify(
    candidate: Candidate, level: int, rng: Generator
) -> tuple[Asks, list[_Unkeyed]]:
    if level == 1:
        return Asks.WHAT_THEY_DID, _labelled(WHAT_THEY_DID, 0)
    seconds = candidate.tag.evidence["seconds to win back"]
    ranges = _ranges(seconds, REGAIN_EDGES if level == 2 else None, REGAIN_STEP, rng)
    return Asks.SECONDS_TO_REGAIN, _range_options(ranges, seconds, "s")


def _labelled(labels: Sequence[str], correct: int) -> list[_Unkeyed]:
    return [(label, index == correct, None, None, {}) for index, label in enumerate(labels)]


def _ranges(
    value: float, edges: tuple[float, float] | None, step: float, rng: Generator
) -> list[tuple[float | None, float | None]]:
    """Three ranges covering ``value``: fixed coarse edges, or narrow ones of width ``step``.

    Narrow ranges put the true one first, second or third at random, so its place gives
    nothing away. Each range includes its lower end and excludes its upper end.
    """
    if edges is not None:
        low, high = edges
        return [(None, low), (low, high), (high, None)]
    place = int(rng.random() * 3)
    first = max(0.0, (math.floor(value / step) - place) * step)
    return [(first + i * step, first + (i + 1) * step) for i in range(3)]


def _range_options(
    ranges: list[tuple[float | None, float | None]], value: float, unit: str
) -> list[_Unkeyed]:
    options: list[_Unkeyed] = []
    for low, high in ranges:
        inside = (low is None or value >= low) and (high is None or value < high)
        bounds: dict[str, float | str] = {"unit": unit}
        if low is not None:
            bounds["from"] = low
        if high is not None:
            bounds["to"] = high
        options.append((_range_label(low, high, unit), inside, None, None, bounds))
    return options


def _range_label(low: float | None, high: float | None, unit: str) -> str:
    if low is None:
        return f"Under {high:g} {unit}"
    if high is None:
        return f"{low:g} {unit} or more"
    return f"{low:g} to {high:g} {unit}"


QUESTIONS: Mapping[ConceptId, ConceptQuestions] = {
    ConceptId.LINE_BREAKING_PASS: ConceptQuestions(_line_breaking_form, _line_breaking),
    ConceptId.COUNTER_PRESS: ConceptQuestions(_after_the_play, _counter_press),
}
ASKABLE = frozenset(QUESTIONS)
