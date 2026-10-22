# The AI Tutor: evaluation

How often the model's words reach the viewer, how long they take, and whether they are any good. The numbers come from `btl tutor-eval`, run against `gpt-5.4-nano` in Azure AI Foundry. The judgement comes from Lily's hand review of 20 samples.

## How it was measured

- **Packs:** `btl tutor-eval` takes evidence packs from the course's own matches, as viewers would meet them (`learn/samples.py`). It keeps up to *n* packs of each kind of question, at each level, asked live and later, so rare kinds aren't drowned out by common ones.
- **Wordings:** for each pack, the `VerifiedTutor` words the question, then the feedback after a right pick and after a wrong one. Each wording ends in one of three ways:
  - **first try:** the model's first reply passed every check;
  - **repaired:** it passed after one repair;
  - **template:** it fell back.
- **Plan's targets:**
  - at least 80% of replies pass on the first try;
  - at least 95% of shown text is model-worded after repair;
  - the 95th percentile of call time is under 5 s.
- **Model settings:** reasoning effort `none`, the Responses API with a strict JSON schema, and four packs worded at once.
- **Not measured:** "why booked" questions are rare and didn't come up in the sampled sessions. Their prompt is the same as "why play on", which did.

## Prompt versions

| Version | What changed | First try | Model-worded | Sample |
|---|---|---|---|---|
| 1 | Instructions mirroring the Verifier; the template's question as a plain version | 40% | 70% | 1 session, 1 per kind (90 wordings) |
| 2 | Times and shirt numbers named as numbers; the template's feedback as a plain version; real examples of option facts (`{answer.lines_broken}`, not `{answer.name}`); whole-sentence facts listed apart | 52% | 84% | the same |
| 3 | Mix-ups numbered from 1. Not in the prompt: values the model writes out in full are turned back into their slots before checking (`slotify`), preferring `{answer}`/`{chosen}`, then outcome facts | 74% | 93% | the same |
| 3 | (the full run below) | **80%** | **94%** | 3 sessions, 2 per kind (192 wordings) |

What each change fixed, in the order the failures showed:
- **Version 1 → 2.** The model wrote values beside their slots, copied `{answer.name}` literally from the prompt's own description, left out `{answer}`, and copied the prompt's "(a whole sentence…)" note into its text.
- **Version 2 → 3.** Most remaining failures were values written out in full: "00:32", "#10 Chinedu Trankwo", "0–0". Telling the model not to do this wasn't enough.

  Turning such a value back into its slot keeps the guarantee, since every number and name shown is still word for word a fact from the pack. Only facts the text may use are converted, so an outcome copied into a question is still rejected. The model also once picked mix-up "3" of three, counting from one.

## Results (prompt version 3)

Prompt version 3, model gpt-5.4-nano: 192 wordings, 231 calls.

#### Pass rates

| What | Wordings | First try | Repaired | Template | Model-worded |
|---|---|---|---|---|---|
| Questions | 64 | 63 (98%) | 1 (2%) | 0 (0%) | 64 (100%) |
| Feedback | 128 | 90 (70%) | 26 (20%) | 12 (9%) | 116 (91%) |
| All | 192 | 153 (80%) | 27 (14%) | 12 (6%) | 180 (94%) |

#### By concept

| Concept | Wordings | First try | Repaired | Template | Model-worded |
|---|---|---|---|---|---|
| Line-breaking passes | 36 | 28 (78%) | 7 (19%) | 1 (3%) | 35 (97%) |
| Restarts | 36 | 31 (86%) | 4 (11%) | 1 (3%) | 35 (97%) |
| Counter-pressing | 36 | 31 (86%) | 4 (11%) | 1 (3%) | 35 (97%) |
| Offside | 36 | 31 (86%) | 2 (6%) | 3 (8%) | 33 (92%) |
| Fouls and cards | 48 | 32 (67%) | 10 (21%) | 6 (12%) | 42 (88%) |
| All | 192 | 153 (80%) | 27 (14%) | 12 (6%) | 180 (94%) |

