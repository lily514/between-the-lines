"""Questions: what to ask about a candidate moment, and its three answer options.

The form depends on the concept, the moment, the viewer's level and when the question is asked:

- A line-breaking pass asked live at level 2 or 3 is a **predict** question: play stops before
  the pass, and the options are passes to three teammates.
- A restart, and a foul that stops play, is predicted at the stoppage: what happens now? A
  booking for stopping a promising attack is instead identified there, at level 2 or 3.
- An offside call asked live is predicted before the pass: will the flag go up, or, at level
  2, which attacker is in an offside position.
- Everything else is an **identify** question about play the viewer has just seen: a
  line-breaking pass asked at level 1 or after a delay, every counter-press, since a
  counter-press happens during a transition and is never asked live, an offside call asked
  later, why the referee played advantage, every ball win, which opens a transition (how it
  was won, then which third, then why that matters), every shot (what came of it, where from,
  how the chance came), and every counter-attack (what the team did next, how long it took to
  reach the box, why it counts as one).

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

from btl.concepts.ball_win import THIRDS, WonWith, pitch_third
from btl.concepts.base import MatchContext
from btl.concepts.line_breaking import LineBreakingPass
from btl.concepts.offside import HALFWAY, offside_line
from btl.concepts.shot import ChanceFrom, ShotOutcome, ShotZone
from btl.learn.candidates import AskedWhen, Candidate
from btl.learn.concept_map import ConceptKey, ConceptMap
from btl.learn.knowledge import Delivery
from btl.schema.ids import ActionId, PlayerId
from btl.schema.snapshot import PlayerPosition
from btl.schema.vocab import ActionType, ConceptId
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
# Option labels may use the pack's context facts as slots: {team} is the team of the moment's
# key action, {opponent} the other one, {attacker} the player an offside call is about.
OFFSIDE_YES = "Yes: {attacker} is past the second-last defender"
OFFSIDE_NO = {
    "the second-last defender": "No: {attacker} is level with or behind the second-last defender",
    "the ball": "No: {attacker} is behind the ball",
    "halfway": "No: {attacker} is in their own half",
}
# Always a wrong reason: the misconception about when offside is judged.
OFFSIDE_WHEN_IT_ARRIVES = "No: offside only counts where {attacker} is when the ball arrives"
BOOKING_REASONS = (
    "For stopping a promising attack",
    "Every foul gets a booking",
    "To make up for not giving a penalty",
)
ADVANTAGE_REASONS = (
    "{opponent} kept the ball, so stopping play would have helped {team}",
    "The referee didn't see the foul",
    "A foul in the middle of the pitch isn't punished",
)
# How the ball was won, as options; the right one plus the first two others.
WON_WITH = {
    WonWith.TACKLE: "A tackle",
    WonWith.INTERCEPTION: "An interception",
    WonWith.KEEPER: "The keeper gathered it",
    WonWith.LOOSE_BALL: "A loose ball",
}
WHICH_THIRD = ("Their own third", "The middle third", "The attacking third")
# Why the third a ball is won in matters, one reason per third, and the map's misconception
# as the distractor (a test keeps it the same as the map's wording).
WHY_THE_THIRD_MATTERS = (
    "Won deep, so the whole pitch is still ahead of them before a chance",
    "Won in midfield, while the opponent is still turning, with ground to cover",
    "Won high up, so they are near goal before the defence is set",
)
DEEP_WINS_ARE_JUST_AS_USEFUL = (
    "Winning the ball deep in your own half is just as useful as winning it high"
)
# A shot's outcome, where it was from, and what made the chance, as options.
SHOT_OUTCOMES = {
    ShotOutcome.SCORED: "Scored",
    ShotOutcome.SAVED: "Saved",
    ShotOutcome.OFF_TARGET: "Off target",
}
SHOT_ZONES = {
    ShotZone.SIX_YARD_BOX: "From the six-yard box",
    ShotZone.PENALTY_AREA: "From the penalty area",
    ShotZone.OUTSIDE_THE_BOX: "From outside the box",
}
CHANCE_SOURCES = {
    ChanceFrom.CROSS: "From a cross",
    ChanceFrom.PASS: "From a pass",
    ChanceFrom.DRIBBLE: "From a dribble",
    ChanceFrom.FREE_KICK: "From a free kick",
    ChanceFrom.LOOSE_BALL: "From a loose ball",
}
# What a team did after winning the ball in its own half; a counter-attack went for goal.
AFTER_WINNING_IT = ("Went straight for goal", "Built up slowly", "Lost it again")
# Seconds-to-the-box ranges for the level-2 identify question, around the planted levels.
BOX_EDGES = (8.0, 10.0)
BOX_STEP = 2.0
# Why it was a counter-attack: the right reason, the map's misconception, and a wrong reason
# (a test keeps the misconception the same as the map's wording).
WHY_A_COUNTER = (
    "They went for goal at once, while the defence was still out of shape",
    "A counterattack is any fast attack",
    "They had most of the possession before the chance came",
)
ANY_FAST_ATTACK = WHY_A_COUNTER[1]


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
    WHAT_RESTART = "what restart"
    FLAG_OR_NOT = "flag or not"
    WHO_IS_OFFSIDE = "who is offside"
    WAS_IT_OFFSIDE = "was it offside"
    AFTER_THE_FOUL = "after the foul"
    WHY_BOOKED = "why booked"
    WHY_PLAY_ON = "why play on"
    HOW_WON = "how won"
    WHERE_WON = "where won"
    WHY_WHERE_MATTERS = "why where matters"
    ON_TARGET = "on target"
    WHERE_FROM = "where from"
    HOW_THE_CHANCE_CAME = "how the chance came"
    WHAT_NEXT_AFTER_WINNING = "what next after winning it"
    SECONDS_TO_BOX = "seconds to the box"
    WHY_A_COUNTER_ATTACK = "why a counter-attack"


@dataclass(frozen=True, slots=True)
class Option:
    """One answer the viewer can pick.

    ``label`` is written by code. A pass option's label holds a ``{target}`` slot for the
    receiver's name, which the evidence pack fills in, as it does the context facts a label
    names, such as ``{team}``. ``facts`` are measured, never written:
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

    ``form`` gives the form for a moment at a level and delivery. ``build`` gives what the
    question asks and its options, unshuffled with exactly one correct, or None if no fair set
    exists.
    """

    form: Callable[[Candidate, int, Delivery], Form]
    build: Callable[[Candidate, int, Form, MatchContext, ThreatModel, Generator], _Built]


def active_concepts(concept_map: ConceptMap) -> tuple[ConceptKey, ...]:
    """The map's concepts the app can ask about: those whose detector has questions here."""
    return tuple(c.key for c in concept_map.concepts if c.detector in ASKABLE)


