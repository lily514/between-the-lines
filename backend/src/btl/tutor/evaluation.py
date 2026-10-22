"""Measuring the model's Tutor: how often its words pass, get repaired, or fall back.

`evaluate` asks a `VerifiedTutor` for every pack's question and for its feedback after a right
pick and after a wrong one (which comes after a sample of recent answers, so the prompt's
history part is measured too), keeping every try's `CheckRecord`. `report` turns that into
tables: pass rates overall, by concept and by kind of question, which checks failed, and the time
and tokens it took. `review_sheet` picks samples of the model's words, beside the template's,
for a person to judge what no check can: whether they are true, pitched right and natural.
"""

import statistics
from collections import Counter
from collections.abc import Iterable, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Literal

from btl.learn.evidence import EvidencePack, Fact, question_view
from btl.learn.grader import Grade
from btl.tutor.base import NO_HISTORY, History, Tutor, TutorFeedback
from btl.tutor.foundry import FoundryTutor
from btl.tutor.slots import feedback_values, fill, question_values
from btl.tutor.verified import CheckRecord, VerifiedTutor
from btl.tutor.verifier import CHECKS

Shown = Literal["first try", "repaired", "template"]
# The recent answers a wrong pick is measured after: right, right, then wrong.
SAMPLE_RECENT = (True, True, False)


@dataclass(frozen=True, slots=True)
class Worded:
    """One wording asked for, how it went, and the words shown (slots filled) beside the template's.

    ``right`` is None for a question, and says whether the pick was right for feedback.
    """

    kind: Literal["question", "feedback"]
    concept: str
    asks: str
    level: int
    delivery: str
    right: bool | None
    shown: Shown
    records: tuple[CheckRecord, ...]
    text: str
    template: str
    facts: str


def evaluate(
    primary: FoundryTutor, fallback: Tutor, packs: Sequence[EvidencePack], workers: int = 4
) -> list[Worded]:
    """Word every pack's question and its feedback after a right and a wrong pick.

    Packs are worded side by side by ``workers`` threads; the results keep the packs' order.
    """

    def word(pack: EvidencePack) -> list[Worded]:
        return _word_pack(primary, fallback, pack)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        return [worded for words in pool.map(word, packs) for worded in words]


def _word_pack(primary: FoundryTutor, fallback: Tutor, pack: EvidencePack) -> list[Worded]:
    view = question_view(pack)
    records: list[CheckRecord] = []
    tutor = VerifiedTutor(primary, fallback, records.append)
    question = tutor.question(view).text
    plain = fallback.question(view).text
    values = question_values(view)
    results = [
        _worded(pack, "question", None, records, fill(question, values), fill(plain, values))
    ]
    wrong = next(option for option in pack.options if not option.correct)
    for chosen, right in ((pack.correct_key, True), (wrong.key, False)):
        records = []
        tutor = VerifiedTutor(primary, fallback, records.append)
        grade = Grade(correct=right, chosen=chosen)
        values = feedback_values(pack, chosen)
        # A wrong pick comes after some history, so the prompt's history part is measured too.
        history = NO_HISTORY if right else History(SAMPLE_RECENT, pack.asks.value)
        feedback = _filled(tutor.feedback(pack, grade, history), values)
        template = _filled(fallback.feedback(pack, grade), values)
        results.append(_worded(pack, "feedback", right, records, feedback, template))
    return results


def _filled(feedback: TutorFeedback, values: dict[str, str]) -> str:
    parts = [fill(feedback.explanation, values), f"Takeaway: {fill(feedback.takeaway, values)}"]
    if feedback.misconception is not None:
        parts.append(f"Common mix-up: {fill(feedback.misconception, values)}")
    return "\n".join(parts)


def _worded(
    pack: EvidencePack,
    kind: Literal["question", "feedback"],
    right: bool | None,
    records: list[CheckRecord],
    text: str,
    template: str,
) -> Worded:
    passed = next((record.attempt for record in records if record.passed), None)
    shown: Shown = "template" if passed is None else "first try" if passed == 1 else "repaired"
    return Worded(
        kind=kind,
        concept=pack.concept.name,
        asks=pack.asks.value,
        level=pack.level,
        delivery=pack.timing.delivery,
        right=right,
        shown=shown,
        records=tuple(records),
        text=text,
        template=template,
        facts=_facts(pack),
    )


def _facts(pack: EvidencePack) -> str:
    def listed(facts: Iterable[tuple[str, Fact]]) -> str:
        return "; ".join(f"{name} = {fact.display}" for name, fact in facts)

    options = " | ".join(
        f"{option.key}{' (right)' if option.correct else ''}: {option.label}"
        for option in pack.options
    )
    return (
        f"Before answering: {listed(pack.context.items())}\n"
        f"Outcome: {listed(pack.outcome.items())}\n"
        f"Options: {options}"
    )


def report(
    words: Sequence[Worded],
    prompt_version: int,
    model: str,
    price_in: float | None = None,
    price_out: float | None = None,
) -> str:
    """The evaluation as Markdown: pass rates, failed checks, time, tokens and (with prices) cost.

    Prices are in US dollars per million tokens.
    """
    calls = [record for worded in words for record in worded.records]
    answered = [record for record in calls if record.error is None]
    lines = [
        f"Prompt version {prompt_version}, model {model}: {len(words)} wordings, "
        f"{len(calls)} calls.",
        "",
        "### Pass rates",
        "",
        *_rates_table("What", [("Questions", "question"), ("Feedback", "feedback")], words),
        "",
        "### By concept",
        "",
        *_rates_table(
            "Concept",
            [(concept, concept) for concept in dict.fromkeys(w.concept for w in words)],
            words,
            by="concept",
        ),
        "",
        "### By kind of question",
        "",
        *_rates_table(
            "Asks",
            [(asks, asks) for asks in dict.fromkeys(w.asks for w in words)],
            words,
            by="asks",
        ),
        "",
        "### Checks failed on the first try",
        "",
        *_checks_table(words),
        "",
        "### Time and tokens",
        "",
        *_cost_lines(calls, answered, price_in, price_out),
    ]
    return "\n".join(lines) + "\n"


