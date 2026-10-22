"""What the model is told: its instructions, a prompt per question or feedback, and the schemas.

Each reply must follow its JSON schema.

A question's prompt is built from its question view only, so the model never sees the answer or
any outcome before the viewer answers. A feedback prompt gets the whole pack. Nothing about the
viewer goes in either: no id, no name, no club.

Facts are listed as ``{slot} = value``. The model writes the slot, never the value, and code
fills it in; the values are shown only so it can write naturally. `PROMPT_VERSION` is logged
with every call, so an evaluation's numbers belong to one version of these words.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from btl.learn.evidence import EvidencePack, Fact, QuestionView, Timing
from btl.learn.grader import Grade
from btl.learn.questions import Asks
from btl.tutor.base import NO_HISTORY, History, TutorFeedback
from btl.tutor.model import JsonSchema, ModelRequest
from btl.tutor.slots import feedback_values, question_values
from btl.tutor.verifier import (
    MAX_EXPLANATION_WORDS,
    MAX_QUESTION_WORDS,
    MAX_TAKEAWAY_WORDS,
    Failure,
)

PROMPT_VERSION = 5
LEVEL_NAMES = {1: "beginner", 2: "intermediate", 3: "analyst"}

INSTRUCTIONS = """\
You word questions and feedback for Between the Lines, an app that helps fans understand \
football while they watch a match. Every club and player is fictional.

