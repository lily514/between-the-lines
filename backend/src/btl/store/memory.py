"""A learner store in memory, for tests and one-off runs."""

from dataclasses import dataclass, field

from btl.learn.learner import LearnerState
from btl.store.base import LearnerExistsError, StaleWriteError, Stored, check_viewer_id


@dataclass
class MemoryLearnerStore:
    """A `btl.store.base.LearnerStore` that forgets everything when the process ends.

    Etags count writes, so each write gives a new one.
    """

    _learners: dict[str, Stored] = field(default_factory=dict[str, Stored])
    _writes: int = 0

    def get(self, viewer_id: str) -> Stored | None:
        """The stored learner, or None."""
        return self._learners.get(viewer_id)

    def create(self, state: LearnerState) -> str:
        """Store a new learner."""
        if check_viewer_id(state.viewer_id) in self._learners:
            raise LearnerExistsError(state.viewer_id)
        return self._write(state)

    def put(self, state: LearnerState, etag: str) -> str:
        """Replace a learner read as ``etag``."""
        current = self._learners[state.viewer_id]
        if current.etag != etag:
            raise StaleWriteError(state.viewer_id)
        return self._write(state)

    def _write(self, state: LearnerState) -> str:
        self._writes += 1
        etag = f"w{self._writes}"
        self._learners[state.viewer_id] = Stored(state, etag)
        return etag
