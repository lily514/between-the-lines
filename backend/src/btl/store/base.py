"""The learner store's contract, and the document a learner is saved as."""

import re
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from typing import Protocol, cast

from btl.learn.concept_map import ConceptKey
from btl.learn.knowledge import Delivery
from btl.learn.learner import LEARNER_VERSION, Attempt, LearnerState
from btl.learn.questions import Asks, Form
from btl.schema.ids import TeamId

# Viewer ids become file names and document ids, so they are kept plain.
VIEWER_ID = re.compile(r"[a-z0-9][a-z0-9_-]{0,63}")
# Version 1 records have no club; they read as a viewer who hasn't chosen one. Version 2
# attempts don't say which period they were asked in.
READABLE_VERSIONS = (1, 2, LEARNER_VERSION)


class LearnerExistsError(Exception):
    """A learner with that id is already stored."""


class StaleWriteError(Exception):
    """The learner changed since it was read; read it again and reapply the change."""


@dataclass(frozen=True, slots=True)
class Stored:
    """A learner as read from the store, with the etag that identifies this version."""

    state: LearnerState
    etag: str


class LearnerStore(Protocol):
    """Keeps learners between runs. Writes are checked against the version last read."""

    def get(self, viewer_id: str) -> Stored | None:
        """The stored learner, or None if there is none."""
        ...

    def create(self, state: LearnerState) -> str:
        """Store a new learner and return its etag.

        Raises:
            LearnerExistsError: If the viewer id is taken.
        """
        ...

    def put(self, state: LearnerState, etag: str) -> str:
        """Replace a learner, if it hasn't changed since it was read as ``etag``.

        Returns:
            The new etag.

        Raises:
            StaleWriteError: If the stored version isn't ``etag``.
            KeyError: If there is no such learner.
        """
        ...


def check_viewer_id(viewer_id: str) -> str:
    """The id, if it is plain: lower-case letters, digits, '-' and '_', up to 64 characters.

    Raises:
        ValueError: Otherwise.
    """
    if not VIEWER_ID.fullmatch(viewer_id):
        raise ValueError(
            f"{viewer_id!r} isn't a valid viewer id: use lower-case letters, digits, '-' and '_'"
        )
    return viewer_id


def to_document(state: LearnerState) -> dict[str, object]:
    """A learner as a JSON-ready document, shaped like a Cosmos DB item."""
    return {
        "id": state.viewer_id,
        "viewer_id": state.viewer_id,
        "version": state.version,
        "seed": state.seed,
        "club": state.club,
        "match_number": state.match_number,
        "attempts": [asdict(attempt) for attempt in state.attempts],
    }


def from_document(document: Mapping[str, object]) -> LearnerState:
    """Read a document written by `to_document`, now or in an earlier version.

    Raises:
        ValueError: If it was written for another version of the record.
    """
    if document["version"] not in READABLE_VERSIONS:
        raise ValueError(
            f"learner {document['id']!r} has record version {document['version']}; "
            f"this code reads versions {', '.join(map(str, READABLE_VERSIONS))}"
        )
    attempts = cast(list[dict[str, object]], document["attempts"])
    club = document.get("club")
    return LearnerState(
        viewer_id=str(document["viewer_id"]),
        seed=cast(int, document["seed"]),
        match_number=cast(int, document["match_number"]),
        attempts=tuple(_attempt(a) for a in attempts),
        club=None if club is None else TeamId(cast(int, club)),
    )


def _attempt(raw: Mapping[str, object]) -> Attempt:
    return Attempt(
        match_number=cast(int, raw["match_number"]),
        action_id=cast(int, raw["action_id"]),
        concept=ConceptKey(str(raw["concept"])),
        form=Form(raw["form"]),
        asks=Asks(raw["asks"]),
        level=cast(int, raw["level"]),
        delivery=Delivery(raw["delivery"]),
        difficulty=cast(float, raw["difficulty"]),
        options=cast(int, raw["options"]),
        chosen=str(raw["chosen"]),
        correct=cast(bool, raw["correct"]),
        pack_id=str(raw["pack_id"]),
        answered_at=str(raw["answered_at"]),
        asked_in=cast(int | None, raw.get("asked_in")),
    )
