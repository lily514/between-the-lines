"""A language model as the Tutor sees it: one request in, one reply out.

`ModelClient` is all the Tutor knows about a model. `btl.tutor.azure` holds the only real client,
the one that talks to Azure. Tests use `FakeClient`, which plays back scripted replies, or
`ReplayClient`, which plays back real replies a `RecordingClient` kept during an evaluation, so
they never touch the network.
"""

import hashlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Protocol

# A JSON schema, as plain JSON values.
JsonSchema = Mapping[str, object]

# Seconds one call may take. The Tutor's own budget (with its repair) is set where it is used.
DEFAULT_TIMEOUT = 12.0


@dataclass(frozen=True, slots=True)
class ModelRequest:
    """One call: the standing instructions, the prompt, and the schema the JSON reply must follow.

    ``timeout`` is in seconds.
    """

    instructions: str
    prompt: str
    schema_name: str
    schema: JsonSchema
    timeout: float = DEFAULT_TIMEOUT


@dataclass(frozen=True, slots=True)
class ModelReply:
    """The model's reply: its JSON text, which model wrote it, its tokens and its seconds."""

    text: str
    model: str
    input_tokens: int
    output_tokens: int
    seconds: float


class ModelError(Exception):
    """The call failed: a timeout, a refused or incomplete reply, or an error from the service."""


class ModelClient(Protocol):
    """Sends one request to a model and returns its reply."""

    def complete(self, request: ModelRequest) -> ModelReply:
        """The model's reply to the request.

        Raises:
            ModelError: If there is no usable reply.
        """
        ...


@dataclass
class FakeClient:
    """A scripted model for tests: each call takes the next reply, or raises the next error.

    Every request is kept in ``requests``, so a test can check what the model was sent.
    """

    replies: Sequence[str | ModelError]
    model: str = "fake-model"
    requests: list[ModelRequest] = field(default_factory=list[ModelRequest])

    def complete(self, request: ModelRequest) -> ModelReply:
        """The next scripted reply.

        Raises:
            ModelError: If the script says so, or has run out.
        """
        self.requests.append(request)
        if len(self.requests) > len(self.replies):
            raise ModelError("the fake model has no more replies")
        reply = self.replies[len(self.requests) - 1]
        if isinstance(reply, ModelError):
            raise reply
        return ModelReply(reply, self.model, len(request.prompt.split()), len(reply.split()), 0.0)


def request_key(request: ModelRequest) -> str:
    """A short fingerprint of what a request asks, to file its reply under."""
    asked = f"{request.schema_name}\n{request.instructions}\n{request.prompt}"
    return hashlib.sha256(asked.encode()).hexdigest()[:16]


@dataclass
class RecordingClient:
    """Passes every request on to a real client, and keeps each reply under its request's key."""

    inner: ModelClient
    replies: dict[str, str] = field(default_factory=dict[str, str])

    def complete(self, request: ModelRequest) -> ModelReply:
        """The inner client's reply, kept.

        Raises:
            ModelError: If the inner client's call fails; nothing is kept then.
        """
        reply = self.inner.complete(request)
        self.replies[request_key(request)] = reply.text
        return reply


@dataclass(frozen=True)
class ReplayClient:
    """Plays back recorded replies: the same request always gets the reply it got when recorded."""

    replies: Mapping[str, str]
    model: str

    def complete(self, request: ModelRequest) -> ModelReply:
        """The reply recorded for this request.

        Raises:
            ModelError: If this request wasn't recorded (its prompt has changed since, say).
        """
        text = self.replies.get(request_key(request))
        if text is None:
            raise ModelError("no recorded reply for this request")
        return ModelReply(text, self.model, 0, 0, 0.0)
