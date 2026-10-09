# Milestone 2c Plan: The web page

> Agreed 2026-10-08. This plan is frozen; where implementation diverges, see [implementation-notes.md](implementation-notes.md). 2c's branch is `feature/web-page`.
> Milestone 2 has three parts: **2a** the learning engine in the terminal (done, f80be81), **2b** the AI Tutor (planned; its plan comes after 2c), **2c** the web page. **2c is built before 2b** because Azure isn't set up yet, and nothing in 2c needs it.

## Context

2a's loop runs in the terminal with an ASCII pitch. 2c puts the same loop in a browser: a small FastAPI layer over `learn/session.py`, and a React page drawn from the design handoff ([design/HANDOFF.md](design/HANDOFF.md), [design/tokens.css](design/tokens.css) and the mockups in [design/](design/)).

**The handoff is a secondary guide.** It sets the look: tokens, colour roles, type, the pitch, tiles, verdicts, bars. **The repo decides behaviour and data.** Where they disagree, the repo wins:

| Handoff says | 2c does | Why |
|---|---|---|
| Plain HTML/JS, no build step | React + strict TypeScript + Vite | Workspace convention, and the stack agreed earlier |
| Northbridge v Westmere; actions 996 and 571 | Whatever clubs and moments the league and the selector produce (seed 7 is now Penrith Sentinels 0–1 Hexham Anchors) | The sample match was regenerated in 2a's T13; the mockup's data is stale |
| Data mapping (§5): phase rules, lines counted by shirt-number ranges, `player_id % 100` | The browser computes no football. Every number, phase and position comes from the API | "Every number has a source": the evidence pack |
| Portrait mapping `X = y, Y = 105 − x` | `X = 68 − y, Y = 105 − x` | With the attack going up, the attacker's left (SPADL y = 68) must be on the left of the screen; `X = y` mirrors the pitch. A test pins this |
| "Right read." / "Good instinct, not this one." | `Grade.verdict` stays the one place verdicts are written; its wording changes to the handoff's, so the terminal gets it too | The verdict belongs to the grade (2a T10) |
| Open item 2: "plant settled moments" | No change | Already decided in 2a: live predict questions come from natural settled play |

**Decided (Lily, 2026-10-08):**
- React + TS + Vite.
- **Step between moments** now, built so that **playing the match at speed** can be added later without reworking anything.
- Screens: **predict, review and feedback** (S2, S3, S4 with the mix-up variant), a **desktop side panel**, and a **simple full-time summary**.

**Not in 2c:**
- the live companion's running captions (S1);
- "Save for the break" and questions-off, which would change the selector;
- Simpler/Deeper;
- the three-level pitch views (S5);
- the radar scouting reports (S6);
- onboarding and placement (S7);
- preferences (S8);
- the curriculum map;
- a theme switch (the tokens already follow the OS setting, dark by default);
- haptics;
- deployment (Milestone 3).

**Budget:** about 5 days, ending around 2026-10-13. Then 2b (about 4 days), Milestone 3 and the video before 2026-10-27.

## How it works

```
browser ── POST /api/viewers ─────────────► start_session (JSON store, shared with `btl learn`)
        ── POST /api/viewers/{id}/next ───► watch_match with a WebViewer:
                                              recorded answers replay, the first unasked
                                              question pauses it ─► QuestionView JSON
                                              (or, if the match is over: full-time summary)
        ── POST /api/viewers/{id}/answers ─► same replay, the answer is given, graded, saved,
           {pack_id, key}                     then it pauses straight after the feedback
                                            ─► Told JSON (verdict, explanation, facts, bars)
```

