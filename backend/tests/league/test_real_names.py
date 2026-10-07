"""Checks generated names against a private list of real names that is never committed.

The list lives in ``backend/private/real-names.txt``, which is gitignored: one real name per
line (clubs, places, players, league marks), ``#`` for comments. Without the file (in CI or a
fresh clone), these tests are skipped. Matching ignores case and accents.
"""

import unicodedata
from pathlib import Path

import numpy as np
import pytest

from btl.league.league import generate_league
from btl.league.names import NAME_STYLES, possible_surnames

REAL_NAMES_FILE = Path(__file__).parents[2] / "private" / "real-names.txt"
SEEDS = range(200)


def _fold(text: str) -> str:
    """Lower case without accents, so "João" and "joao" compare equal."""
    decomposed = unicodedata.normalize("NFKD", text.lower())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def _real_names() -> list[str]:
    if not REAL_NAMES_FILE.exists():
        pytest.skip(f"no private list at {REAL_NAMES_FILE}")
    lines = REAL_NAMES_FILE.read_text().splitlines()
    return [_fold(line.strip()) for line in lines if line.strip() and not line.startswith("#")]


def test_no_style_can_produce_a_listed_full_name() -> None:
    # Checks the pools themselves, so it covers every seed, not just a sample.
    real_names = _real_names()
    clashes: list[str] = []

    for style in NAME_STYLES:
        first_names = {_fold(name) for name in style.first_names}
        surnames = {_fold(name) for name in possible_surnames(style)}
        for real in real_names:
            first, _, last = real.partition(" ")
            if first in first_names and last in surnames:
                clashes.append(f"{style.name} can produce {real!r}")

    assert not clashes, "\n".join(clashes)


def test_no_generated_name_contains_a_real_name() -> None:
    real_names = _real_names()
    matches: set[str] = set()

    for seed in SEEDS:
        league = generate_league(np.random.default_rng(seed))
        names = [league.name]
        for club in league.clubs:
            names.append(club.name)
            names.extend(player.full_name for player in club.squad)
        matches.update(
            f"{name!r} contains {real!r}"
            for name in names
            for real in real_names
            if real in _fold(name)
        )

    assert not matches, "\n".join(sorted(matches))