Rules for everything you write:
- Every number, club, player, time and place comes from the facts you are given, written as its \
slot in curly braces, such as {player} or {answer.threat_added}. Never write a digit, a number \
word (two, half, second, dozen) or a name yourself.
- Clock times (such as 00:32), shirt numbers (such as #10), scores and measurements are numbers \
too: use the slot that holds them, such as {occurred_at} or {player}. Never copy a value you \
were shown into your text.
- Write each fact only as its slot. Its value is filled in for you, so never also write the \
value, in brackets or otherwise, and never add a sign or unit the value already has: write \
"{threat_added}", not "+{threat_added}" or "{threat_added} (+0.1%)". The values are shown only \
so you know what each slot will say.
- Use only the slots listed, exactly as written. Never put anything else in curly braces.
- Read your text with each slot replaced by its value: it must read naturally, with nothing \
said twice.
- Plain British English, short sentences, in the second person where it helps. Use football \
words the concept text uses, and explain any other.
- No betting language: no odds, bets, stakes, tips or wagers.
- Reply only with JSON in the requested shape."""

QUESTION_SCHEMA: JsonSchema = {
    "type": "object",
    "properties": {"text": {"type": "string"}},
    "required": ["text"],
    "additionalProperties": False,
}
FEEDBACK_SCHEMA: JsonSchema = {
    "type": "object",
    "properties": {
        "explanation": {"type": "string"},
        "takeaway": {"type": "string"},
        "misconception": {"type": ["integer", "null"]},
    },
    "required": ["explanation", "takeaway", "misconception"],
    "additionalProperties": False,
}


@dataclass(frozen=True, slots=True)
class Repair:
    """A second try: the model's first reply, and the checks it failed."""

    reply: str
    failures: Sequence[Failure]


def question_request(view: QuestionView, plain: str, repair: Repair | None = None) -> ModelRequest:
    """The request for a question's wording.

    Args:
        view: Everything the viewer may know before answering; nothing else is sent.
        plain: The template's wording of the same question, as a guide to what is asked.
        repair: The first try and why it failed, for a second one.
    """
    keys = {option.key for option in view.options}
    lines = [
        "Word the question the viewer is about to answer.",
        "",
        f"Concept: {view.concept_name}. The viewer is at {LEVEL_NAMES[view.level]} level.",
        f"It asks: {view.asks.value}.",
        _when(view.timing),
        f"A plain version: {plain}",
        "",
        "Facts you may use:",
        *_fact_lines(
            {
                name: value
                for name, value in question_values(view).items()
                if name.split(".")[0] not in keys
            }
        ),
        "",
        "The options the viewer will see, which the question must never point at:",
        *(f"- {option.label}" for option in view.options),
        "",
        "Rules for the question:",
        "- Ask what the plain version asks, in your own words.",
        "- Don't mention an option: not by its letter, not by its slot, and not with words from "
        "the option labels that would tell them apart.",
        f"- At most {MAX_QUESTION_WORDS} words.",
        'Reply as {"text": "..."}.',
    ]
    return _request(lines, "question", QUESTION_SCHEMA, repair)


def feedback_request(
    pack: EvidencePack,
    grade: Grade,
    plain: TutorFeedback,
    repair: Repair | None = None,
    history: History = NO_HISTORY,
) -> ModelRequest:
    """The request for the feedback after an answer, from the whole pack.

    Args:
        pack: Everything about the question.
        grade: The viewer's answer, graded.
        plain: The template's feedback, which passes every check, as a starting point.
        repair: The first try and why it failed, for a second one.
        history: The viewer's recent answers on the concept; no id, no name, no club.
    """
    right = next(option for option in pack.options if option.correct)
    picked = next((option for option in pack.options if option.key == grade.chosen), None)
    level = LEVEL_NAMES[pack.level]
    explanation = {
        "beginner": pack.concept.beginner,
        "intermediate": pack.concept.intermediate,
        "analyst": pack.concept.analyst,
    }[level]
    lines = [
        "Word the feedback after the viewer answered.",
        "",
        f"Concept: {pack.concept.name}. The viewer is at {level} level.",
        f"It asked: {pack.asks.value}.",
        f"The right answer is {right.key}: {right.label}.",
        (
            "The viewer picked it."
            if grade.correct
            else "The viewer picked "
            + (f"{picked.key}: {picked.label}." if picked is not None else "nothing.")
        ),
        "",
        f"The concept, explained at {level} level (its slots are facts below):",
        explanation,
        f"What the viewer should take away: {pack.concept.objective}",
        "",
        "A plain version, which follows every rule:",
        f"Explanation: {plain.explanation}",
        f"Takeaway: {plain.takeaway}",
        "Write a clearer, more natural version for this viewer. Keep {answer} and the outcome "
        "slots the plain version uses.",
        "",
        "Facts known before answering:",
        *_fact_lines({**_shown(pack.context), **_timing(pack.timing)}),
        "Facts that answer the question (outcome facts):",
        *_fact_lines(_shown(pack.outcome)),
        "Write outcome facts as listed, with nothing in front of the name.",
        f"{{answer}} = {right.label} (the right option)",
        *([f"{{chosen}} = {picked.label} (the viewer's pick)"] if picked is not None else []),
        *_option_section(pack),
        *_sentence_note(feedback_values(pack, grade.chosen)),
        "",
        *_history_lines(history),
        "Common mix-ups for this concept, by number:",
        *(f"{index}. {text}" for index, text in enumerate(pack.concept.misconceptions, start=1)),
        "",
        "Rules for the feedback:",
        "- The verdict has already been shown, so never say the answer was right or wrong "
        '(no "correct", "wrong", "well done", "not quite").',
        "- The explanation must contain {answer} itself, or one of the right option's own "
        "facts, and at least one outcome fact.",
        *(
            ["- Compare the right pass with the viewer's, citing a {chosen.*} fact."]
            if pack.asks is Asks.WHERE_TO_PASS and not grade.correct
            else []
        ),
        '- If you compare the same fact for two options with words like "more" or "fewer", '
        'the order must match the values. Don\'t use "better" or "faster" for that.',
        f"- explanation: at most {MAX_EXPLANATION_WORDS} words.",
        f"- takeaway: one sentence, at most {MAX_TAKEAWAY_WORDS} words.",
        "- misconception: "
        + (
            "null."
            if grade.correct
            else "the number of the mix-up that best fits the viewer's pick, or null if none fits."
        ),
        'Reply as {"explanation": "...", "takeaway": "...", "misconception": null}.',
    ]
    return _request(lines, "feedback", FEEDBACK_SCHEMA, repair)


def _request(
    lines: list[str], name: str, schema: JsonSchema, repair: Repair | None
) -> ModelRequest:
    if repair is not None:
        lines += [
            "",
            "Your last reply was:",
            repair.reply,
            "It failed these checks, so write it again and fix each one:",
            *(f"- {failure.check}: {failure.reason}" for failure in repair.failures),
        ]
    return ModelRequest(INSTRUCTIONS, "\n".join(lines), name, schema)


def _when(timing: Timing) -> str:
    if timing.delivery == "live":
        return "It is asked live, the moment it happens; play is paused on it."
    place = "a stoppage for a {restart}" if timing.restart else timing.delivered_phase.value
    return (
        f"It is asked later, at {place}, about a moment that happened at {{occurred_at}}. "
        "Say first where play is and when the moment happened."
    )


def _history_lines(history: History) -> list[str]:
    if not history.recent:
        return []
    answers = ", ".join("right" if right else "wrong" for right in history.recent)
    lines = [f"The viewer's recent answers on this concept, oldest first: {answers}."]
    if history.last_wrong is not None:
        lines.append(f"Their last wrong answer was to a question asking: {history.last_wrong}.")
    return [
        *lines,
        "Open the explanation with one short, kind clause about these answers, in words only: "
        'never count them. For example "You\'ve been reading these well lately, but…" or '
        '"This kind has tripped you up before:".',
        "",
    ]


def _option_section(pack: EvidencePack) -> list[str]:
    own = [name for option in pack.options for name in {**option.neutral, **option.outcome}]
    if not own:
        return ["The options have no facts of their own: {answer} and {chosen} are their labels."]
    example = own[0]
    return [
        "The options and their own facts. The right option's facts can also be written with "
        f"\"answer.\" in front, such as {{answer.{example}}}, and the viewer's pick's with "
        f'"chosen." in front, such as {{chosen.{example}}}:',
        *(
            line
            for option in pack.options
            for line in _option_lines(option.key, option.label, option.neutral, option.outcome)
        ),
    ]


def _sentence_note(values: Mapping[str, str]) -> list[str]:
    sentences = [f"{{{name}}}" for name, value in values.items() if _sentence(value)]
    if not sentences:
        return []
    return [
        f"These facts are whole sentences: {', '.join(sentences)}. Use each on its own, never "
        "inside another sentence."
    ]


def _option_lines(
    key: str, label: str, neutral: Mapping[str, Fact], outcome: Mapping[str, Fact]
) -> list[str]:
    facts = {f"{key}.{name}": fact.display for name, fact in {**neutral, **outcome}.items()}
    return [f"- {key}: {label}", *(f"  {line}" for line in _fact_lines(facts))]


def _fact_lines(values: Mapping[str, str]) -> list[str]:
    return [f"{{{name}}} = {value}" for name, value in values.items()] or ["(none)"]


def _sentence(value: str) -> bool:
    return value.endswith(".") and " " in value


def _shown(facts: Mapping[str, Fact]) -> dict[str, str]:
    return {name: fact.display for name, fact in facts.items()}


def _timing(timing: Timing) -> dict[str, str]:
    values = {"occurred_at": timing.occurred_at, "delivered_at": timing.delivered_at}
    if timing.restart is not None:
        values["restart"] = timing.restart
    return values
