import json
from pathlib import Path

import pytest
import uvicorn
from fastapi import FastAPI
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from btl.cli import app as cli
from btl.cli.app import app
from btl.io import save_threat_model
from btl.tutor.azure import FoundrySettings
from tests.fixtures.learning import threat_model
from tests.fixtures.tutor import ByKind

runner = CliRunner()
WIDE = {"COLUMNS": "200"}


def test_openapi_writes_the_schema_the_page_s_types_are_made_from(tmp_path: Path) -> None:
    out = tmp_path / "api" / "openapi.json"

    result = runner.invoke(app, ["openapi", "--out", str(out)], env=WIDE)

    assert result.exit_code == 0, result.output
    schema = json.loads(out.read_text())
    assert set(schema["paths"]) == {
        "/api/viewers",
        "/api/viewers/{viewer_id}",
        "/api/viewers/{viewer_id}/next",
        "/api/viewers/{viewer_id}/answers",
        "/api/clubs",
        "/api/viewers/{viewer_id}/club",
        "/api/viewers/{viewer_id}/team-sheet",
    }
    assert {"QuestionOut", "FullTimeOut", "FeedbackOut", "TeamSheetOut"} <= set(
        schema["components"]["schemas"]
    )


def test_the_page_s_committed_schema_matches_the_api() -> None:
    committed = Path(__file__).parents[3] / "frontend" / "src" / "api" / "openapi.json"

    result = runner.invoke(app, ["openapi"], env=WIDE)

    assert result.exit_code == 0, result.output
    assert result.output == committed.read_text(), (
        "frontend/src/api/openapi.json is out of date. From backend/ run "
        "`uv run btl openapi --out ../frontend/src/api/openapi.json`, then from frontend/ "
        "`npm run api-types`."
    )


def test_serve_runs_the_api_and_says_when_there_is_no_built_page(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    model = tmp_path / "model.json"
    save_threat_model(threat_model(), model)
    served: list[tuple[FastAPI, str, int]] = []

    def run(api: FastAPI, host: str, port: int, log_level: str) -> None:
        served.append((api, host, port))

    monkeypatch.setattr(uvicorn, "run", run)

    result = runner.invoke(
        app,
        [
            "serve",
            *("--model", str(model), "--learners", str(tmp_path / "learners")),
            *("--frontend", str(tmp_path / "dist"), "--port", "8123"),
        ],
        env=WIDE,
    )

    assert result.exit_code == 0, result.output
    assert "serving the API only" in result.output
    assert [(host, port) for _, host, port in served] == [("127.0.0.1", 8123)]


def test_serve_with_the_model_words_the_page_s_questions_through_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    model = tmp_path / "model.json"
    save_threat_model(threat_model(), model)
    served: list[FastAPI] = []

    def run(api: FastAPI, host: str, port: int, log_level: str) -> None:
        served.append(api)

    def fake_azure(settings: FoundrySettings) -> ByKind:
        return ByKind()

    monkeypatch.setattr(uvicorn, "run", run)
    monkeypatch.setattr(cli, "AzureClient", fake_azure)
    env = {
        **WIDE,
        "BTL_FOUNDRY_ENDPOINT": "https://example-resource.openai.azure.com/",
        "BTL_FOUNDRY_DEPLOYMENT": "tutor-model",
        "BTL_FOUNDRY_TENANT": "00000000-0000-0000-0000-000000000001",
    }

    result = runner.invoke(
        app,
        [
            "serve",
            *("--model", str(model), "--learners", str(tmp_path / "learners")),
            *("--frontend", str(tmp_path / "dist"), "--tutor", "foundry"),
            *("--tutor-log", str(tmp_path / "tutor-log.jsonl")),
        ],
        env=env,
    )

    assert result.exit_code == 0, result.output
    page = TestClient(served[0])
    page.post("/api/viewers", json={"viewer_id": "lily", "seed": 7})
    question = page.post("/api/viewers/lily/next").json()
    assert question["text"].startswith("Over to you: what is your read on ")
    assert (tmp_path / "tutor-log.jsonl").read_text().count('"kind": "question"') == 1
