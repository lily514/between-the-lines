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
| 3 | (full run) | 80% | 94% | 3 sessions, 2 per kind (192 wordings) |
| 4 | T8: the feedback prompt tells the viewer's recent answers on the concept, which the model "may mention" in words; a wrong pick is measured after a sample history | 77% | 91% | full run |
| 5 | The explanation opens with one short clause about those answers, in words | **80%** | **92%** | full run (below) |

What each change fixed, in the order the failures showed:
- **Version 1 → 2.** The model wrote values beside their slots, copied `{answer.name}` literally from the prompt's own description, left out `{answer}`, and copied the prompt's "(a whole sentence…)" note into its text.
- **Version 2 → 3.** Most remaining failures were values written out in full: "00:32", "#10 Chinedu Trankwo", "0–0". Telling the model not to do this wasn't enough.

  Turning such a value back into its slot keeps the guarantee, since every number and name shown is still word for word a fact from the pack. Only facts the text may use are converted, so an outcome copied into a question is still rejected. The model also once picked mix-up "3" of three, counting from one.

**How noisy these numbers are.** The model's replies vary from run to run, and nothing here fixes its sampling.
- **Unchanged prompt:** the question prompt was identical in versions 3 and 4, yet questions passed first time 98% of the time in one full run and 91% in the next.
- **Small runs:** a 90-wording run moved further still, from 97% to 77%.

So differences of a few points between versions are within the noise.

**Version 4 to 5.** Told it "may mention" the viewer's recent answers, the model mentioned them in none of 16 feedbacks after a wrong pick. Asked to open with one short clause about them, it did in 11 of 16 ("You've been reading these well lately, but this kind has tripped you up before."). Some of those clauses are clumsy.

## Results (prompt version 5)

Prompt version 5, model gpt-5.4-nano: 192 wordings, 231 calls.

#### Pass rates

| What | Wordings | First try | Repaired | Template | Model-worded |
|---|---|---|---|---|---|
| Questions | 64 | 58 (91%) | 6 (9%) | 0 (0%) | 64 (100%) |
| Feedback | 128 | 95 (74%) | 17 (13%) | 16 (12%) | 112 (88%) |
| All | 192 | 153 (80%) | 23 (12%) | 16 (8%) | 176 (92%) |

#### By concept

| Concept | Wordings | First try | Repaired | Template | Model-worded |
|---|---|---|---|---|---|
| Line-breaking passes | 36 | 27 (75%) | 6 (17%) | 3 (8%) | 33 (92%) |
| Restarts | 36 | 33 (92%) | 3 (8%) | 0 (0%) | 36 (100%) |
| Counter-pressing | 36 | 30 (83%) | 3 (8%) | 3 (8%) | 33 (92%) |
| Offside | 36 | 33 (92%) | 2 (6%) | 1 (3%) | 35 (97%) |
| Fouls and cards | 48 | 30 (62%) | 9 (19%) | 9 (19%) | 39 (81%) |
| All | 192 | 153 (80%) | 23 (12%) | 16 (8%) | 176 (92%) |

#### By kind of question

| Asks | Wordings | First try | Repaired | Template | Model-worded |
|---|---|---|---|---|---|
| lines broken | 12 | 10 (83%) | 1 (8%) | 1 (8%) | 11 (92%) |
| where to pass | 12 | 9 (75%) | 2 (17%) | 1 (8%) | 11 (92%) |
| gap width | 12 | 8 (67%) | 3 (25%) | 1 (8%) | 11 (92%) |
| what restart | 36 | 33 (92%) | 3 (8%) | 0 (0%) | 36 (100%) |
| what they did | 12 | 9 (75%) | 2 (17%) | 1 (8%) | 11 (92%) |
| seconds to win back | 24 | 21 (88%) | 1 (4%) | 2 (8%) | 22 (92%) |
| flag or not | 12 | 12 (100%) | 0 (0%) | 0 (0%) | 12 (100%) |
| was it offside | 12 | 11 (92%) | 0 (0%) | 1 (8%) | 11 (92%) |
| after the foul | 36 | 23 (64%) | 5 (14%) | 8 (22%) | 28 (78%) |
| who is offside | 12 | 10 (83%) | 2 (17%) | 0 (0%) | 12 (100%) |
| why play on | 12 | 7 (58%) | 4 (33%) | 1 (8%) | 11 (92%) |
| All | 192 | 153 (80%) | 23 (12%) | 16 (8%) | 176 (92%) |

#### Checks failed on the first try

| Check | First tries failing it |
|---|---|
| slots | 1 (1%) |
| bare_number | 8 (4%) |
| names | 2 (1%) |
| vocabulary | 0 (0%) |
| hint | 3 (2%) |
| verdict | 2 (1%) |
| grounded | 8 (4%) |
| comparison | 0 (0%) |
| misconception | 0 (0%) |
| echo | 14 (7%) |
| length | 2 (1%) |
| (no reply) | 0 (0%) |

#### Time and tokens

- Calls: 231, of which 0 got no usable reply.
- Seconds per call: median 1.77, 95th percentile 2.55.
- Tokens: 232,856 in, 22,960 out.

**Against the targets:**
- **First try:** 80%, which meets the target. Questions 91%, feedback 74%.
- **Model-worded:** 92%, three points short of 95%. Questions 100%, feedback 88%. The fouls questions are the weakest (81%): their outcome facts are whole sentences ("Hexham Anchors get a free kick."), which the model tends to fold into its own sentences.
- **Time:** median 1.8 s and 95th percentile 2.6 s per call, inside 5 s. A wording that needs a repair takes about twice as long.
- **Cost:** about 230 calls, with 233,000 tokens in and 23,000 out, for 192 wordings. That is roughly 1,200 tokens in and 120 out per wording. `btl tutor-eval --price-in … --price-out …` turns this into dollars at the current price.

**Recorded replies.** `tests/fixtures/tutor-replies.json` holds 105 real replies, for prompt version 5, from a smaller run with the tests' own threat model. The tests replay them to check two things:
- every request today still matches one that was recorded, so a prompt change without re-recording fails a test;
- they still pass the Verifier as they did then.

## Hand review

The review was of prompt version 3's words, before T8 added the clause about the viewer's recent answers. Twenty samples, four per concept: `tutor-review.md`. For each, Lily judges whether it is true to the evidence, right for the level, gives nothing away before answering (for questions), and reads naturally.

**Result (2026-10-22):** Lily scanned all twenty and judged them accurate enough for the prototype. She found nothing the Verifier accepted that was wrong about the match, so no new check was needed. This was a scan rather than a sample-by-sample marking, so the boxes in the sheet are left unticked.

Some wording is clumsy without being wrong. In sample 1, for example: "For how many defensive lines did that pass go through". That is the kind of thing a stronger model or another round of prompt work would smooth, and the README's honest limits say so.
