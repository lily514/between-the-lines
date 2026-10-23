"""The Blob store's own cases, beyond the contract: run against Azurite with ``-m blob``."""

import json

import pytest

from btl.learn.learner import LearnerState
from btl.store.base import StaleWriteError, to_document
from btl.store.blob import BlobLearnerStore
from tests.fixtures.azurite import azurite_container

pytestmark = pytest.mark.blob


def test_replacing_a_learner_who_isn_t_stored_is_a_key_error() -> None:
    store = BlobLearnerStore(azurite_container())

    with pytest.raises(KeyError):
        store.put(LearnerState("lily", seed=7), '"0x8DC0000000000000"')


def test_a_write_after_another_server_changed_the_blob_is_refused() -> None:
    container = azurite_container()
    store = BlobLearnerStore(container)
    read = store.create(LearnerState("lily", seed=7))
    # Another revision of the app saves the learner in between, straight to the blob.
    container.get_blob_client("lily.json").upload_blob(
        json.dumps(to_document(LearnerState("lily", seed=7).next_match())), overwrite=True
    )

    with pytest.raises(StaleWriteError):
        store.put(LearnerState("lily", seed=7).next_match(), read)


def test_the_blob_is_the_same_readable_document_as_the_json_file() -> None:
    container = azurite_container()
    BlobLearnerStore(container).create(LearnerState("lily", seed=7))

    blob = container.get_blob_client("lily.json")
    saved = json.loads(blob.download_blob().readall())

    assert saved == to_document(LearnerState("lily", seed=7))
    assert blob.get_blob_properties().content_settings.content_type == "application/json"
