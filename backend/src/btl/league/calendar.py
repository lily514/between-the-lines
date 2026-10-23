"""When a viewer's matches are played: a fixed, made-up calendar of Saturday kick-offs.

The calendar is part of the fiction, like the clubs. A viewer's match ``n`` is on matchday
``n``, one week after the last, so the same match always has the same date. Nothing here reads
the clock; whether a match is upcoming or finished comes from the viewer's record.
"""

from dataclasses import dataclass
from datetime import date, timedelta

SEASON_START = date(2026, 10, 24)
KICK_OFF = "15:00"
DAYS_BETWEEN_MATCHDAYS = 7


@dataclass(frozen=True, slots=True)
class Matchday:
    """A matchday: its number, its date and the kick-off time."""

    number: int
    day: date
    kick_off: str

    @property
    def label(self) -> str:
        """The date as the page shows it, e.g. ``Sat 24 Oct``."""
        return f"{self.day:%a} {self.day.day} {self.day:%b}"


def matchday(match_number: int) -> Matchday:
    """The matchday of a viewer's match, counting from 1."""
    if match_number < 1:
        raise ValueError(f"match numbers count from 1, not {match_number}")
    day = SEASON_START + timedelta(days=DAYS_BETWEEN_MATCHDAYS * (match_number - 1))
    return Matchday(match_number, day, KICK_OFF)