def question_form(candidate: Candidate, level: int, delivery: Delivery) -> Form:
    """The form a question about a moment takes at a level and delivery."""
    return QUESTIONS[candidate.tag.concept].form(candidate, level, delivery)


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
        the real one; for which attacker is offside, not exactly one is; and advantage below
        level 3.
    """
    concept = candidate.tag.concept
    if concept not in QUESTIONS:
        raise ValueError(f"no questions exist for {concept}")
    asking = QUESTIONS[concept]
    form = asking.form(candidate, level, delivery)
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


def _line_breaking_form(candidate: Candidate, level: int, delivery: Delivery) -> Form:
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


def _after_the_play(candidate: Candidate, level: int, delivery: Delivery) -> Form:
    # A counter-press, a ball win or a counter-attack happens in a transition, and a shot's
    # result is its answer, so these are only asked after the play.
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


def _what_happens_now(candidate: Candidate, level: int, delivery: Delivery) -> Form:
    return Form.PREDICT


def _restart(
    candidate: Candidate,
    level: int,
    form: Form,
    ctx: MatchContext,
    threat: ThreatModel,
    rng: Generator,
) -> _Built:
    """The right restart, the other team's restart on that line, and one from the other line.

    How hard it is comes from the moment, not from the options: the levels take different
    moments, such as a ball off a defender at level 3.
    """
    first, last = candidate.tag.span
    restart = ctx.events[last]
    ours = "{team}" if restart.team_id == ctx.events[first].team_id else "{opponent}"
    theirs = "{opponent}" if ours == "{team}" else "{team}"
    if restart.action_type is ActionType.THROW_IN:
        labels = (f"Throw-in to {ours}", f"Throw-in to {theirs}", f"Corner to {ours}")
    elif restart.action_type is ActionType.GOALKICK:
        labels = (f"Goal kick to {ours}", f"Corner to {theirs}", f"Throw-in to {ours}")
    else:
        labels = (f"Corner to {ours}", f"Goal kick to {theirs}", f"Throw-in to {ours}")
    return Asks.WHAT_RESTART, _labelled(labels, 0)


def _offside_form(candidate: Candidate, level: int, delivery: Delivery) -> Form:
    return Form.PREDICT if delivery is Delivery.LIVE else Form.IDENTIFY


def _offside(
    candidate: Candidate,
    level: int,
    form: Form,
    ctx: MatchContext,
    threat: ThreatModel,
    rng: Generator,
) -> _Built:
    if level == 2:
        return _who_is_offside(candidate, ctx)
    asks = Asks.FLAG_OR_NOT if form is Form.PREDICT else Asks.WAS_IT_OFFSIDE
    if candidate.tag.evidence["offside"]:
        labels = (OFFSIDE_YES, OFFSIDE_NO["the second-last defender"], OFFSIDE_WHEN_IT_ARRIVES)
    else:
        reason = OFFSIDE_NO[offside_reference(candidate, ctx)]
        labels = (reason, OFFSIDE_YES, OFFSIDE_WHEN_IT_ARRIVES)
    return asks, _labelled(labels, 0)


def offside_reference(candidate: Candidate, ctx: MatchContext) -> str:
    """What made the offside line at an offside moment: the furthest forward of three.

    Returns:
        "the second-last defender", "the ball" or "halfway".
    """
    event = ctx.events[candidate.tag.action_id]
    line = candidate.tag.evidence["line (m)"]
    if line == round(HALFWAY, 1):
        return "halfway"
    return "the ball" if line == round(event.start_x, 1) else "the second-last defender"


def _who_is_offside(candidate: Candidate, ctx: MatchContext) -> _Built:
    """Three attackers as the pass is played, exactly one in an offside position.

    The other two are the onside attackers nearest the line, so the call is close.
    """
    event = ctx.events[candidate.tag.action_id]
    snapshot = ctx.snapshot(event.action_id)
    line = None if snapshot is None else offside_line(snapshot, event)
    if snapshot is None or line is None:
        return None
    attackers = [
        p
        for p in snapshot.positions
        if p.team_id == event.team_id and not p.is_actor and not p.is_goalkeeper
    ]
    offside = [p for p in attackers if p.x > line]
    onside = sorted((p for p in attackers if p.x <= line), key=lambda p: line - p.x)
    if len(offside) != 1 or len(onside) < 2:
        return None
    options: list[_Unkeyed] = [
        ("{target}", player is offside[0], player.player_id, (player.x, player.y), {})
        for player in (offside[0], *onside[:2])
    ]
    return Asks.WHO_IS_OFFSIDE, options


def _foul_form(candidate: Candidate, level: int, delivery: Delivery) -> Form:
    if candidate.asked_when is AskedWhen.AFTERWARDS:
        return Form.IDENTIFY
    return Form.IDENTIFY if level >= 2 and _explained_booking(candidate) else Form.PREDICT


def _explained_booking(candidate: Candidate) -> bool:
    evidence = candidate.tag.evidence
    return bool(evidence["booked"] and evidence["promising attack"])


def _foul(
    candidate: Candidate,
    level: int,
    form: Form,
    ctx: MatchContext,
    threat: ThreatModel,
    rng: Generator,
) -> _Built:
    if candidate.tag.evidence["advantage"]:
        return None if level < 3 else (Asks.WHY_PLAY_ON, _labelled(ADVANTAGE_REASONS, 0))
    if form is Form.IDENTIFY:
        return Asks.WHY_BOOKED, _labelled(BOOKING_REASONS, 0)
    # {team} fouled, so {opponent} restart.
    if candidate.tag.evidence["penalty"]:
        labels = ("Penalty to {opponent}", "Free kick to {opponent}", "Free kick to {team}")
    else:
        labels = ("Free kick to {opponent}", "Penalty to {opponent}", "Free kick to {team}")
    return Asks.AFTER_THE_FOUL, _labelled(labels, 0)


def _ball_win(
    candidate: Candidate,
    level: int,
    form: Form,
    ctx: MatchContext,
    threat: ThreatModel,
    rng: Generator,
) -> _Built:
    """How the ball was won, then which third, then why the third matters."""
    evidence = candidate.tag.evidence
    if level == 1:
        won_with = WonWith(int(evidence["won with"]))
        others = [way for way in WonWith if way is not won_with][:2]
        return Asks.HOW_WON, _labelled([WON_WITH[won_with], *(WON_WITH[w] for w in others)], 0)
    third = THIRDS.index(pitch_third(evidence["metres from own goal"]))
    if level == 2:
        return Asks.WHERE_WON, _labelled(WHICH_THIRD, third)
    another = next(i for i in range(len(THIRDS)) if i != third)
    reasons = (
        WHY_THE_THIRD_MATTERS[third],
        DEEP_WINS_ARE_JUST_AS_USEFUL,
        WHY_THE_THIRD_MATTERS[another],
    )
    return Asks.WHY_WHERE_MATTERS, _labelled(reasons, 0)


def _shot(
    candidate: Candidate,
    level: int,
    form: Form,
    ctx: MatchContext,
    threat: ThreatModel,
    rng: Generator,
) -> _Built:
    """How the shot ended, then where it was from, then what made the chance."""
    evidence = candidate.tag.evidence
    if level == 1:
        outcome = ShotOutcome(int(evidence["outcome"]))
        return Asks.ON_TARGET, _labelled(
            list(SHOT_OUTCOMES.values()), list(SHOT_OUTCOMES).index(outcome)
        )
    if level == 2:
        zone = ShotZone(int(evidence["zone"]))
        return Asks.WHERE_FROM, _labelled(list(SHOT_ZONES.values()), list(SHOT_ZONES).index(zone))
    source = ChanceFrom(int(evidence["chance from"]))
    others = [way for way in ChanceFrom if way is not source][:2]
    labels = [CHANCE_SOURCES[source], *(CHANCE_SOURCES[way] for way in others)]
    return Asks.HOW_THE_CHANCE_CAME, _labelled(labels, 0)


def _counter_attack(
    candidate: Candidate,
    level: int,
    form: Form,
    ctx: MatchContext,
    threat: ThreatModel,
    rng: Generator,
) -> _Built:
    """What the team did next, then how long it took to reach the box, then why it counts."""
    if level == 1:
        return Asks.WHAT_NEXT_AFTER_WINNING, _labelled(AFTER_WINNING_IT, 0)
    if level == 2:
        seconds = candidate.tag.evidence["seconds to the box"]
        ranges = _ranges(seconds, BOX_EDGES, BOX_STEP, rng)
        return Asks.SECONDS_TO_BOX, _range_options(ranges, seconds, "s")
    return Asks.WHY_A_COUNTER_ATTACK, _labelled(WHY_A_COUNTER, 0)


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
    ConceptId.RESTART: ConceptQuestions(_what_happens_now, _restart),
    ConceptId.OFFSIDE: ConceptQuestions(_offside_form, _offside),
    ConceptId.FOUL: ConceptQuestions(_foul_form, _foul),
    ConceptId.BALL_WIN: ConceptQuestions(_after_the_play, _ball_win),
    ConceptId.SHOT: ConceptQuestions(_after_the_play, _shot),
    ConceptId.COUNTER_ATTACK: ConceptQuestions(_after_the_play, _counter_attack),
}
ASKABLE = frozenset(QUESTIONS)