#### By kind of question

| Asks | Wordings | First try | Repaired | Template | Model-worded |
|---|---|---|---|---|---|
| lines broken | 12 | 9 (75%) | 3 (25%) | 0 (0%) | 12 (100%) |
| where to pass | 12 | 11 (92%) | 1 (8%) | 0 (0%) | 12 (100%) |
| gap width | 12 | 8 (67%) | 3 (25%) | 1 (8%) | 11 (92%) |
| what restart | 36 | 31 (86%) | 4 (11%) | 1 (3%) | 35 (97%) |
| what they did | 12 | 11 (92%) | 0 (0%) | 1 (8%) | 11 (92%) |
| seconds to win back | 24 | 20 (83%) | 4 (17%) | 0 (0%) | 24 (100%) |
| flag or not | 12 | 9 (75%) | 2 (17%) | 1 (8%) | 11 (92%) |
| was it offside | 12 | 10 (83%) | 0 (0%) | 2 (17%) | 10 (83%) |
| after the foul | 36 | 24 (67%) | 7 (19%) | 5 (14%) | 31 (86%) |
| who is offside | 12 | 12 (100%) | 0 (0%) | 0 (0%) | 12 (100%) |
| why play on | 12 | 8 (67%) | 3 (25%) | 1 (8%) | 11 (92%) |
| All | 192 | 153 (80%) | 27 (14%) | 12 (6%) | 180 (94%) |

#### Checks failed on the first try

| Check | First tries failing it |
|---|---|
| slots | 0 (0%) |
| bare_number | 9 (5%) |
| names | 3 (2%) |
| vocabulary | 0 (0%) |
| hint | 1 (1%) |
| verdict | 3 (2%) |
| grounded | 18 (9%) |
| comparison | 0 (0%) |
| misconception | 0 (0%) |
| echo | 10 (5%) |
| length | 4 (2%) |
| (no reply) | 0 (0%) |

#### Time and tokens

- Calls: 231, of which 0 got no usable reply.
- Seconds per call: median 1.81, 95th percentile 2.60.
- Tokens: 228,566 in, 22,146 out.

**Against the targets:**
- **First try:** 80%, which meets the target. Questions 98%, feedback 70%.
- **Model-worded:** 94%, one point short of 95%. Questions 100%, feedback 91%. The fouls questions are the weakest (88%): their outcome facts are whole sentences ("Hexham Anchors get a free kick."), which the model tends to fold into its own sentences.
- **Time:** median 1.8 s and 95th percentile 2.6 s per call, inside 5 s. A wording that needs a repair takes about twice as long.
- **Cost:** about 230 calls, with 229,000 tokens in and 22,000 out, for 192 wordings. That is roughly 1,200 tokens in and 115 out per wording. `btl tutor-eval --price-in … --price-out …` turns this into dollars at the current price.

**Recorded replies.** `tests/fixtures/tutor-replies.json` holds 104 real replies, from a smaller run with the tests' own threat model. The tests replay them to check two things:
- every request today still matches one that was recorded, so a prompt change without re-recording fails a test;
- they still pass the Verifier as they did then.

## Hand review

Twenty samples, four per concept: `tutor-review.md`. For each, Lily judges whether it is true to the evidence, right for the level, gives nothing away before answering (for questions), and reads naturally.

**Result (2026-10-22):** Lily scanned all twenty and judged them accurate enough for the prototype. She found nothing the Verifier accepted that was wrong about the match, so no new check was needed. This was a scan rather than a sample-by-sample marking, so the boxes in the sheet are left unticked.

Some wording is clumsy without being wrong. In sample 1, for example: "For how many defensive lines did that pass go through". That is the kind of thing a stronger model or another round of prompt work would smooth, and the README's honest limits say so.
