"""The Azurite storage emulator, for the opt-in Blob store tests: a fresh container, or a skip.

Azurite runs in Docker on localhost (docs/setup.md). It accepts only its own account key, which
Microsoft publishes; the tests read it from BTL_AZURITE_KEY, so it is never in the repo.
"""

import os
import uuid

import pytest
from azure.core.exceptions import AzureError
from azure.storage.blob import BlobServiceClient, ContainerClient

ACCOUNT = "devstoreaccount1"
URL = f"http://127.0.0.1:10000/{ACCOUNT}"


def azurite_container() -> ContainerClient:
    """A new, empty container in Azurite, so no test sees another's learners."""
    key = os.environ.get("BTL_AZURITE_KEY")
    if not key:
        pytest.skip("set BTL_AZURITE_KEY to Azurite's published account key (docs/setup.md)")
    # No retries and a short timeout: if Azurite isn't running, say so at once.
    service = BlobServiceClient(
        URL,
        credential={"account_name": ACCOUNT, "account_key": key},
        retry_total=0,
        connection_timeout=2,
    )
    try:
        # The SDK types one of create_container's own parameters as a bare dict.
        return service.create_container(  # pyright: ignore[reportUnknownMemberType]
            f"learners-{uuid.uuid4().hex[:12]}"
        )
    except AzureError as error:
        pytest.skip(f"Azurite isn't answering on {URL} ({type(error).__name__}); see docs/setup.md")
