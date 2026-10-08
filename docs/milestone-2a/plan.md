# Milestone 2a Plan: The loop in the terminal

> Agreed 2026-10-08 (amended the same day, before T1, to add phase-of-play gating). This plan is frozen; where implementation diverges, see [implementation-notes.md](implementation-notes.md).
> Milestone 2 is split three ways: **2a** the learning engine in the terminal, **2b** the Foundry Tutor and the Verifier, **2c** the web page. Each gets its own branch, plan, and `--no-ff` merge. 2a's branch is `feature/learning-loop`.

## Context

Milestone 1 can simulate a match with teachable moments in it, but nobody is asked anything. 2a builds the learning engine:
- a Bayesian Knowledge Tracing (BKT) learner model, driven by Lily's concept map;
- a **live** moment selector;
- a **phase-of-play gate** that decides when a question may be asked;
- questions that adapt to the viewer;
- an evidence pack for every question;
- feedback from templates written in code.

A viewer plays three matches in the terminal. Each moment is described in text with the existing ASCII pitch. The viewer types A, B or C, gets feedback, and sees per-concept progress bars.

**Guiding principles:**
- **The match never depends on the viewer.** With real data, a match is what it is. Adaptation lives in *which moments we ask about*, *when*, and *how*. Every candidate comes from the detectors.
- **Never prompt during a transition.** On a real broadcast you can't freeze a counter-attack. A moment that happens in a transition is queued and asked at the next dead ball or break. By then the viewer has seen how the play ended, so a deferred question is always a **review** question, never a predict question.

No Azure, no web, no LLM. Everything is pure Python and fully testable. 2a deliberately puts in place the interfaces that 2b and 2c plug into: the `Tutor` protocol, fact slots, the question views, the `Grader`, and the `LearnerStore`.

**Budget:** about 6 days, ending around 2026-10-15. That leaves about 11 days for 2b, 2c, Milestone 3 and the video. The first cut below brings it back towards 5.

## How the loop works

```
session seed ─► match seeds ─► simulate_with_moments(MATCH_DESIGN)          # same for every viewer
                                        │
              detectors ─► candidates (quality filter, difficulty 0–1)
              phase_timeline(match) ─► settled / transition / dead ball / break
                                        │
   play through the match in order ─────┤ at each candidate: live selector
                                        │   (frontier, difficulty band, spacing, cap)
                                        ▼
                                   phase gate
                     ┌──────────────────┴───────────────────┐
             settled: ask now                     transition: queue it
             (predict allowed)                    ─► next dead ball ≥ 15 s or break:
                     │                               deliver, re-levelled to mastery now
                     └──────────────────┬───────────────────┘
                                        ▼
               question (form + options by level and delivery) ─► evidence pack
                                        │
                  QuestionView ─► TemplateTutor ─► viewer answers A/B/C
                                        │
                  ChoiceGrader ─► BKT update ─► FeedbackView ─► TemplateTutor ─► feedback + bars
                                        │
                        mastery changed ─► the next decision is judged against it
```

## Decisions

**Matches.** Every match uses one fixed `MATCH_DESIGN`, the same for every viewer: each active concept planted at levels 1, 2 and 3. Planting is a stand-in for "a real match has plenty of good moments". Nobody's knowledge influences it. Natural detections add more candidates.

