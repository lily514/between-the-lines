"""The evaluation, run on real replies recorded from the model: no network."""

from collections import Counter
from functools import cache
from pathlib import Path

from btl.io import load_replies
from btl.learn.samples import sample_packs
from btl.learn.session import Course
from btl.tutor.evaluation import Worded, evaluate, report, review_sheet
from btl.tutor.foundry import FoundryTutor
from btl.tutor.model import ReplayClient
from btl.tutor.prompts import PROMPT_VERSION
from btl.tutor.templates import TemplateTutor
from tests.fixtures.learning import threat_model

REPLIES = Path(__file__).parents[1] / "fixtures" / "tutor-replies.json"
RECORD = (
    "Re-record them: save tests.fixtures.learning.threat_model() to a file, then run "
    "`btl tutor-eval --model FILE --seeds 1 --per-kind 1 "
    "--record tests/fixtures/tutor-replies.json`."
)


@cache
def replayed() -> tuple[Worded, ...]:
    version, model, replies = load_replies(REPLIES)
    assert version == PROMPT_VERSION, (
        f"The recorded replies are for prompt version {version}. {RECORD}"
    )
    course = Course(threat_model(), TemplateTutor())
    packs = sample_packs(course, range(1), per_kind=1)
    return tuple(evaluate(FoundryTutor(ReplayClient(replies, model)), TemplateTutor(), packs))


def test_every_request_today_was_answered_when_the_replies_were_recorded() -> None:
    errors = [r.error for w in replayed() for r in w.records if r.error is not None]

    assert errors == [], f"The prompts have changed since the replies were recorded. {RECORD}"


def test_the_recorded_replies_still_pass_as_they_did() -> None:
    shown = Counter((w.kind, w.shown) for w in replayed())

    assert shown == {
        ("question", "first try"): 29,
        ("question", "repaired"): 1,
        ("feedback", "first try"): 47,
        ("feedback", "repaired"): 7,
        ("feedback", "template"): 6,
    }
    assert all("{" not in w.text for w in replayed())


def test_the_report_gives_rates_checks_and_cost() -> None:
    text = report(replayed(), PROMPT_VERSION, "gpt-5.4-nano", price_in=0.1, price_out=0.4)

    assert text.startswith(f"Prompt version {PROMPT_VERSION}, model gpt-5.4-nano: 90 wordings")
    assert "| Questions | 30 | 29 (97%) | 1 (3%) | 0 (0%) | 30 (100%) |" in text
    assert "| Fouls and cards |" in text and "| after the foul |" in text
    assert "| grounded |" in text and "Estimated cost: $" in text


def test_the_review_sheet_samples_each_concept_beside_its_template() -> None:
    sheet = review_sheet(replayed())

    concepts = {w.concept for w in replayed()}
    assert sheet.count("\n### ") == 4 * len(concepts)
    assert sheet.count("**Model**") == sheet.count("**Template**") == sheet.count("<summary>Facts")
    assert sheet.count("- [ ] Gives nothing away before answering") == 2 * len(concepts)
    assert "(template)" not in sheet
