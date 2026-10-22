import pytest

from btl.tutor.model import FakeClient, ModelError, ModelRequest

REQUEST = ModelRequest("Instructions.", "A short prompt.", "question", {"type": "object"})


def test_the_fake_model_plays_its_script_and_keeps_every_request() -> None:
    fake = FakeClient(['{"text": "One"}', ModelError("timed out"), '{"text": "Two"}'])

    first = fake.complete(REQUEST)
    with pytest.raises(ModelError, match="timed out"):
        fake.complete(REQUEST)
    third = fake.complete(REQUEST)

    assert (first.text, third.text) == ('{"text": "One"}', '{"text": "Two"}')
    assert first.model == "fake-model" and first.input_tokens == 3
    assert fake.requests == [REQUEST] * 3


def test_the_fake_model_fails_once_its_script_runs_out() -> None:
    with pytest.raises(ModelError, match="no more replies"):
        FakeClient([]).complete(REQUEST)
