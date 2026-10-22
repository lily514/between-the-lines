"""`btl learn --tutor foundry`, with a fake model in place of Azure."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from btl.cli import app as cli
from btl.tutor.azure import FoundrySettings
from btl.tutor.prompts import PROMPT_VERSION
from tests.cli.test_learn import saved_model
from tests.fixtures.tutor import ByKind

runner = CliRunner()
FOUNDRY = {
    "COLUMNS": "200",
    "BTL_FOUNDRY_ENDPOINT": "https://example-resource.openai.azure.com/",
    "BTL_FOUNDRY_DEPLOYMENT": "tutor-model",
    "BTL_FOUNDRY_TENANT": "00000000-0000-0000-0000-000000000001",
}


def fake_azure(settings: FoundrySettings) -> ByKind:
    return ByKind()


def learn(tmp_path: Path, env: dict[str, str]) -> tuple[int, str]:
    result = runner.invoke(
        cli.app,
        [
            "learn",
            "--viewer",
            "lily",
            "--learners",
            str(tmp_path / "learners"),
            "--model",
            str(saved_model(tmp_path)),
            "--tutor",
            "foundry",
            "--tutor-log",
            str(tmp_path / "tutor-log.jsonl"),
        ],
        input="A\n" * 30,
        env=env,
    )
    return result.exit_code, result.output


def test_learn_with_the_model_says_who_worded_each_feedback_and_logs_every_call(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cli, "AzureClient", fake_azure)

    code, output = learn(tmp_path, FOUNDRY)

    assert code == 0, output
    assert "Worded by fake-model." in output
    assert "Worded by template (fallback: verdict)." in output
    lines = (tmp_path / "tutor-log.jsonl").read_text().splitlines()
    records = [json.loads(line) for line in lines]
    assert {record["kind"] for record in records} == {"question", "feedback"}
    assert all(
        record["prompt_version"] == PROMPT_VERSION and record["logged_at"] for record in records
    )


def test_learn_with_the_model_needs_its_settings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    for name in ("BTL_FOUNDRY_ENDPOINT", "BTL_FOUNDRY_DEPLOYMENT", "BTL_FOUNDRY_TENANT"):
        monkeypatch.delenv(name, raising=False)

    code, output = learn(tmp_path, {"COLUMNS": "200"})

    assert code == 1 and "Set BTL_FOUNDRY_ENDPOINT" in output
