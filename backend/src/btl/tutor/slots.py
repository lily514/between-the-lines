"""Fact slots: ``{name}`` in a Tutor's text, filled by code from the evidence.

The names a slot can use:

- ``{team}``, ``{gap_m}``: a fact from the pack's context, or after answering its outcome.
- ``{B.label}``, ``{B.threat_added}``: an option's label or one of its facts.
- ``{answer}``, ``{answer.lines_broken}``: the right option, after answering.
- ``{chosen}``, ``{chosen.threat_added}``: the option the viewer picked, after answering.
- ``{occurred_at}``, ``{delivered_at}``, ``{restart}``: when the moment happened and is asked.

Before the viewer answers, only the question view's facts can be filled, so wording that
cites an outcome fails rather than giving the answer away.
"""

import re
from collections.abc import Collection, Mapping

from btl.learn.evidence import EvidencePack, Fact, QuestionView, Timing

SLOT = re.compile(r"\{([A-Za-z_][A-Za-z0-9_.]*)\}")


class SlotError(KeyError):
    """A slot names a fact that isn't available."""


def slot_names(text: str) -> set[str]:
    """Every slot a text uses."""
    return set(SLOT.findall(text))


def fill(text: str, values: Mapping[str, str]) -> str:
    """Replace each slot with its value.

    Raises:
        SlotError: If a slot names something not in ``values``.
    """
    missing = sorted(slot_names(text) - set(values))
    if missing:
        raise SlotError(f"no value for {', '.join('{' + name + '}' for name in missing)}")
    return SLOT.sub(lambda match: values[match.group(1)], text)


def question_values(view: QuestionView) -> dict[str, str]:
    """What a question's wording may use: context, timing and each option's neutral facts."""
    values = {**_shown(view.context), **_timing(view.timing)}
    for option in view.options:
        values[f"{option.key}.label"] = option.label
        values |= {f"{option.key}.{name}": fact.display for name, fact in option.neutral.items()}
    return values


def feedback_values(pack: EvidencePack, chosen: str | None) -> dict[str, str]:
    """What feedback may use: everything in the pack, plus the right and the picked option."""
    values = {**_shown(pack.context), **_shown(pack.outcome), **_timing(pack.timing)}
    for option in pack.options:
        option_values = {"label": option.label} | _shown(option.neutral) | _shown(option.outcome)
        values |= {f"{option.key}.{name}": text for name, text in option_values.items()}
        aliases = ["answer"] if option.correct else []
        aliases += ["chosen"] if option.key == chosen else []
        for alias in aliases:
            values[alias] = option.label
            values |= {f"{alias}.{name}": text for name, text in option_values.items()}
    return values


def slotify(text: str, values: Mapping[str, str], prefer: Collection[str] = ()) -> str:
    """Turn values written out in full back into their slots, longest first.

    A model sometimes copies a value ("#10 Chinedu Trankwo", "00:32") instead of writing its
    slot. Only values with a digit or a capital letter are turned back, since a plain word such
    as "one" or "free kick" is often just a word. The text then reads exactly as before once
    filled, but every number and name in it comes from a slot the checks can follow.

    When two slots hold the same value, {answer} and {chosen} win, then the names in ``prefer``
    (feedback prefers the outcome facts), then the others.
    """

    def rank(pair: tuple[str, str]) -> tuple[int, int]:
        value, name = pair
        tie = 0 if name.startswith(("answer", "chosen")) else 1 if name in prefer else 2
        return -len(value), tie

    # Longest first, so a full name wins over part of it.
    found = sorted(
        ((value, name) for name, value in values.items() if _distinctive(value)), key=rank
    )
    pieces = SLOT.split(text)
    # SLOT.split gives text, slot name, text, …: only the text between slots is searched.
    for index in range(0, len(pieces), 2):
        for value, name in found:
            pieces[index] = re.sub(
                rf"(?<![\w#]){re.escape(value)}(?![\w])", f"\x00{name}\x00", pieces[index]
            )
    joined = "".join(
        piece if index % 2 == 0 else f"{{{piece}}}" for index, piece in enumerate(pieces)
    )
    return re.sub(r"\x00([^\x00]+)\x00", r"{\1}", joined)


def _distinctive(value: str) -> bool:
    return any(character.isdigit() or character.isupper() for character in value)


def _shown(facts: Mapping[str, Fact]) -> dict[str, str]:
    return {name: fact.display for name, fact in facts.items()}


def _timing(timing: Timing) -> dict[str, str]:
    values = {
        "occurred_at": timing.occurred_at,
        "delivered_at": timing.delivered_at,
        "delivered_phase": timing.delivered_phase.value,
    }
    if timing.restart is not None:
        values["restart"] = timing.restart
    return values
