"""The Azure AI Foundry client: the only code in the package that talks to the network.

It calls a model deployment through the Responses API, with the reply held to a JSON schema
(structured output) and no reasoning, which keeps a nano model quick. It signs in with Microsoft
Entra ID through the Azure CLI, never with a key: key access is switched off on the resource.
The tenant is always named, because an `az login` can default to a different tenant from the
one the resource is in, and Azure refuses that tenant's tokens.
"""

import time
from collections.abc import Callable
from dataclasses import dataclass

import httpx2
import openai
from azure.core.credentials import TokenCredential
from azure.core.exceptions import AzureError
from azure.identity import AzureCliCredential, get_bearer_token_provider
from openai import AzureOpenAI

from btl.tutor.model import ModelError, ModelReply, ModelRequest

API_VERSION = "2025-04-01-preview"
TOKEN_SCOPE = "https://cognitiveservices.azure.com/.default"
# gpt-5.4-nano accepts none, low, medium, high and xhigh; "minimal" is refused.
REASONING_EFFORT = "none"


@dataclass(frozen=True, slots=True)
class FoundrySettings:
    """Where the model is: the resource's endpoint, the deployment's name, and the tenant."""

    endpoint: str
    deployment: str
    tenant: str


def cli_credential(tenant: str) -> AzureCliCredential:
    """The developer's `az login`, asked for tokens from ``tenant``."""
    return AzureCliCredential(tenant_id=tenant)


class AzureClient:
    """A `btl.tutor.model.ModelClient` for a deployment in Azure AI Foundry."""

    def __init__(
        self,
        settings: FoundrySettings,
        *,
        credential: TokenCredential | None = None,
        http_client: httpx2.Client | None = None,
    ) -> None:
        """Connect to the deployment in ``settings``.

        Args:
            settings: Where the model is.
            credential: Where tokens come from; by default the Azure CLI, in the settings' tenant.
            http_client: The HTTP client to send through; tests pass one with a mock transport.
        """
        token: Callable[[], str] = get_bearer_token_provider(
            credential or cli_credential(settings.tenant), TOKEN_SCOPE
        )
        self._deployment = settings.deployment
        # No retries: the Tutor has its own time budget, and falls back to the template.
        self._client = AzureOpenAI(
            azure_endpoint=settings.endpoint,
            api_version=API_VERSION,
            azure_ad_token_provider=token,
            http_client=http_client,
            max_retries=0,
        )

    def complete(self, request: ModelRequest) -> ModelReply:
        """Send the request to the deployment.

        Raises:
            ModelError: If signing in or the call fails, times out, or the reply is incomplete.
        """
        started = time.perf_counter()
        try:
            response = self._client.responses.create(
                model=self._deployment,
                instructions=request.instructions,
                input=request.prompt,
                text={
                    "format": {
                        "type": "json_schema",
                        "name": request.schema_name,
                        "schema": dict(request.schema),
                        "strict": True,
                    }
                },
                reasoning={"effort": REASONING_EFFORT},
                timeout=request.timeout,
            )
        except (openai.OpenAIError, AzureError) as error:
            raise ModelError(f"{type(error).__name__}: {error}") from error
        seconds = time.perf_counter() - started
        if response.status != "completed" or not response.output_text:
            raise ModelError(f"the reply was {response.status} with no text")
        usage = response.usage
        return ModelReply(
            text=response.output_text,
            model=response.model,
            input_tokens=0 if usage is None else usage.input_tokens,
            output_tokens=0 if usage is None else usage.output_tokens,
            seconds=seconds,
        )
