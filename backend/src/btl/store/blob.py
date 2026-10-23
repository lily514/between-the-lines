"""A learner store in Azure Blob Storage: one JSON blob per viewer, for the deployed demo.

Each learner is the blob ``<viewer id>.json`` in one container, holding the same document the
JSON file store writes. The blob's ETag is the learner's etag, and Azure itself enforces the
stale-write check: a new learner is uploaded only if no blob has that name (``If-None-Match: *``),
and a change only if the blob is still the version read (``If-Match``). So two app replicas, or
two revisions during a deploy, can never overwrite each other's answers.

This module and `btl.tutor.azure` are the only ones that import an Azure SDK. The store takes a
ready-made container client: in Azure, `blob_container` signs it in as the app's managed
identity, and the tests use the Azurite emulator's own key. The store itself never sees a key.
"""

import json
from dataclasses import dataclass
from typing import cast

from azure.core import MatchConditions
from azure.core.credentials import TokenCredential
from azure.core.exceptions import ResourceExistsError, ResourceModifiedError, ResourceNotFoundError
from azure.identity import AzureCliCredential, ManagedIdentityCredential
from azure.storage.blob import BlobClient, ContainerClient, ContentSettings

from btl.learn.learner import LearnerState
from btl.store.base import (
    LearnerExistsError,
    StaleWriteError,
    Stored,
    check_viewer_id,
    from_document,
    to_document,
)

JSON = ContentSettings(content_type="application/json")


def blob_container(
    account_url: str, container: str, client_id: str | None, tenant: str
) -> ContainerClient:
    """The container of learner blobs, signed in with Microsoft Entra ID, never a key.

    Args:
        account_url: The storage account's blob endpoint, ``https://<account>.blob.core.windows.net``.
        container: The container's name.
        client_id: The app's managed identity, in Azure; without one, the developer's `az login`.
        tenant: The tenant `az login` is asked for tokens from, when there is no managed identity.
    """
    credential: TokenCredential = (
        ManagedIdentityCredential(client_id=client_id)
        if client_id
        else AzureCliCredential(tenant_id=tenant)
    )
    return ContainerClient(account_url, container, credential=credential)


@dataclass(frozen=True, slots=True)
class BlobLearnerStore:
    """A `btl.store.base.LearnerStore` keeping each learner in a blob in ``container``."""

    container: ContainerClient

    def get(self, viewer_id: str) -> Stored | None:
        """The stored learner, or None if it has no blob."""
        try:
            download = self._blob(viewer_id).download_blob()
        except ResourceNotFoundError:
            return None
        document = cast(dict[str, object], json.loads(download.readall()))
        return Stored(from_document(document), _etag(download.properties.etag))

    def create(self, state: LearnerState) -> str:
        """Store a new learner, only if no blob has its name."""
        try:
            written = self._blob(state.viewer_id).upload_blob(
                _text(state), overwrite=False, content_settings=JSON
            )
        except ResourceExistsError:
            raise LearnerExistsError(state.viewer_id) from None
        return _etag(written["etag"])

    def put(self, state: LearnerState, etag: str) -> str:
        """Replace a learner's blob, only if it is still the version read as ``etag``."""
        blob = self._blob(state.viewer_id)
        try:
            written = blob.upload_blob(
                _text(state),
                overwrite=True,
                etag=etag,
                match_condition=MatchConditions.IfNotModified,
                content_settings=JSON,
            )
        except ResourceNotFoundError:
            raise KeyError(state.viewer_id) from None
        except ResourceModifiedError:
            # A missing blob can also fail the If-Match check, so tell the two apart.
            if not blob.exists():
                raise KeyError(state.viewer_id) from None
            raise StaleWriteError(state.viewer_id) from None
        return _etag(written["etag"])

    def _blob(self, viewer_id: str) -> BlobClient:
        return self.container.get_blob_client(f"{check_viewer_id(viewer_id)}.json")


def _text(state: LearnerState) -> str:
    return json.dumps(to_document(state), indent=2, ensure_ascii=False) + "\n"


def _etag(value: object) -> str:
    # The SDK types the ETag loosely; it is always a string such as '"0x8DC…"'.
    return cast(str, value)
