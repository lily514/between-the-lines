import io
import json
import logging
from collections.abc import Iterator
from pathlib import Path

import pytest
import uvicorn
from fastapi import FastAPI
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from btl.api.events import LOGGER, emit
from btl.cli import app as cli
from btl.cli.app import app
from btl.io import save_threat_model
from btl.store.memory import MemoryLearnerStore
from btl.tutor.azure import FoundrySettings
from tests.fixtures.learning import threat_model
from tests.fixtures.tutor import ByKind

runner = CliRunner()
WIDE = {"COLUMNS": "200"}
EVENTS_TO_STDOUT = cli._events_to_stdout  # pyright: ignore[reportPrivateUsage]


@pytest.fixture(autouse=True)
def events_stay_put(monkeypatch: pytest.MonkeyPatch) -> None:
    # Sending events to stdout changes the process's logging, so the serve tests leave it alone.
    monkeypatch.setattr(cli, "_events_to_stdout", lambda: None)


@pytest.fixture
def events_logger() -> Iterator[logging.Logger]:
    logger = logging.getLogger(LOGGER)
    handlers, level = list(logger.handlers), logger.level
    yield logger
    logger.handlers, logger.level = handlers, level


def test_serve_writes_events_to_stdout_one_json_object_a_line(
    events_logger: logging.Logger, monkeypatch: pytest.MonkeyPatch
) -> None:
    out = io.StringIO()
    monkeypatch.setattr("sys.stdout", out)

    EVENTS_TO_STDOUT()
    emit("full_time", viewer_id="ana", match_number=1, finished=False)

    assert json.loads(out.getvalue()) == {
        "event": "full_time",
        "viewer_id": "ana",
        "match_number": 1,
        "finished": False,
    }


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


def test_serve_in_azure_signs_in_as_the_app_s_identity_and_needs_no_tenant(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    model = tmp_path / "model.json"
    save_threat_model(threat_model(), model)
    settings: list[FoundrySettings] = []

    def fake_azure(given: FoundrySettings) -> ByKind:
        settings.append(given)
        return ByKind()

    def run(api: FastAPI, host: str, port: int, log_level: str) -> None:
        pass

    monkeypatch.setattr(uvicorn, "run", run)
    monkeypatch.setattr(cli, "AzureClient", fake_azure)
    env: dict[str, str | None] = {
        **WIDE,
        "BTL_FOUNDRY_ENDPOINT": "https://example-resource.openai.azure.com/",
        "BTL_FOUNDRY_DEPLOYMENT": "tutor-model-demo",
        "BTL_FOUNDRY_TENANT": None,
        "AZURE_CLIENT_ID": "00000000-0000-0000-0000-00000000c11d",
    }

    result = runner.invoke(
        app,
        [
            "serve",
            *("--model", str(model), "--store", "memory", "--tutor", "foundry"),
            *("--frontend", str(tmp_path / "dist"), "--tutor-log", str(tmp_path / "log.jsonl")),
        ],
        env=env,
    )

    assert result.exit_code == 0, result.output
    assert [(s.deployment, s.client_id) for s in settings] == [
        ("tutor-model-demo", "00000000-0000-0000-0000-00000000c11d")
    ]


def test_serve_reads_its_options_from_the_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    model = tmp_path / "model.json"
    save_threat_model(threat_model(), model)
    served: list[tuple[FastAPI, str, int]] = []

    def run(api: FastAPI, host: str, port: int, log_level: str) -> None:
        served.append((api, host, port))

    monkeypatch.setattr(uvicorn, "run", run)
    env = {
        **WIDE,
        "BTL_HOST": "0.0.0.0",
        "BTL_PORT": "8124",
        "BTL_STORE": "memory",
        "BTL_LEARNERS": str(tmp_path / "learners"),
        "BTL_MODEL": str(model),
        "BTL_FRONTEND": str(tmp_path / "dist"),
        "BTL_TUTOR": "template",
    }

    result = runner.invoke(app, ["serve"], env=env)

    assert result.exit_code == 0, result.output
    [(api, host, port)] = served
    assert (host, port) == ("0.0.0.0", 8124)
    page = TestClient(api)
    assert page.post("/api/viewers", json={"viewer_id": "lily", "seed": 7}).status_code == 200
    assert not (tmp_path / "learners").exists()  # the memory store writes no files


def test_serve_with_the_blob_store_needs_its_account(tmp_path: Path) -> None:
    model = tmp_path / "model.json"
    save_threat_model(threat_model(), model)

    result = runner.invoke(
        app,
        ["serve", "--model", str(model), "--store", "blob"],
        env={**WIDE, "BTL_BLOB_ACCOUNT_URL": None},
    )

    assert result.exit_code == 1
    assert "--blob-account-url" in result.output


def test_serve_in_azure_keeps_learners_in_blobs_signed_in_as_the_app(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    model = tmp_path / "model.json"
    save_threat_model(threat_model(), model)
    opened: list[tuple[str, str, str | None]] = []

    def fake_container(
        account_url: str, container: str, client_id: str | None, tenant: str
    ) -> object:
        opened.append((account_url, container, client_id))
        return object()

    def run(api: FastAPI, host: str, port: int, log_level: str) -> None:
        pass

    monkeypatch.setattr(uvicorn, "run", run)
    monkeypatch.setattr(cli, "blob_container", fake_container)

    def store(container: object) -> MemoryLearnerStore:
        return MemoryLearnerStore()

    monkeypatch.setattr(cli, "BlobLearnerStore", store)
    env = {
        **WIDE,
        "BTL_STORE": "blob",
        "BTL_BLOB_ACCOUNT_URL": "https://example.blob.core.windows.net",
        "AZURE_CLIENT_ID": "00000000-0000-0000-0000-00000000c11d",
    }

    result = runner.invoke(app, ["serve", "--model", str(model)], env=env)

    assert result.exit_code == 0, result.output
    assert opened == [
        (
            "https://example.blob.core.windows.net",
            "learners",
            "00000000-0000-0000-0000-00000000c11d",
        )
    ]
