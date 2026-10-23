"""The container smoke test: build the image, start it, and play one question to its feedback.

Opt in with ``uv run pytest -m container``; it needs Docker, and the first build takes a minute or
two. It talks only to the container, on localhost, with the image's defaults: the template Tutor
and the memory store.
"""

import json
import shutil
import subprocess
import time
import urllib.error
import urllib.request
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

pytestmark = pytest.mark.container

REPO = Path(__file__).parents[2]
IMAGE = "btl:smoke-test"
# Seconds to wait for the server to answer, and for Docker to call it healthy.
PATIENCE = 60.0


def _docker(*args: str) -> str:
    done = subprocess.run(["docker", *args], capture_output=True, text=True, check=False)
    if done.returncode != 0:
        raise AssertionError(f"docker {' '.join(args)} failed:\n{done.stderr}")
    return done.stdout.strip()


def _call(base: str, method: str, path: str, body: object = None) -> Any:
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(
        base + path, data=data, method=method, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.loads(response.read())


def _until(ready: Any, what: str) -> None:
    deadline = time.monotonic() + PATIENCE
    while not ready():
        if time.monotonic() > deadline:
            raise AssertionError(f"gave up waiting for {what}")
        time.sleep(0.2)


@pytest.fixture(scope="module")
def container() -> Iterator[tuple[str, str]]:
    """The running image: its id and the address it answers on."""
    running = shutil.which("docker") is not None and (
        subprocess.run(["docker", "info"], capture_output=True, check=False).returncode == 0
    )
    if not running:
        pytest.skip("Docker isn't running")
    _docker("build", "--tag", IMAGE, str(REPO))
    cid = _docker("run", "--detach", "--health-interval=1s", "--publish", "127.0.0.1::8000", IMAGE)
    try:
        port = _docker("port", cid, "8000").splitlines()[0].rsplit(":", 1)[1]
        yield cid, f"http://127.0.0.1:{port}"
    finally:
        _docker("rm", "--force", cid)


def _answers(base: str) -> bool:
    try:
        return _call(base, "GET", "/api/health") == {"status": "ok"}
    except (urllib.error.URLError, ConnectionError):
        return False


def test_the_container_starts_quickly_and_says_it_is_healthy(container: tuple[str, str]) -> None:
    cid, base = container
    started = time.monotonic()
    _until(lambda: _answers(base), "the health check")
    print(f"answering after {time.monotonic() - started:.1f} s")

    _until(
        lambda: _docker("inspect", "--format", "{{.State.Health.Status}}", cid) == "healthy",
        "Docker to call it healthy",
    )
    # The threat model was fitted when the image was built, not when it started.
    assert "No threat model yet" not in _docker("logs", cid)


def test_the_app_runs_as_a_user_who_can_t_change_it(container: tuple[str, str]) -> None:
    cid, _ = container
    assert _docker("exec", cid, "id", "-u") == "10001"
    refused = subprocess.run(
        ["docker", "exec", cid, "touch", "/app/data/models/expected-threat.json"],
        capture_output=True,
        check=False,
    )
    assert refused.returncode != 0


def test_a_question_goes_round_to_its_feedback(container: tuple[str, str]) -> None:
    _, base = container
    _until(lambda: _answers(base), "the health check")
    with urllib.request.urlopen(base + "/", timeout=10) as page:
        assert b'<div id="root">' in page.read()

    _call(base, "POST", "/api/viewers", {"viewer_id": "smoke", "seed": 7})
    step = _call(base, "POST", "/api/viewers/smoke/next")
    while step["kind"] != "question":  # a match can end before its first question
        step = _call(base, "POST", "/api/viewers/smoke/next")
    pick = step["options"][0]["key"]
    feedback = _call(
        base, "POST", "/api/viewers/smoke/answers", {"pack_id": step["pack_id"], "key": pick}
    )

    assert feedback["chosen"] == pick and feedback["source"] == "template"
    assert feedback["explanation"]
