from typing import ClassVar

import pytest
from typer.testing import CliRunner

from btl.cli import app as cli
from btl.tutor.azure import FoundrySettings
from btl.tutor.model import ModelError, ModelReply, ModelRequest

runner = CliRunner()
WIDE = {"COLUMNS": "200"}
FOUNDRY = {
    "BTL_FOUNDRY_ENDPOINT": "https://example-resource.openai.azure.com/",
    "BTL_FOUNDRY_DEPLOYMENT": "tutor-model",
    "BTL_FOUNDRY_TENANT": "00000000-0000-0000-0000-000000000001",
}


class Answering:
    """Stands in for `AzureClient`: answers, or fails, without the network."""

    fail: ClassVar[bool] = False
    settings: ClassVar[list[FoundrySettings]] = []

    def __init__(self, settings: FoundrySettings) -> None:
        Answering.settings.append(settings)

    def complete(self, request: ModelRequest) -> ModelReply:
        if Answering.fail:
            raise ModelError("PermissionDenied: 401")
        return ModelReply('{"reply": "ready"}', "tutor-model-2026-03-17", 40, 6, 1.234)


@pytest.fixture(autouse=True)
def no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli, "AzureClient", Answering)
    Answering.fail = False
    Answering.settings = []


def test_tutor_ping_reports_the_model_time_and_tokens() -> None:
    result = runner.invoke(cli.app, ["tutor-ping"], env={**WIDE, **FOUNDRY})

    assert result.exit_code == 0, result.output
    assert "tutor-model (tutor-model-2026-03-17) answered in 1.23 s" in result.output
    assert "40 tokens in and 6 out" in result.output
    assert Answering.settings == [FoundrySettings(*FOUNDRY.values())]


def test_tutor_ping_says_which_settings_are_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in FOUNDRY:
        monkeypatch.delenv(name, raising=False)

    result = runner.invoke(
        cli.app, ["tutor-ping"], env={**WIDE, "BTL_FOUNDRY_DEPLOYMENT": "tutor-model"}
    )

    assert result.exit_code == 1
    assert "Set BTL_FOUNDRY_ENDPOINT, BTL_FOUNDRY_TENANT" in result.output


def test_tutor_ping_reports_a_failed_call() -> None:
    Answering.fail = True

    result = runner.invoke(cli.app, ["tutor-ping"], env={**WIDE, **FOUNDRY})

    assert result.exit_code == 1
    assert "No reply from tutor-model: PermissionDenied: 401" in result.output