def _rates_table(
    heading: str,
    groups: Sequence[tuple[str, str]],
    words: Sequence[Worded],
    by: Literal["kind", "concept", "asks"] = "kind",
) -> list[str]:
    rows = [
        f"| {heading} | Wordings | First try | Repaired | Template | Model-worded |",
        "|---|---|---|---|---|---|",
    ]
    for name, value in [*groups, ("All", "")]:
        group = [w for w in words if not value or _group(w, by) == value]
        counts = Counter(w.shown for w in group)
        total = len(group)
        model = counts["first try"] + counts["repaired"]
        rows.append(
            f"| {name} | {total} | {_share(counts['first try'], total)} | "
            f"{_share(counts['repaired'], total)} | {_share(counts['template'], total)} | "
            f"{_share(model, total)} |"
        )
    return rows


def _group(worded: Worded, by: Literal["kind", "concept", "asks"]) -> str:
    if by == "kind":
        return worded.kind
    return worded.concept if by == "concept" else worded.asks


def _checks_table(words: Sequence[Worded]) -> list[str]:
    firsts = [r for w in words for r in w.records if r.attempt == 1]
    failed = Counter(reason for record in firsts for reason in record.reasons)
    errors = sum(record.error is not None for record in firsts)
    rows = ["| Check | First tries failing it |", "|---|---|"]
    rows += [f"| {check} | {_share(failed[check], len(firsts))} |" for check in CHECKS]
    rows.append(f"| (no reply) | {_share(errors, len(firsts))} |")
    return rows


def _cost_lines(
    calls: Sequence[CheckRecord],
    answered: Sequence[CheckRecord],
    price_in: float | None,
    price_out: float | None,
) -> list[str]:
    seconds = sorted(record.seconds for record in answered)
    tokens_in = sum(record.input_tokens for record in calls)
    tokens_out = sum(record.output_tokens for record in calls)
    lines = [
        f"- Calls: {len(calls)}, of which {len(calls) - len(answered)} got no usable reply.",
        f"- Seconds per call: median {_percentile(seconds, 50):.2f}, "
        f"95th percentile {_percentile(seconds, 95):.2f}.",
        f"- Tokens: {tokens_in:,} in, {tokens_out:,} out.",
    ]
    if price_in is not None and price_out is not None:
        cost = (tokens_in * price_in + tokens_out * price_out) / 1_000_000
        per = cost / len(calls) if calls else 0.0
        lines.append(f"- Estimated cost: ${cost:.4f} (${per:.6f} a call).")
    return lines


def _percentile(values: Sequence[float], percent: int) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]
    return statistics.quantiles(values, n=100, method="inclusive")[percent - 1]


def _share(count: int, total: int) -> str:
    return f"{count} ({count / total:.0%})" if total else "0"


def review_sheet(words: Sequence[Worded], per_concept: int = 4) -> str:
    """Samples of the model's words beside the template's, as Markdown, for a person to judge.

    Each concept gets ``per_concept`` samples, half questions and half feedback where it can,
    taking a new kind of question each time before repeating one.
    """
    model = [w for w in words if w.shown != "template"]
    chosen: list[Worded] = []
    for concept in dict.fromkeys(w.concept for w in model):
        for kind in ("question", "feedback"):
            pool = [w for w in model if w.concept == concept and w.kind == kind]
            chosen += _varied(pool, per_concept // 2)
    lines = [
        "# The AI Tutor: hand review",
        "",
        "For each sample, tick what holds, and note anything wrong. The facts are what the "
        "words may say; the template's wording is there for comparison.",
        "",
    ]
    for number, worded in enumerate(chosen, start=1):
        pick = (
            ""
            if worded.right is None
            else (" after a right pick" if worded.right else " after a wrong pick")
        )
        lines += [
            f"### {number}. {worded.concept}: {worded.asks}, level {worded.level}, "
            f"{worded.delivery}, {worded.kind}{pick} ({worded.shown})",
            "",
            "**Model**",
            "",
            *_quoted(worded.text),
            "",
            "**Template**",
            "",
            *_quoted(worded.template),
            "",
            "<details><summary>Facts</summary>",
            "",
            *_quoted(worded.facts),
            "",
            "</details>",
            "",
            "- [ ] True to the evidence",
            "- [ ] Right for the level",
            *(["- [ ] Gives nothing away before answering"] if worded.kind == "question" else []),
            "- [ ] Reads naturally",
            "- Notes:",
            "",
        ]
    return "\n".join(lines)


def _varied(pool: Sequence[Worded], count: int) -> list[Worded]:
    picked: list[Worded] = []
    seen: set[str] = set()
    for worded in [*pool, *pool]:
        if len(picked) == count:
            break
        if worded in picked or (worded.asks in seen and len(seen) < len({w.asks for w in pool})):
            continue
        picked.append(worded)
        seen.add(worded.asks)
    return picked


def _quoted(text: str) -> list[str]:
    return [f"> {line}" if line else ">" for line in text.splitlines()]
