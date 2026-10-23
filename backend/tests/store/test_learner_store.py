"""The contract every learner store keeps. Milestone 3's Cosmos DB store joins STORES."""

import json
from collections.abc import Callable
from pathlib import Path

import pytest

from btl.learn.knowledge import Delivery
from btl.learn.learner import Attempt, LearnerState
from btl.learn.questions import Asks, Form
from btl.schema.ids import TeamId
from btl.store.base import (
    LearnerExistsError,
    LearnerStore,
    StaleWriteError,
    check_viewer_id,
    from_document,
    to_document,
)
from btl.store.json_files import JsonLearnerStore
from btl.store.memory import MemoryLearnerStore
from tests.fixtures.learning import LINE_BREAKING

STORES: dict[str, Callable[[Path], LearnerStore]] = {
    "memory": lambda _: MemoryLearnerStore(),
    "json files": lambda folder: JsonLearnerStore(folder / "learners"),
}
ANSWER = Attempt(
    match_number=1,
    action_id=412,
    concept=LINE_BREAKING,
    form=Form.PREDICT,
    asks=Asks.WHERE_TO_PASS,
    level=2,
    delivery=Delivery.LIVE,
    difficulty=0.57,
    options=3,
    chosen="C",
    correct=True,
    pack_id="0123456789abcdef",
    answered_at="2026-10-08T12:00:00+00:00",
)


@pytest.fixture(params=sorted(STORES))
def store(request: pytest.FixtureRequest, tmp_path: Path) -> LearnerStore:
    name: str = request.param
    return STORES[name](tmp_path)


def test_a_new_learner_reads_back_unchanged(store: LearnerStore) -> None:
    state = LearnerState("lily", seed=7).answered(ANSWER)

    etag = store.create(state)
    stored = store.get("lily")

    assert stored is not None
    assert stored.state == state and stored.etag == etag


def test_an_unknown_learner_is_none(store: LearnerStore) -> None:
    assert store.get("nobody") is None


def test_a_viewer_id_can_only_be_created_once(store: LearnerStore) -> None:
    store.create(LearnerState("lily", seed=7))

    with pytest.raises(LearnerExistsError):
        store.create(LearnerState("lily", seed=8))


def test_a_write_from_the_version_read_succeeds_and_changes_the_etag(store: LearnerStore) -> None:
    first = store.create(LearnerState("lily", seed=7))

    second = store.put(LearnerState("lily", seed=7).answered(ANSWER), first)
    stored = store.get("lily")

    assert second != first
    assert stored is not None and stored.etag == second and len(stored.state.attempts) == 1


def test_a_write_from_an_old_version_is_refused(store: LearnerStore) -> None:
    first = store.create(LearnerState("lily", seed=7))
    store.put(LearnerState("lily", seed=7).answered(ANSWER), first)

    with pytest.raises(StaleWriteError):
        store.put(LearnerState("lily", seed=7).next_match(), first)


@pytest.mark.parametrize("viewer_id", ["", "Lily", "../escape", "a b", "x" * 65])
def test_viewer_ids_are_kept_plain(viewer_id: str) -> None:
    with pytest.raises(ValueError, match="isn't a valid viewer id"):
        check_viewer_id(viewer_id)


@pytest.mark.parametrize(
    "viewer_id",
    [
        "0123456789abcdef0123456789abcdef",
        "ffffffffffffffffffffffffffffffff",
        "9f86d081884c7d659a2feaa0c55ad015",
    ],
)
def test_a_browser_s_random_id_is_a_valid_viewer_id(viewer_id: str) -> None:
    # The page makes 128 random bits as 32 lower-case hex characters (`newViewerId`).
    check_viewer_id(viewer_id)


def test_the_document_is_shaped_like_a_cosmos_item_and_round_trips() -> None:
    state = LearnerState("lily", seed=7, match_number=2).answered(ANSWER)

    document = to_document(state)

    assert document["id"] == document["viewer_id"] == "lily"
    assert from_document(json.loads(json.dumps(document))) == state


def test_the_club_round_trips() -> None:
    state = LearnerState("lily", seed=7, club=TeamId(4))

    assert from_document(json.loads(json.dumps(to_document(state)))) == state


def test_a_record_from_before_clubs_reads_as_no_club_and_is_saved_as_the_new_version(
    store: LearnerStore,
) -> None:
    document = to_document(LearnerState("lily", seed=7).answered(ANSWER))
    del document["club"]
    document["version"] = 1

    state = from_document(document)

    assert state == LearnerState("lily", seed=7).answered(ANSWER)
    assert state.club is None
    store.create(state)
    stored = store.get("lily")
    assert stored is not None and to_document(stored.state)["version"] == 2


def test_a_record_from_another_version_is_refused() -> None:
    document = to_document(LearnerState("lily", seed=7)) | {"version": 99}

    with pytest.raises(ValueError, match="record version 99"):
        from_document(document)


def test_the_json_store_writes_one_readable_file_per_learner(tmp_path: Path) -> None:
    store = JsonLearnerStore(tmp_path)
    store.create(LearnerState("lily", seed=7).answered(ANSWER))

    files = sorted(path.name for path in tmp_path.iterdir())
    saved = json.loads((tmp_path / "lily.json").read_text())

    assert files == ["lily.json"]
    assert saved["attempts"][0]["concept"] == "line_breaking_pass"
