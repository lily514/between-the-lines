"""The Verifier: plain-code checks a Tutor's wording must pass before the viewer sees it.

A model writes words around ``{slots}``; code fills the slots from the evidence pack. The
Verifier makes sure the words can't smuggle in anything the pack doesn't say: a number, a name,
the answer before it is given, a verdict, or a comparison the facts contradict. It is strict on
purpose. A false rejection costs only a template sentence; a false acceptance puts a wrong claim
in front of a learner.

Each check has a name, used as the reason in logs, in the message asking the model to repair
its text, and in the evaluation. `docs/milestone-2b/verifier.md` explains each with an example.

What no check can do is tell whether a football explanation is true, or pitched at the right
level; the evaluation's hand review covers that.
"""

import re
from collections.abc import Mapping
from dataclasses import dataclass

from btl.learn.evidence import EvidencePack, Fact, PackOption, QuestionView
from btl.learn.grader import Grade
from btl.learn.questions import Asks
from btl.tutor.slots import SLOT, SlotError, feedback_values, fill, question_values, slot_names

MAX_QUESTION_WORDS = 45
MAX_EXPLANATION_WORDS = 90
MAX_TAKEAWAY_WORDS = 25

# Words that state a number. "One", "first", "last" and "once" are left out: they are far more
# often a pronoun or an adverb ("this one", "drop back first", "at once") than a count.
NUMBER_WORDS = frozenset((
    "zero", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven",
    "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen",
    "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety", "hundred",
    "thousand", "million", "dozen", "half", "quarter", "twice", "double", "triple", "treble",
    "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth", "ninth", "tenth",
))  # fmt: skip
# Football phrases made of number words that state no number. They are taken out before looking.
FOOTBALL_PHRASES = re.compile(
    r"\b(?:second[- ]last defender|second[- ]last|half[- ]?time|half[- ]?way|first half|"
    r"second half|(?:own|other|opposing|opposition'?s?|team'?s|their|his|its|the attacking|"
    r"the defending) half)\b",
    re.IGNORECASE,
)
# Capitalised words any wording may use mid-sentence, besides the pack's own names.
ALLOWED_NAMES = frozenset({"I", "Expected", "Threat", "Laws", "Law", "Game", "VAR"})
BETTING_WORDS = re.compile(
    r"\b(?:odds|bets?|betting|wagers?|stakes?|tips?|tipster|punts?|punter|bookmakers?|bookies?|"
    r"accumulators?|gambl\w*)\b",
    re.IGNORECASE,
)
VERDICT_PHRASES = re.compile(
    r"\b(?:correct(?:ly)?|incorrect(?:ly)?|wrong|well done|not quite|good job|great job|"
    r"nice one|spot on|unlucky|you got it|you were right|right answer|exactly right|"
    r"good (?:pick|call|read)|bad (?:pick|call|read))\b",
    re.IGNORECASE,
)
# Words that say nothing about which option is right, even when only some labels use them:
# words that join a label's other words, and words any question about football uses.
LABEL_STOPWORDS = frozenset((
    "a", "an", "the", "to", "of", "for", "in", "on", "at", "by", "and", "or", "with", "from", "is",
    "was", "are", "it", "its", "be", "they", "their", "his", "her", "when", "where", "what", "why",
    "how", "only", "so", "would", "have", "has", "had", "did", "do", "ball", "back", "play",
    "played", "stopped", "player", "players", "team", "referee", "pitch", "match", "game",
))  # fmt: skip
# An option named by its letter: "option B", "(C)", "B)", or a lone B or C.
OPTION_LETTER = re.compile(
    r"\b(?:option|answer|choice)s?\s+[A-D]\b|\([A-D]\)|\b[A-D][):]|"
    r"(?<![\w'\u2019-])[B-D](?![\w'\u2019-])"
)
MORE_WORDS = frozenset((
    "more", "higher", "bigger", "greater", "larger", "wider", "longer", "further", "farther",
    "deeper",
))  # fmt: skip
FEWER_WORDS = frozenset(["fewer", "less", "lower", "smaller", "narrower", "shorter"])
UNORDERED_COMPARATIVES = re.compile(
    r"\b(?:than|faster|quicker|slower|sooner|later|better|worse|most|least)\b", re.IGNORECASE
)
CHECKS = (
    "slots",
    "bare_number",
    "names",
    "vocabulary",
    "hint",
    "verdict",
    "grounded",
    "comparison",
    "misconception",
    "echo",
    "length",
)
WORD = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ][A-Za-zÀ-ÖØ-öø-ÿ'\u2019-]*")
# Where a sentence, or a clause after a colon, starts: its first word may be capitalised.
SENTENCE_END = re.compile(r"(?<=[.!?:])\s+")
FULL_STOP = re.compile(r"(?<=[.!?])\s+")


@dataclass(frozen=True, slots=True)
class Failure:
    """One failed check: its name, and what was wrong, for logs and for a repair request."""

    check: str
    reason: str


@dataclass(frozen=True, slots=True)
class Check:
    """The Verifier's result: every failure found; none means the wording may be shown."""

    failures: tuple[Failure, ...]

    @property
    def passed(self) -> bool:
        """Whether every check passed."""
        return not self.failures

    @property
    def reasons(self) -> tuple[str, ...]:
        """The names of the failed checks, each once, in the order found."""
        return tuple(dict.fromkeys(failure.check for failure in self.failures))


@dataclass(frozen=True, slots=True)
class FeedbackText:
    """Feedback as a Tutor writes it: two texts with slots, and which misconception it offers.

    ``misconception`` indexes the concept's misconceptions in the pack; None offers none.
    """

    explanation: str
    takeaway: str
    misconception: int | None


def verify_question(text: str, view: QuestionView) -> Check:
    """Check a question's wording against what the viewer may know before answering."""
    values = question_values(view)
    failures = [
        *_slots(text, values),
        *_bare_numbers(text),
        *_names(text, values),
        *_betting(text),
        *_hints(text, view),
        *_echoes(text, values),
        *_length(text, "question", MAX_QUESTION_WORDS),
    ]
    return Check(tuple(failures))


def verify_feedback(feedback: FeedbackText, pack: EvidencePack, grade: Grade) -> Check:
    """Check feedback's wording against the whole pack and the viewer's answer."""
    values = feedback_values(pack, grade.chosen)
    texts = (feedback.explanation, feedback.takeaway)
    failures = [
        *(failure for text in texts for failure in _slots(text, values)),
        *(failure for text in texts for failure in _bare_numbers(text)),
        *(failure for text in texts for failure in _names(text, values)),
        *(failure for text in texts for failure in _betting(text)),
        *(failure for text in texts for failure in _verdicts(text)),
        *_grounded(feedback.explanation, pack, grade),
        *(failure for text in texts for failure in _comparisons(text, pack, grade)),
        *_misconception(feedback.misconception, pack, grade),
        *(failure for text in texts for failure in _echoes(text, values)),
        *_length(feedback.explanation, "explanation", MAX_EXPLANATION_WORDS),
        *_takeaway_length(feedback.takeaway),
    ]
    return Check(tuple(failures))


def _without_slots(text: str) -> str:
    # A slot stands for a value the pack supplies, so it is read as one lower-case word.
    return SLOT.sub("slot", text)


def _slots(text: str, values: Mapping[str, str]) -> list[Failure]:
    unknown = sorted(slot_names(text) - set(values))
    failures = [Failure("slots", f"{{{name}}} is not a fact this text may use") for name in unknown]
    # Braces that don't make a slot would reach the viewer as they are.
    stray = re.findall(r"\{[^{}]*\}|[{}]", SLOT.sub("", text))
    failures += [Failure("slots", f"{brace!r} is not a slot") for brace in stray]
    return failures


def _bare_numbers(text: str) -> list[Failure]:
    plain = FOOTBALL_PHRASES.sub(" ", _without_slots(text))
    found = re.findall(r"\d+", plain) + [
        word for word in WORD.findall(plain) if word.lower() in NUMBER_WORDS
    ]
    return [Failure("bare_number", f'"{number}" is a number outside a slot') for number in found]


def _names(text: str, values: Mapping[str, str]) -> list[Failure]:
    known = {word.lower() for value in values.values() for word in WORD.findall(value)}
    # Read as the viewer will, since a value can end one sentence and the text start the next.
    try:
        readable = fill(text, values)
    except SlotError:
        readable = _without_slots(text)
    failures: list[Failure] = []
    for sentence in SENTENCE_END.split(readable.strip()):
        words = WORD.findall(sentence)
        for word in words[1:]:
            base = re.sub(r"['\u2019]s$", "", word)
            # A lone capital letter names an option; the hint check deals with that.
            if len(base) == 1 or not base[0].isupper() or base in ALLOWED_NAMES:
                continue
            if base.lower() not in known:
                failures.append(Failure("names", f'"{base}" is a name the evidence doesn\'t give'))
    return failures


def _betting(text: str) -> list[Failure]:
    return [
        Failure("vocabulary", f'"{word}" is betting language')
        for word in BETTING_WORDS.findall(text)
    ]


def _verdicts(text: str) -> list[Failure]:
    return [
        Failure("verdict", f'"{phrase}" gives a verdict, which belongs to the grade')
        for phrase in VERDICT_PHRASES.findall(text)
    ]


def _hints(text: str, view: QuestionView) -> list[Failure]:
    keys = {option.key for option in view.options}
    failures = [
        Failure("hint", f"{{{name}}} points at an option")
        for name in sorted(slot_names(text))
        if name.split(".")[0] in keys
    ]
    failures += [
        Failure("hint", f'"{match}" names an option') for match in OPTION_LETTER.findall(text)
    ]
    telling = _telling_label_words(view)
    failures += [
        Failure("hint", f'"{word}" comes from an option\'s label')
        for word in dict.fromkeys(WORD.findall(_without_slots(text)))
        if word.lower() in telling
    ]
    return failures


def _telling_label_words(view: QuestionView) -> set[str]:
    """Words that tell options apart: in some labels but not all, and not shown otherwise."""
    labels = [_lower_words(option.label) for option in view.options]
    in_some = set[str]().union(*labels)
    in_all = labels[0].intersection(*labels[1:]) if labels else set[str]()
    shown = _lower_words(" ".join(question_values(view)[name] for name in _shown_names(view)))
    subject = _lower_words(f"{view.asks.value} {view.concept_name}")
    return in_some - in_all - shown - subject - LABEL_STOPWORDS


def _shown_names(view: QuestionView) -> list[str]:
    """The question view's own facts and timing, not its options'."""
    keys = {option.key for option in view.options}
    return [name for name in question_values(view) if name.split(".")[0] not in keys]


def _lower_words(text: str) -> set[str]:
    return {word.lower() for word in WORD.findall(text)}


def _grounded(explanation: str, pack: EvidencePack, grade: Grade) -> list[Failure]:
    names = slot_names(explanation)
    failures: list[Failure] = []
    if not any(name == "answer" or name.startswith("answer.") for name in names):
        failures.append(Failure("grounded", "it doesn't cite the answer, {answer} or {answer.*}"))
    if not any(_is_outcome(name, pack) for name in names):
        failures.append(Failure("grounded", "it cites none of the outcome facts"))
    wrong_pass = pack.asks is Asks.WHERE_TO_PASS and not grade.correct
    if wrong_pass and not any(name.startswith("chosen.") for name in names):
        failures.append(Failure("grounded", "after a wrong pass it doesn't cite {chosen.*}"))
    return failures


def _is_outcome(name: str, pack: EvidencePack) -> bool:
    if name in pack.outcome:
        return True
    ref, _, fact = name.partition(".")
    return bool(fact) and any(fact in option.outcome for option in _options_for(ref, pack))


def _options_for(ref: str, pack: EvidencePack) -> list[PackOption]:
    if ref == "answer":
        return [option for option in pack.options if option.correct]
    if ref == "chosen":
        return list(pack.options)
    return [option for option in pack.options if option.key == ref]


def _comparisons(text: str, pack: EvidencePack, grade: Grade) -> list[Failure]:
    failures: list[Failure] = []
    for sentence in SENTENCE_END.split(text.strip()):
        pairs = _same_fact_pairs(sentence, pack, grade.chosen)
        if not pairs:
            continue
        words = {word.lower() for word in WORD.findall(_without_slots(sentence))}
        more, fewer = bool(words & MORE_WORDS), bool(words & FEWER_WORDS)
        if not (more or fewer):
            if UNORDERED_COMPARATIVES.search(_without_slots(sentence)):
                failures.append(
                    Failure("comparison", "it compares two options in a way code can't check")
                )
            continue
        if more and fewer:
            failures.append(Failure("comparison", "it compares two options both ways at once"))
            continue
        for (first, a), (second, b) in pairs:
            if not isinstance(a.value, float | int) or not isinstance(b.value, float | int):
                failures.append(Failure("comparison", f"{{{first}}} isn't a number to compare"))
            elif (more and not a.value > b.value) or (fewer and not a.value < b.value):
                word = "more" if more else "fewer"
                failures.append(
                    Failure("comparison", f"{{{first}}} is not {word} than {{{second}}}")
                )
    return failures


def _same_fact_pairs(
    sentence: str, pack: EvidencePack, chosen: str | None
) -> list[tuple[tuple[str, Fact], tuple[str, Fact]]]:
    """Slots in a sentence that name the same fact of two different options, in order."""
    found: list[tuple[str, str, str, Fact]] = []
    for name in SLOT.findall(sentence):
        ref, _, fact_name = name.partition(".")
        option = _option(ref, pack, chosen)
        fact = None if option is None else {**option.neutral, **option.outcome}.get(fact_name)
        if option is not None and fact is not None:
            found.append((name, option.key, fact_name, fact))
    return [
        ((first, a), (second, b))
        for i, (first, key_a, fact_a, a) in enumerate(found)
        for second, key_b, fact_b, b in found[i + 1 :]
        if fact_a == fact_b and key_a != key_b
    ]


def _option(ref: str, pack: EvidencePack, chosen: str | None) -> PackOption | None:
    key = pack.correct_key if ref == "answer" else chosen if ref == "chosen" else ref
    return next((option for option in pack.options if option.key == key), None)


def _misconception(index: int | None, pack: EvidencePack, grade: Grade) -> list[Failure]:
    if index is None:
        return []
    if grade.correct:
        return [Failure("misconception", "a right answer gets no misconception")]
    count = len(pack.concept.misconceptions)
    if not 0 <= index < count:
        return [Failure("misconception", f"there is no misconception {index}; there are {count}")]
    return []


def _echoes(text: str, values: Mapping[str, str]) -> list[Failure]:
    """What only shows once the slots are filled: a value said twice, or a sentence split."""
    try:
        filled = fill(text, values)
    except SlotError:
        return []  # The slots check has already rejected it.
    failures: list[Failure] = []
    for sentence in FULL_STOP.split(filled.strip()):
        words = [word.lower() for word in re.findall(r"[\w'\u2019#%+-]+(?:\.\d+)?", sentence)]
        for size in range(1, 6):
            for start in range(len(words) - 2 * size + 1):
                run = words[start : start + size]
                if run == words[start + size : start + 2 * size] and any(w.isalpha() for w in run):
                    failures.append(Failure("echo", f'"{" ".join(run)}" is said twice in a row'))
    # A name or phrase written out in the same sentence as its own slot ("{receiver} (#8 …)").
    for sentence in FULL_STOP.split(text.strip()):
        literal = SLOT.sub(" ", sentence).lower()
        for name in slot_names(sentence):
            value = values.get(name, "").lower()
            if " " in value.strip() and value in literal:
                failures.append(Failure("echo", f"{{{name}}}'s value is also written out"))
    if re.search(r"\.\s+[a-z]|\.\.", filled):
        failures.append(Failure("echo", "a whole-sentence fact is used inside another sentence"))
    return failures


def _length(text: str, what: str, most: int) -> list[Failure]:
    words = len(_without_slots(text).split())
    if words > most:
        return [Failure("length", f"the {what} has {words} words; at most {most}")]
    return []


def _takeaway_length(takeaway: str) -> list[Failure]:
    failures = _length(takeaway, "takeaway", MAX_TAKEAWAY_WORDS)
    if len(FULL_STOP.split(takeaway.strip())) > 1:
        failures.append(Failure("length", "the takeaway is more than one sentence"))
    return failures