**Planted moments are mostly review material; live predict comes from natural play (Lily's choice).**
- Every planted line-break begins with an interception, and its pass comes about 5 s later. That's a transition, so it is queued and asked as a review question. Planted counter-presses are transitions too.
- **Live predict questions come only from natural line-breaks in settled play** that pass the quality filter. The templates are unchanged.
- **This needs enough of them.** A band test over 40 seeds (T6) checks that each match has natural settled line-break candidates in each difficulty band. If a band is thin, the selector simply finds no live candidate there, and that concept's questions arrive as deferred review instead. The loop still works, with fewer predict questions. The measured counts go into the implementation notes.

**Candidates come from the detectors, never from planting records.**
- Each candidate needs a **difficulty from 0 to 1, computed by its detector**:
  - Line-breaking already has one.
  - Counter-press gets one in 2a: the longer the opponent keeps the ball before it's won back, the harder the press is to spot.
- **Quality filter, in football terms**, so it would apply unchanged to real data. A natural line break must:
  - go forward at least 15 m;
  - add threat;
  - allow a consistent set of options.

  Every planted moment must pass the filter.

**Phase of play gates delivery.**
- **`phase_timeline(match)` in `concepts/phase.py`** reads football from events only, so it would work unchanged on real data. It never trusts the simulator's own `phase` field, just as detectors never trust its `possession_id`. As a sanity check, a test compares its transitions with that field and expects broad agreement.
- It splits the match into segments that cover it with no gaps or overlaps:

  | Segment | Rule |
  |---|---|
  | Transition | From a turnover until the team in possession completes `TRANSITION_PASSES` = 4 passes, `TRANSITION_SECONDS` = 12 s pass, or the ball goes dead |
  | Dead ball | From the event that sends the ball dead (out of play, or a goal) to the restart. A window under `MIN_QUESTION_WINDOW` = 15 s is too short for a question |
  | Break | Half-time and full time |
  | Settled | Everything else |

- **The gate:**

  | Phase | What can be asked |
  |---|---|
  | Settled | Live: predict (levels 2–3), pausing before the play, or identify |
  | Transition | Nothing. The candidate is queued |
  | Dead ball (15 s or longer) | One queued question |
  | Half-time | Up to 2 queued questions |
  | Full time | Up to 2 queued questions, as the recap |

- **Measured in the sample match:** about 45 dead-ball windows of 15 s or more. Goal kicks (21 s), corners (about 27 s) and kickoffs after a goal (46 s) always qualify. Throw-ins (median 14 s) mostly don't. The simulator has no fouls or free kicks. No simulator change is needed.
- **Queue rules:**
  - The oldest queued question is delivered first.
  - At delivery, the frontier is rechecked and the level re-picked from current mastery.
  - A queued question is dropped if its concept has been mastered since it was queued.
- **Deferred questions are review questions:** identify forms at every level, with wrong options that get closer as the level rises. For example, "How many lines did that pass break?" or "How long did they take to win it back: under 3 seconds, 3–5, or more than 5?" They open with context: "Dead ball (goal kick). Earlier, at {minute}…"

**Live selector.**
- **Frontier:** active concepts whose *active* prerequisites are above unlock (0.8) and which are below mastery (0.95). Prerequisites that aren't built yet count as met.
- **Target level from current mastery:** p < 0.4 → 1, p < 0.7 → 2, otherwise 3.
- **Difficulty bands, which overlap:** level 1 → 0–0.4, level 2 → 0.3–0.7, level 3 → 0.6–1.
- **Walking candidates in match order,** it selects a candidate when:
  - the concept is on the frontier;
  - the difficulty is in the band as of now;
  - at least 8 minutes have passed since the last *prompt*, live or deferred;
  - the in-play cap allows it.
- **The cap of 4 covers in-play prompts only** (live and dead ball). Half-time and full time have their own cap of 2 each and are exempt from spacing.
- **Minimum of two prompts per match, guaranteed at the breaks.** If fewer than 2 prompts have happened by half-time or full time and the queue is empty, ask a review question about the best candidate already passed, ignoring the band. The selector only ever looks back, so there's no look-ahead problem.
- **Empty frontier** (everything mastered): occasional level-3 review prompts. Spaced review comes later.

**Questions adapt to the level and to the delivery:**

| Concept | Level | Form | Delivery | Wrong options |
|---|---|---|---|---|
| Line-breaking | 1 | identify: "How many lines did that pass break?" | live or deferred | far (none / one / two) |
| Line-breaking | 2 | predict: "Where should #8 pass?" | **live, settled only** (natural candidates) | clear (a pass straight back, a sideways pass) |
| Line-breaking | 3 | predict | **live, settled only** | close (the free teammate, the best forward pass that breaks no line) |
| Line-breaking | 2–3, deferred | identify (review) | deferred | closer as the level rises |
| Counter-press | 1–3 | identify (review): "After losing it, what did they do?" / "How long did they take to win it back?" | live or deferred (in practice deferred) | closer as the level rises |

- Counter-press has **no predict form**; that's the honest consequence of gating.
- **Always 3 options,** so guess = 1/3 stays derived, not tuned.
- **Invariant, over 40 seeds × every level × planted and natural candidates:** in a pass question, the right answer has the most lines broken and at least as much threat added as each wrong option.

**The learner model sits behind an interface, so BKT can be swapped** (for example for Performance Factors Analysis).
- **`KnowledgeModel` protocol** (`learn/knowledge.py`):

  | Method | Returns |
  |---|---|
  | `initial_state(concepts)` | the model's starting state |
  | `update(state, observation)` | the new state, plus an `Update` |
  | `mastery(state, concept)` | a number from 0 to 1 |
  | `explain(update)` | one sentence |
  | `thresholds` | unlock and mastery, owned by the model |

- **`Observation`:** concepts (a tuple), correct, option count, difficulty, level, and **`delivery: live | deferred`**. BKT ignores delivery, but the attempt log records it, so a later model can weight review answers differently.
- **The attempt log is the source of truth.** A model's state is derived by replaying it, and cached with the model's name and version.
- **Parameters in the concept map are grouped by model** (`learner_models.bkt`).
- **A contract test suite that every model must pass:**
  - results stay in [0, 1];
  - a correct answer never lowers the estimate;
  - it is deterministic;
  - replaying the log equals updating one answer at a time;
  - `explain()` quotes the update's before and after numbers.

**BKT.**
- **Parameters:** the map's per-tier defaults. Guess is 1 / number of options.
- **The update:** Bayes on the answer, then the learning step. A wrong answer can raise mastery slightly, and the sentence says so.
- **Tier-2 worked trace as a test:** four correct answers give 0.15 → 0.42 → 0.72 → 0.89 → 0.96.

**Evidence pack.**
- Every number the viewer sees is a `Fact`, with a value and number-only display text formatted by code.
- **The pack records** `phase`, `occurred_at`, `delivered_at` and `delivery`.
- **Each question form hides exactly its own answer facts.** Review questions may show the play's path (as level-1 identify does) but never the facts that answer them. Predict questions hide the right option and every outcome fact. The feedback view is the full pack.
- Feedback text uses **fact slots** like `{B.threat_added}`, filled in by code. In 2b the model writes the same slots.

## The concept map

**Where it lives:**
- **`backend/src/btl/learn/concept_map.yaml`**, loaded with `importlib.resources`.
- **`btl/learn/concept_map.py`**, which validates it; nothing else reads the YAML.
- **`docs/concept-map.md`**, a living reference.
- **New dependency:** `pyyaml` and `types-PyYAML`.

**Edits, each listed in the implementation notes:**
- `bkt_defaults` and `thresholds` move under `learner_models.bkt`.
- Add `counter_press`: tier 2, pressure strand, prerequisite `pressing`.
- Add **`phase_of_play`** as an inactive tier-1 concept. `phase_timeline` becomes its detector later, so one piece of code does two jobs.
- The active concepts' text uses only facts we compute.
- `detector:` holds a `ConceptId` value, or null.
- Example club names become `{home_team}` / `{away_team}`.
- Inactive concepts otherwise stay as written.

**Validation tests:**
- ids are unique, and prerequisites exist and form no cycle;
- tiers, strands and question types are the declared ones;
- every placeholder is in its concept's `evidence_fields`;
- every active concept's evidence fields are produced by its builder;
- no betting words.

## Module structure

```
backend/src/btl/
├── concepts/counter_press.py   # + difficulty from seconds to win back
├── concepts/line_breaking.py   # + public lines_broken(snapshot, team_id, start, end)
├── concepts/phase.py           # phase_timeline(match): settled / transition / dead ball / break
├── learn/                      # pure: no I/O, no network, no datetime.now()
│   ├── concept_map.yaml / concept_map.py
│   ├── knowledge.py            # KnowledgeModel protocol, Observation, Update, replay()
│   ├── bkt.py                  # BktModel
│   ├── candidates.py           # MATCH_DESIGN, candidates from detector tags, quality filter
│   ├── questions.py            # forms by level and delivery; near or far distractors
│   ├── evidence.py             # EvidencePack, Fact, per-form question views, feedback view
│   ├── selector.py             # live selection + phase gate + queue
│   ├── learner.py              # LearnerState, Attempt, MatchProgress
│   ├── grader.py               # Answer, Grade, Grader, ChoiceGrader
│   └── session.py              # the loop
├── tutor/                      # base.py, slots.py, templates.py (TemplateTutor)
├── store/                      # LearnerStore protocol; memory and JSON-file implementations
└── cli/app.py                  # + `btl learn`, `btl demo-viewer`
```

**Reused from Milestone 1:**
- `simulate_with_moments`;
- `match_context` and `detect_all`;
- `split_possessions` and `changes_hands_in_open_play`, for turnovers in `phase.py`;
- `seen_by`;
- `ThreatModel.value_at`;
- `pitch_picture`.

## Ordered tasks (one reviewed commit each, tests included)

T-numbers are renumbered from the earlier draft: the old T4b (phase timeline) is now T5.

| # | Task | Acceptance criteria |
|---|---|---|
| 0 | Plan + CLAUDE.md | `docs/milestone-2a/plan.md` as amended; CLAUDE.md updated |
| T1 | Groundwork | CLI tests pass with `FORCE_COLOR` set; `lines_broken` public and used by the detector |
| T2 | Concept map | The edited YAML, including `counter_press` and `phase_of_play`; loader; validation tests; `frontier()` tests; `pyyaml`; `docs/concept-map.md` |
| T3 | Learner model interface + BKT | Protocol, `Observation` (with `delivery`), `replay()`; the contract suite on BKT; the worked trace; `docs/milestone-2a/learner-model.md` |
| T4 | Counter-press difficulty | 0–1 from seconds to win back, with named thresholds; planted levels detected in difficulty order over 40 seeds |
| T5 | Phase timeline (`concepts/phase.py`) | Segments cover the match with no gaps or overlaps; every turnover starts a transition; dead-ball windows run from the ball going dead to the restart; windows of 15 s or more per match land in a stated band over 40 seeds; planted line-breaks and counter-presses are both classified as transitions; broad agreement with the simulator's own `phase` field |
| T6 | Candidates | `MATCH_DESIGN`; candidates from detector tags only (`candidates.py` never reads `match.planted`); quality filter; every planted moment survives it; **natural settled line-break candidates per match, per difficulty band, land in a stated band over 40 seeds** |
| T7 | Questions and options | Forms by level and delivery; counter-press has no predict form; wrong options get closer as the level rises; the invariant over 40 seeds |
| T8 | Evidence pack | Deterministic `pack_id`; each form hides exactly its answer facts; phase and delivery fields; displays match values |
| T9 | Live selector, gate and queue | Table-driven tests: frontier, bands, spacing from the last prompt, the in-play cap of 4, break caps of 2, queue order, re-levelling at delivery, dropping mastered concepts, the minimum of 2 met through breaks; a property test over 40 seeds that no prompt is ever delivered inside a transition |
| T10 | Grader, Tutor protocol, slots, TemplateTutor | Templates differ by level; deferred templates open with phase context; every slot fills; import rule for `tutor/` |
| T11 | Learner store | Contract suite on the memory and JSON stores |
| T12 ★ | Session + terminal (`btl learn`, `btl demo-viewer`) | Plays by hand and resumes across runs; the terminal shows why it's asking now (the phase label); end-to-end: the demo viewer over three matches, no prompt delivered in a transition, mastery ends higher for both concepts, levels rise within and across matches |
| T13 | Wrap-up | README "Try the learning loop" plus an honest-limits line (see below); implementation-notes summary; merge `--no-ff` |

## CLAUDE.md changes (commit 0)

- **What this is:** Milestone 2a adds the learning engine in the terminal.
- **The match never depends on the viewer.** Adaptation is in moment choice, timing and question form. Candidates come from detectors, never from `match.planted`.
- **Never prompt during a transition.** Delivery is decided by phase of play, computed from match events only. Deferred questions are review questions, never predict.
- **Layout:** subpackages schema, league, sim, plant, value, concepts, learn, tutor, store, cli, plus `replay.py`. The concept map is `learn/concept_map.yaml`.
- **Feedback rule:** `tutor/` never imports sim, value, concepts or plant. Every number shown comes from the evidence pack, through a fact slot.
- **The learner model:** behind `KnowledgeModel`; the attempt log is the source of truth.
- **Time:** `learn/` takes time as a parameter and never reads the clock.

## Risks and cuts

1. **Dead-ball windows too rare or too short,** so questions pile up at the breaks. The sample already has about 45 qualifying windows. A band test in T6 guards it, and 15 s is a named constant.
2. **Too few natural settled line-breaks in a band,** so few live predict questions. T6's band test measures it. The loop degrades to deferred review rather than breaking. If it bites, the fix is the option set aside: a settled build-up in the template.
3. **Counter-press is review-only,** which is less exciting than predict. That's the honest consequence, and it's documented.
4. **Natural candidates that teach badly.** The quality filter and the options invariant guard this.
5. **BKT moves fast on few answers.** The update sentence explains each jump.

**Cut order if short:**
1. **Deliver deferred questions only at half-time and full time,** skipping dead-ball windows. This halves the queue logic and keeps the core rule.
2. Resuming across runs (T11 slips to 2b).
3. Level-1 identify for live line-breaks; deferred review stays.
4. The hand-built options fixture.

**Honest limit for the README:** on a real live feed, even pausing before a play in settled possession isn't possible. Predict questions would become quick answer-in-five-seconds prompts while play continues.

## Verification

- From `backend/`: `uv run pytest`, `ruff check`, `ruff format --check` and `pyright` all pass.
- `uv run btl demo-viewer` prints three matches in which:
  - each prompt is labelled with its phase;
  - nothing is asked in a transition;
  - questions get harder as answers improve.
- `uv run btl learn --viewer lily` can be played by hand, quit, and resumed.
