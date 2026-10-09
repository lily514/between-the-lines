"""A learner store as one JSON file per viewer, for running locally.

Each learner is ``<folder>/<viewer id>.json``, the same document Cosmos DB will hold. A file is
written to a temporary name and then moved into place, so a crash never leaves half a file.
The etag is a hash of the file's content.
"""

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from btl.learn.learner import LearnerState
from btl.store.base import (
    LearnerExistsError,
    StaleWriteError,
    Stored,
    check_viewer_id,
    from_document,
    to_document,
)


@dataclass(frozen=True, slots=True)
class JsonLearnerStore:
    """A `btl.store.base.LearnerStore` keeping each learner in a JSON file under ``folder``."""

    folder: Path

    def get(self, viewer_id: str) -> Stored | None:
        """The stored learner, or None if it has no file."""
        path = self._path(viewer_id)
        if not path.exists():
            return None
        text = path.read_text(encoding="utf-8")
        document = cast(dict[str, object], json.loads(text))
        return Stored(from_document(document), _etag(text))

    def create(self, state: LearnerState) -> str:
        """Store a new learner in a new file."""
        if self._path(state.viewer_id).exists():
            raise LearnerExistsError(state.viewer_id)
        return self._write(state)

    def put(self, state: LearnerState, etag: str) -> str:
        """Replace a learner's file, if it is still the version read as ``etag``."""
        current = self.get(state.viewer_id)
        if current is None:
            raise KeyError(state.viewer_id)
        if current.etag != etag:
            raise StaleWriteError(state.viewer_id)
        return self._write(state)

    def _path(self, viewer_id: str) -> Path:
        return self.folder / f"{check_viewer_id(viewer_id)}.json"

    def _write(self, state: LearnerState) -> str:
        self.folder.mkdir(parents=True, exist_ok=True)
        text = json.dumps(to_document(state), indent=2, ensure_ascii=False) + "\n"
        path = self._path(state.viewer_id)
        temporary = path.with_suffix(".json.tmp")
        temporary.write_text(text, encoding="utf-8")
        os.replace(temporary, path)
        return _etag(text)


def _etag(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]
