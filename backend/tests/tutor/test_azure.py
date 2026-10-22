"""The Azure client's requests and replies, checked against a mock transport: no network."""

import importlib
import json
import pkgutil
from collections.abc import Callable
from types import ModuleType
from typing import Any

import httpx2
import pytest
from azure.core.credentials import AccessToken
from azure.core.exceptions import ClientAuthenticationError

import btl
from btl.tutor.azure import (
    REASONING_EFFORT,
    TOKEN_SCOPE,
    AzureClient,
    FoundrySettings,
    cli_credential,
)
from btl.tutor.model import ModelError, ModelRequest
from tests.fixtures.imports import imports_by_module

SETTINGS = FoundrySettings(
    endpoint="https://example-resource.openai.azure.com/",
    deployment="tutor-model",
    tenant="00000000-0000-0000-0000-000000000001",
)
SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {"text": {"type": "string"}},
    "required": ["text"],
    "additionalProperties": False,
}
REQUEST = ModelRequest("Word questions.", "The question view.", "question", SCHEMA, timeout=5.0)
FAR_FUTURE = 4_000_000_000


class FakeCredential:
    """Hands out one token, and remembers which scopes were asked for."""

    def __init__(self, fail: bool = False) -> None:
        self.scopes: list[str] = []
        self.fail = fail

    # The azure-core protocol takes untyped keyword options.
    def get_token(self, *scopes: str, **kwargs: Any) -> AccessToken:
        self.scopes.extend(scopes)
        if self.fail:
            raise ClientAuthenticationError("not signed in")
        return AccessToken("entra-token", FAR_FUTURE)


def response_body(text: str, status: str = "completed") -> dict[str, object]:
    return {
        "id": "resp_1",
        "object": "response",
        "created_at": 0,
        "model": "tutor-model-2026-03-17",
        "status": status,
        "output": [
            {
                "type": "message",
                "id": "msg_1",
                "role": "assistant",
                "status": "completed",
                "content": [{"type": "output_text", "text": text, "annotations": []}],
            }
        ],
        "parallel_tool_calls": False,
        "tool_choice": "auto",
        "tools": [],
        "usage": {
            "input_tokens": 120,
            "output_tokens": 18,
            "total_tokens": 138,
            "input_tokens_details": {"cached_tokens": 0},
            "output_tokens_details": {"reasoning_tokens": 0},
        },
    }


def client_with(
    handler: Callable[[httpx2.Request], httpx2.Response], credential: FakeCredential | None = None
) -> AzureClient:
    transport = httpx2.MockTransport(handler)
    return AzureClient(
        SETTINGS,
        credential=credential or FakeCredential(),
        http_client=httpx2.Client(transport=transport),
    )


def test_a_request_goes_to_the_deployment_with_an_entra_token_and_a_strict_schema() -> None:
    sent: list[httpx2.Request] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        sent.append(request)
        return httpx2.Response(200, json=response_body('{"text": "Where now?"}'))

    credential = FakeCredential()
    client_with(handler, credential).complete(REQUEST)

    (request,) = sent
    body = json.loads(request.content)
    assert request.url.host == "example-resource.openai.azure.com"
    assert request.url.path == "/openai/responses"
    assert request.url.params["api-version"] == "2025-04-01-preview"
    assert request.headers["authorization"] == "Bearer entra-token"
    assert "api-key" not in request.headers
    assert credential.scopes == [TOKEN_SCOPE]
    assert body["model"] == "tutor-model"
    assert (body["instructions"], body["input"]) == ("Word questions.", "The question view.")
    assert body["reasoning"] == {"effort": REASONING_EFFORT} == {"effort": "none"}
    assert body["text"]["format"] == {
        "type": "json_schema",
        "name": "question",
        "schema": SCHEMA,
        "strict": True,
    }


def test_a_reply_brings_its_text_model_and_tokens() -> None:
    reply = client_with(
        lambda _: httpx2.Response(200, json=response_body('{"text": "Where now?"}'))
    ).complete(REQUEST)

    assert reply.text == '{"text": "Where now?"}'
    assert reply.model == "tutor-model-2026-03-17"
    assert (reply.input_tokens, reply.output_tokens) == (120, 18)
    assert reply.seconds >= 0


def refuse(status: int) -> Callable[[httpx2.Request], httpx2.Response]:
    return lambda _: httpx2.Response(status, json={"error": {"code": "x", "message": "no"}})


def incomplete(_: httpx2.Request) -> httpx2.Response:
    return httpx2.Response(200, json=response_body("", status="incomplete"))


def time_out(request: httpx2.Request) -> httpx2.Response:
    raise httpx2.ReadTimeout("too slow", request=request)


@pytest.mark.parametrize(
    "handler",
    [
        refuse(401),
        refuse(429),
        refuse(500),
        time_out,
        incomplete,
    ],
    ids=["unauthorised", "rate-limited", "server error", "timeout", "incomplete"],
)
def test_every_failure_becomes_a_model_error(
    handler: Callable[[httpx2.Request], httpx2.Response],
) -> None:
    with pytest.raises(ModelError):
        client_with(handler).complete(REQUEST)


def test_a_failed_sign_in_becomes_a_model_error_before_anything_is_sent() -> None:
    sent: list[httpx2.Request] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        sent.append(request)
        return httpx2.Response(200, json=response_body("{}"))

    with pytest.raises(ModelError, match="ClientAuthenticationError"):
        client_with(handler, FakeCredential(fail=True)).complete(REQUEST)
    assert sent == []


def test_the_azure_cli_is_asked_for_tokens_from_the_named_tenant() -> None:
    assert cli_credential(SETTINGS.tenant).tenant_id == SETTINGS.tenant


def test_only_the_azure_client_imports_network_libraries() -> None:
    network = ("openai", "azure", "httpx2")
    importers = [
        f"{package.__name__}.{module}"
        for package in _packages()
        for module, imported in imports_by_module(package).items()
        if any(name == lib or name.startswith(f"{lib}.") for name in imported for lib in network)
    ]

    assert importers == ["btl.tutor.azure.py"]


def _packages() -> list[ModuleType]:
    found: list[ModuleType] = [btl]
    for info in pkgutil.iter_modules(btl.__path__):
        if info.ispkg:
            found.append(importlib.import_module(f"btl.{info.name}"))
    return found