**The server keeps no session in memory.** 2a made a match replay exactly from its saved answers (that's how `btl learn` resumes). So each request re-runs the viewer's current match up to the next unanswered question and stops there. The `WebViewer` stops `watch_match` by raising an exception: in `ask` when there's no answer for that question, and in `tell` once the feedback is captured. The answer is saved before `tell` runs, so stopping there loses nothing.
- **Cost:** each request re-simulates one match. T1 splits the match preparation (simulate, rate, phase timeline, candidates) out of `watch_match` into `prepare_match`, and the API layer caches it per match seed. A request then only replays the selector.
- **Stale tabs:** the answer carries the `pack_id` it was asked with. If it isn't the pending question, the server answers 409 and the page fetches `/next` again.
- **The answer doesn't also fetch the next question.** In 2b, wording a question means a model call; keeping them separate keeps each request to one Tutor call, and lets the page show the feedback while the next question loads.
- **Nothing hidden leaves the server early.** The question payload is built from the `QuestionView` only: no right answer, no outcome facts, no path for a predict question. A test checks this over 40 seeds.
- **Same records as the terminal.** A viewer can start in `btl learn` and carry on in the browser.

**Ready for playing the match at speed (later).** Each question payload says when and in what phase it's asked (`delivered`: period, seconds, phase, restart) and when the play happened. The page's between-questions area is one component, `MatchStep`, that gets "from this time to the next question's time". A `MatchPlayback` with the same props can replace it, fed later by a frames endpoint built on `replay.py` and the cached `prepare_match`. 2c builds neither the frames endpoint nor the playback.

## Decisions

**Backend (`btl/api/`, new subpackage).**
- **FastAPI**, with pydantic response models mirroring `QuestionView`, `Told` and the summary. The handlers are thin: they call `learn/session.py`.
- **`btl serve`** runs uvicorn and also serves the built page from `frontend/dist`, so the demo is one command. In development, Vite proxies `/api` to it.
- **The server clock** stamps each answer; `learn/` still never reads the clock.
- **Viewer ids** use the store's existing rule (lower-case letters, digits, `-`, `_`). No accounts: the start screen asks for a name. That's honest for a hackathon demo; Milestone 3 decides about real identity.
- **New dependencies:** `fastapi`, `uvicorn`. `httpx` (dev) for `TestClient`.

**Pack additions (T1, `learn/evidence.py`; `pack_version` goes up by one).**
- Each `Marker` says whether it's the **home** team, so the pitch draws home as a filled disc and away as a ring (the handoff tells teams apart by shape, not by which side has the ball).
- The pack gains the play's **real path** for predict questions too (`reveal_path`), used by the reveal animation. `question_view` leaves it out, as it already does every outcome.
- The API also sends the model's **thresholds** (unlock 0.8, mastery 0.95) for the bar's ticks, and each concept's mastery **before and after** the answer, for the bar's "prior" and "gain" parts.

**Frontend (`frontend/`).**
- **The stack:**
  - Vite + React + strict TS, on Node 24 (`.nvmrc`, as in `../Web`).
  - Formatting copies `../Web`'s `.prettierrc` and `.editorconfig`: tabs, no semicolons, single quotes, no trailing commas, 120 wide, no parentheses around a single arrow parameter.
  - ESLint with typescript-eslint, react-hooks and react-refresh, without studiokit.
  - Vitest + Testing Library.
- **API types are generated, not hand-written.** `btl openapi` writes the schema to a file, and `openapi-typescript` turns it into `src/api/schema.d.ts`; both are committed. A test fails if the committed schema is out of date, so a contract change can't land on one side only.
- **Styles:**
  - `src/styles/tokens.css` is the handoff's file as delivered. Component CSS uses only `var(--…)`, never a hex value; a lint check enforces it.
  - Fonts come from Google Fonts, with the handoff's URL.
  - Dark is the default; light follows the OS setting.
- **Components** (one per `.tsx`; helpers in a `.support.ts` beside them):

  | Component | Contents |
  |---|---|
  | `Pitch` (+ `Pitch.support.ts`) | Mapping, markings, home discs, away rings, ball, cropped `viewBox`, option tags at `target_at`, path layer |
  | `AnswerGroup` / `AnswerTile` | `role="radiogroup"`; every state in the handoff, each with an icon and a word |
  | `LockIn` | Disabled until a pick |
  | `PhasePill` | Settled possession, Transition, Dead ball, half-time, full time |
  | `VerdictMark` | Correct, incorrect, mix-up |
  | `ProgressBar` | Prior part, gain, and ticks at unlock and mastery |
  | `StatTile` | Monospace numbers |

- **Screens:**

  | Screen | Contents |
  |---|---|
  | `Welcome` | Name, then start or carry on |
  | `MatchStep` | Header with clubs, score and clock; phase pill; the why-now line; Continue |
  | `QuestionSheet` | Predict (S2) and review (S3) |
  | `Feedback` | S4, with the mix-up variant |
  | `FullTime` | Score, questions asked, each concept's bar from kickoff to now, then "Next match" |

- **Wording:** questions and feedback show the Tutor's filled text exactly as the API sends it. Labels and chips come from the handoff ("Your read", "Lock in B", "The reveal").
- **Stat tiles:** each pack outcome fact, by its display text.
- **Source line:** "Source · match {seed} · action {id} · worded by {source}".
- **Layout:** phone first at 390 px. At 900 px and wider, a 420 px side panel sits beside a "your stream" area in `--bg-deep`, and nothing overlaps.
- **Keys:** only while the sheet is open: 1/2/3 or the arrow keys pick, Enter locks in.
- **Accessibility:**
  - Focus moves to the question heading when the sheet opens, and to the verdict on the reveal.
  - The feedback is in an `aria-live="polite"` region.
  - The pitch has a text alternative: who has the ball, and where each option is.
  - Contrast comes from the tokens.
- **Motion:** the sheet slides in (240 ms), and the reveal draws the path (600 ms) and then fades the text in. With `prefers-reduced-motion`, both become a 120 ms crossfade.

**CI.** A second job, `frontend`, runs `npm ci`, the type check, ESLint, the Prettier check, Vitest and the build. The backend job is unchanged apart from its new tests. Setup steps (Node 24, `npm ci`, `btl serve`) go in `docs/setup.md`.

**The design files.** [`design/`](design/) holds the handoff as reference: `HANDOFF.md`, `tokens.css`, and the mockups 2c uses: `S2-Predict`, `S3-Review`, `S3-Reveal`, `S4-Feedback`, `S4-MixUp`, `D-Live` and `Components` (every component state). They contain no real names or betting terms. The handoff's other screens stay out of the repo. The `.dc.html` files are exported from a design canvas and load a `support.js` that isn't included, so they are read as markup, not opened in a browser.

## Tasks

| # | Task | Done when |
|---|---|---|
| 0 | Plan, CLAUDE.md, design reference | Plan and the design files committed; CLAUDE.md updated (below) |
| T1 | Engine changes for the web | `prepare_match` split out of `watch_match`, with the terminal's behaviour unchanged (existing tests pass as they are); `Marker` home flag; `reveal_path`, which the view leaves out; verdict wording; `pack_version` bumped |
| T2 | Web API (`btl/api/`, `btl serve`) | Start, next, answer and summary endpoints; `WebViewer` pausing; 409 on a stale `pack_id`; tests with `TestClient`: **answering through the API with the demo viewer's picks gives the same attempt log as `btl demo-viewer`**; no outcome fact, right answer or predict path in any question payload over 40 seeds; bad viewer ids refused; a finished viewer handled. A request's time is measured and noted |
| T3 | Frontend scaffold | Vite/React/TS strict; Prettier, ESLint and editorconfig as above; tokens and base styles; generated API types with the up-to-date check; the Vite proxy; the CI job; `docs/setup.md` |
| T4 | Pitch | The mapping test pins the attacker's left on screen-left and attacking up; the crop keeps every option inside the `viewBox`; home and away are told apart by shape; the path layer animates, or crossfades with reduced motion |
| T5 | Question sheet | Predict and review render from fixture payloads; Lock in stays disabled until a pick; the radiogroup works by keyboard; focus goes to the heading; the review form shows the play's path, and predict shows none |
| T6 | Feedback | Correct, incorrect and mix-up states, each with an icon and words, not colour alone; the reveal path; stat tiles from outcome facts; the source line; the learner sentence (`Told.update`) and the bar with prior, gain and both ticks |
| T7 ★ | The loop in the browser | Welcome → MatchStep → question → feedback → … → FullTime → next match, against the real API; resuming after a reload; the desktop side panel; the accessibility and reduced-motion pass; Lily plays one match by hand in both themes, on a phone width and on desktop |
| T8 | Wrap-up | README "Try the web page" with screenshots, the status table, honest limits; implementation-notes summary; `--no-ff` merge |

Rough days: T1 0.5, T2 1, T3 0.5, T4 0.75, T5 0.5, T6 0.5, T7 1, T8 0.25, so about 5.

## CLAUDE.md changes (commit 0)

- **Git workflow:** M2c "The web page": `feature/web-page`. 2c is built before 2b.
- **What this is:** Milestone 2c puts the loop in a browser.
- **Learning design rules:**
  - The browser computes no football and invents no numbers: everything comes from the API.
  - Question payloads are built from the question view only.
- **Layout:** `frontend/` exists now (Vite + React + TS); the subpackages gain `api` (the HTTP routes the page calls; the page itself is `frontend/`).
- **Python style (I/O):** "I/O only in `btl/io.py`, `btl/store/`, `btl/cli/` and `btl/api/`."
- **Commands:** `uv run btl serve`; from `frontend/`: `npm ci`, `npm run dev`, `npm test`, `npm run lint`, `npm run build`, `npm run api-types`.
- **Frontend style:** per the workspace CLAUDE.md; component CSS uses tokens only.

## Risks and cuts

1. **Replaying every request is slow.** The `prepare_match` cache is the plan; if a request still takes over 1 s, the selector's replay is the next thing to cache.
2. **Raising an exception to pause `watch_match`** is unusual. It's contained in `btl/api/`, and the API-against-demo-viewer equivalence test guards it. If it gets awkward, the alternative is a step-by-step session API in `learn/`, which is a larger change.
3. **Front-end polish eats the budget.** The mockups are detailed; the cut order below protects the loop itself.
4. **The pitch's handedness or crop is wrong** and nobody notices. Tests pin both, and T7's hand check compares with `btl moments`' ASCII pitch for the same action.

**Cut order if short:**
1. The desktop keyboard keys (the side panel stays).
2. Generated API types (hand-written types plus one contract test instead).
3. The reveal animation (show the path straight away).
4. The mix-up variant (the misconception shows as plain text).
5. The desktop side panel (phone layout everywhere).

## Verification

- From `backend/`: `uv run pytest`, `ruff check`, `ruff format --check` and `pyright` all pass. From `frontend/`: `npm run lint`, `npm test` and `npm run build` all pass. CI runs both jobs.
- `uv run btl serve`, then open the page: play match 1 by name, answering a predict question (if one comes up) and review questions. Reload mid-match and it carries on. Finish on the full-time summary.
- A record started in the browser carries on in `uv run btl learn --viewer NAME`, and vice versa.
- In DevTools, the question's network response has no right answer or outcome numbers.
- Check both themes (OS setting), a 390 px width and desktop width, keyboard only, and reduced motion.

## After approval

Create `feature/web-page` from main. Put this plan at `docs/milestone-2c/plan.md` and show it to Lily before committing ("Add Milestone 2c plan"). The design reference goes in the same commit. Then commit CLAUDE.md, then start T1.
