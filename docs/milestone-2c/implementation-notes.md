# Milestone 2c: Implementation notes

Where implementation diverged from [plan.md](plan.md), or something surprising was learned. One note per occurrence, added in the same commit as the change.

## T1 — Engine changes for the web (2026-10-08)
**Plan said:** split the match preparation out of `watch_match` into `prepare_match` so the API layer can cache it; a home flag on each `Marker`; a `reveal_path` that the question view leaves out; the handoff's verdict wording; bump `pack_version`.
**We did:** as planned, with these choices:
- **`prepare_match(course, seed, match_number)`** returns a `PreparedMatch`: the two clubs, the match seed, the match, its context, its phase timeline and its candidates. Nothing in it depends on the viewer's answers. `watch_match` takes an optional `prepare` callable (session seed and match number in, prepared match out). Without it, it prepares the match each time, as before. The answer-time random generator stays in `watch_match`, because questions draw from it as they are asked.
- **`reveal_path` lives on `EvidencePack`,** not on `Picture`. `QuestionView` carries the picture, so a path stored in the picture would reach the browser before the answer. It is the same path an identify question's picture shows (every action of the play, then where the last one ended), now kept for predict questions too.
- **`Marker.home`** says whether the player is on the home club. `side` still says attacking or defending, relative to the ball.
- **Verdicts** are now "Right read." and "Good instinct, not this one.". They are written in `grader.py` only, so the terminal changes too. The README's demo excerpt was updated.
- **`pack_version` is 2.** Every pack id changes; attempts already saved keep their old ids, which nothing reads back.

**Measured** on Lily's Mac, with the default threat model:
- `prepare_match` takes about 0.14 s (the same over 5 seeds).
- Watching seed 7's first match with the demo viewer takes 0.13 s from scratch, and about 4 ms once the prepared match is cached.

**Why:** the plan left these details open. The measurements are for T2's cache decision.
**Affects:**
- **T2:** caches `PreparedMatch` per (session seed, match number) and passes the cached lookup as `prepare`. With it, a request only replays the selector (a few milliseconds), so no further cache is needed. A plain dict is fine: `Course` holds numpy-backed models, so it can't be a cache key, but a server has one `Course`.
- **T6:** draws `reveal_path` on the reveal.

## T2 — Web API (2026-10-08)
**Plan said:** a FastAPI layer in `btl/api/` with start, next, answer and summary endpoints; a `WebViewer` that pauses the session by raising; 409 on a stale `pack_id`; question payloads from the question view only; the JSON store shared with `btl learn`; `btl serve`, which also serves the built page. Tests: the API with the demo viewer's picks gives the same attempt log as `btl demo-viewer`; no answer or outcome in any question payload over 40 seeds; bad ids refused; a finished viewer handled. Measure a request.
**We did:** as planned, with these choices:
- **Endpoints** (the shapes are pydantic models in `btl/api/models.py`; `btl openapi` writes the schema):

  | Route | Body → response | Errors |
  |---|---|---|
  | `POST /api/viewers` | `{viewer_id, seed?}` → `StatusOut` | 422 bad id |
  | `GET /api/viewers/{id}` | → `StatusOut` | 404, 422 |
  | `POST /api/viewers/{id}/next` | → `QuestionOut` (`kind: "question"`) or `FullTimeOut` (`kind: "full_time"`) | 404, 409 finished |
  | `POST /api/viewers/{id}/answers` | `{pack_id, key}` → `FeedbackOut` | 404, 409 not the waiting question, 422 unknown key |

  - **`StatusOut`:** `viewer_id`, `match_number`, `matches` (3), `finished`, `fixture {home, away}` (null once finished), `concepts [{name, value}]`, `thresholds {unlock, mastery}`.
  - **`QuestionOut`:**
    - `pack_id`, `match_number`, `home`, `away`, `concept_name`;
    - `form` ("identify" or "predict"), `asks`, `level`, and `text` (the Tutor's filled wording);
    - `occurred {period, seconds, clock, phase}`, and `delivered`, which is the same plus `delivery` ("live" or "deferred") and `restart`;
    - `context` (facts as `{value, display}`);
    - `options [{key, label, neutral, target_at}]`;
    - `picture {action_id, markers [{shirt, side, home, x, y, role}], ball, path}`.
  - **`FeedbackOut`:**
    - `correct`, `chosen`, `correct_key`, `verdict`, `explanation`, `takeaway`, `source`, `update`;
    - `concept_name`, `level`, `match_number`, `action_id`, `match_seed` (for the source line);
    - `context`, `outcome`, and `options` (each with `correct`, `chosen`, `neutral`, `outcome`, `target_at`);
    - `picture`, `reveal_path`, `concepts [{name, before, after}]`, `thresholds`.
  - **`FullTimeOut`:** `match_number`, `home`, `away`, `home_goals`, `away_goals`, `questions`, `concepts [{name, before, after}]` (`before` is the kickoff value), `thresholds`, `finished`, `next_match`.
- **Full time moves the viewer on.** `/next` at the end of a match returns the summary, and the record moves to the next match in the same request. That's how `watch_match` ends a match, and it keeps the server free of any memory. A page reloaded after full time sees the next match's first question, not the summary again; the status endpoint still has the bars.
- **An answer can never end a match.** If no question is waiting (say a repeated answer to a match's last question), the session would otherwise play on to full time and save that. `AnswerOnlyStore` wraps the store for answer requests and refuses any save that moves to the next match, so that request returns 409 and changes nothing. A test answers every question twice and checks this.
- **`Asked` gains `prompt`,** the selector's decision. The question payload needs the period and seconds of the moment and of its delivery; `Timing` has only clock text, and the clock can't tell first-half added time from the second half. This is in `learn/session.py` only and doesn't change the pack.
- **`seed_for_viewer`** (the session seed a name gives) moved from the CLI into `learn/session.py`, so `btl learn` and the API choose the same matches for the same name.
- **The course is loaded on the first request that needs it.** `create_app` takes a loader, so `btl openapi` builds the app without a threat model. `btl serve` loads the threat model, or fits it, before it starts listening, as `btl learn` does. That keeps the CLI's helper in the CLI, so `btl/api` never imports `btl/cli`.
- **One lock for every viewer request.** Requests replay and save a viewer's record, so they take turns. One lock is enough for a demo server, and the store's etags would refuse a clash anyway, as a 409.
- **The built page** is served for every path outside `/api` (files where they exist, `index.html` otherwise); paths that escape the folder get `index.html`. Unknown `/api` paths are 404s.
- **The 40-seed check of question payloads** runs the payload builder directly on each seed's candidates: two per concept × 3 levels × live and deferred. Each payload is checked for:
  - no outcome fact names;
  - no `correct`, `correct_key`, `outcome`, `reveal_path`, `chosen` or `explanation`;
  - no threat figure from the outcome;
  - for a predict question, no path.

  Through the API, the full three-match demo session runs once.
- **`httpx2`, not `httpx`,** for FastAPI's `TestClient`. Starlette 1.7 warns that `httpx` is deprecated for its test client, and the test settings turn warnings into errors.

**Measured** with the default threat model, the template Tutor and an in-memory store. The first question of a match, which prepares it, takes 0.14 s. After that, the median request is about 2 ms for `/next` and 2 ms for an answer. A whole three-match session through the API takes about 1 s, most of it the three preparations.

**Why:** the plan left these details open; the answer-only store closes a hole the plan didn't foresee.
**Affects:**
- **T3:** `uv run btl openapi --out ../frontend/src/api/openapi.json` gives the schema for the generated types. `btl serve` listens on port 8000, so the Vite dev server proxies `/api` there.
- **T5–T7:** build against the shapes above. Show `delivered.restart` and `delivered.phase` for why it's asking now, and `occurred.clock` for when the play happened.
- **2b:** an answer request words only the feedback, and `/next` only the question.

## T3 — Frontend scaffold (2026-10-08)
**Plan said:** Vite + React + strict TypeScript on Node 24, formatted like `../Web`, ESLint with typescript-eslint, react-hooks and react-refresh; Vitest + Testing Library; `tokens.css` as delivered, with no colour literals in component CSS; generated API types with an up-to-date check; the Vite proxy; a CI job; `docs/setup.md`.
**We did:** as planned, with these choices:
- **Versions** (exact, so the lockfile and `package.json` agree): React 19.3, Vite 8.3, Vitest 5.0, ESLint 10.12 with typescript-eslint 8.71, Prettier 3.9, openapi-typescript 7.13, jsdom 30.
- **TypeScript 5.9.3, not the latest 7.0.** typescript-eslint supports TypeScript below 6.1, and openapi-typescript needs 5.x. Moving up waits for both.
- **Strictness** beyond `strict`: `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`, `verbatimModuleSyntax`, unused locals and parameters. ESLint uses typescript-eslint's `strictTypeChecked` and `stylisticTypeChecked` rule sets.
- **Formatting** copies `../Web`'s `.prettierrc` and `.editorconfig`: tabs, no semicolons, single quotes, no trailing commas, 120 wide. `npm run lint` runs ESLint, `prettier --check` and the colour check.
- **The colour check** (`scripts/check-css-colours.mjs`) scans every `.css` file under `src/` except `styles/tokens.css` for hex colours and `rgb()`/`hsl()` calls, and fails with each file and line.
- **API types, two checks:**
  - a backend test runs `btl openapi` and compares it with the committed `frontend/src/api/openapi.json`;
  - a frontend test runs openapi-typescript on that file and compares the result with the committed `src/api/schema.d.ts`.

  Each failure says which command to run.
- **`src/api/client.ts`** has one function per endpoint (`startViewer`, `getStatus`, `nextStep`, `answer`), typed from the generated schema. A failed request throws `ApiError` with the HTTP status, so the page can tell a stale question (409) from a bad name (422). FastAPI's error text becomes the message.
- **Reduced motion is left to each component.** A page-wide rule shortening every transition would also remove the 120 ms crossfade the handoff keeps for reduced motion.
- **Light theme:** `tokens.css` already follows the OS setting, and `color-scheme: dark light` lets form controls follow it too.

**Why:** the plan left these details open; the TypeScript version is what the lint and type tools support today.
**Affects:**
- **T4–T7** import types from `src/api/client.ts` (`Question`, `Feedback`, `FullTime`, `Status`). Component CSS uses `var(--…)` only, and handles reduced motion itself. The placeholder `App.tsx` is replaced in T7.

## T4 — Pitch (2026-10-08)
**Plan said:** a `Pitch` component (with `Pitch.support.ts`) that maps the picture to a portrait pitch attacking up, with `X = 68 − y`, `Y = 105 − x` pinned by a test; markings; home discs and away rings; the ball; a `viewBox` cropped to the moment; option tags at `target_at`; a path layer that animates, or crossfades with reduced motion. The crop keeps every option inside the view.
**We did:** as planned, with these choices:
- **Props:** `picture`, `options` (`{key, at}` in picture coordinates), `path` (the play's path: `picture.path` for a review question, `reveal_path` on the reveal), `reveal`, `crop` (`'full'` or `'moment'`) and `label`, the start of what a screen reader hears.
- **The crop keeps the full width** and cuts only the top and bottom, as the handoff's example `-3 14 74 70` does, so players are drawn the same size in every view. It covers the ball, the carrier, every option and the path, with a 10 m margin and a height of at least 50 m. A view that comes within 10 m of a goal line is stretched to show it, because one that stops just short looks cut off.
- **Which players take part:** the one on the ball, and anyone within 1.5 m of an option's target or a point on the path. When there are options or a path, the others drop to 35% (discs) or 55% (rings), as the handoff says. With neither, nobody is dimmed.
- **Options** are dashed arrows from the ball, each with its letter beside the middle of the line, on whichever side is further from the players. A halo marks the carrier, and the ball sits 1.5 m ahead of them.
- **The path** is drawn with `pathLength="1"`, so the reveal traces it by animating `stroke-dashoffset` from 1 to 0 over `--t-path`. With reduced motion, it fades in over `--t-hover` instead. Both are CSS only.
- **What a screen reader hears:** the label, "The team on the ball is attacking upwards", who has the ball and where, and where each option is. Places are "on the left, in the attacking third", from the given coordinates split into thirds. That's arithmetic on the picture, not a judgement about the play, so it doesn't break the "browser computes no football" rule.
- **Fixtures:** `src/test-fixtures/` holds real payloads captured from the API with the template Tutor:
  - a live predict question and its feedback after a wrong pick (seed 7, match 3);
  - a review question on lines broken and its feedback after a right pick;
  - a counter-press review question and its feedback.

  `test-fixtures/index.ts` types them. JSON imports type each pair as `number[]`, so each payload is cast once there.
- **`client.ts` exports `Picture` and `Marker`.**
- **Checked by eye:** the three fixtures were rendered with headless Chrome in both themes. The direction agrees with the terminal's ASCII pitch: that pitch attacks right with high `y` on the top rows, and turning it a quarter-turn anticlockwise (so it attacks up) puts those rows on the left, which is where `X = 68 − y` puts them. The first render showed the crop stopping just short of the goal line and two option letters on top of players; both were fixed as described above.

**Why:** the plan left these details open; the goal-line rule and the letter placement came from looking at the render.
**Affects:**
- **T5:** the question sheet passes the options (from `target_at`) and `crop="moment"`. A review question also passes `picture.path`; a predict question has none.
- **T6:** the reveal passes `reveal_path`, `reveal` and `crop="moment"`.
- **T5–T7** can use the fixtures in `src/test-fixtures/index.ts`.
- **Not drawn yet:** the handoff's defensive lines and their numbered badges on the reveal. The pack doesn't carry line positions, and the plan doesn't ask for them.

## T5 — Question sheet (2026-10-08)
**Plan said:** a `QuestionSheet` for predict (S2) and review (S3) questions, built from the question payload, with `AnswerGroup`/`AnswerTile` as a radio group, `LockIn` disabled until a pick, and a `PhasePill`. Keys 1/2/3 pick and Enter locks in, only while the sheet is open. Focus goes to the question heading. The sheet slides in over 240 ms, or crossfades with reduced motion.
**We did:** as planned, with these choices:
- **Components and props:**
  - `QuestionSheet({question, onLockIn, busy?})` holds the pick itself. The page gives it `key={question.pack_id}`, so a new question starts with no pick.
  - `AnswerGroup({label, choices, selected, onSelect, disabled?, outcome?})`. `outcome` (`{correct, chosen}`) turns the tiles into the reveal's states for T6: the answer gets ✓ and "Answer", a wrong pick gets ✕, "Your pick" and a dashed border, and the others are muted. The pick can't change after that.
  - `AnswerTile` draws one option; `LockIn({selected, busy?, onLockIn})`; `PhasePill({phase, detail?})`.
- **Two layouts for the tiles,** chosen in `AnswerGroup.support.ts`. When every label is 18 characters or less ("One", "Under 8 m"), three 112 px tiles sit side by side, as in the mockups. Otherwise each option gets a full-width row, with its letter on the left. Labels such as "Pass to #14 Niels Rosinga" and "Hunted the ball straight back and won it" don't fit a third of a 390 px phone. Every option keeps its letter, so the tiles match the letters on the pitch and keys 1/2/3.
- **No separate "Earlier, at…" line when the question already gives the time.** The template Tutor's review questions open with "Play has stopped for a free kick. Back at 05:12: …", so the line would repeat it. The line appears only when the wording leaves the time out, which 2b's model might do.
- **The score shows only for live questions.** A review question's score is from when the play happened, and may be out of date by the stoppage, so its bar shows just the clock. The hyphen in the score becomes an en dash, as in the mockups.
- **Left out on purpose:**
  - "Save for the break", the close button and the "If play restarts first…" line. The selector doesn't re-queue a question, so they would promise something that doesn't happen (the plan leaves "Save for the break" out).
  - The review screen's Replay button, which needs playback.
- **Lock in stays focusable when it can't be used:** it has `aria-disabled` rather than `disabled`, and says "Pick an answer to lock in". While the answer is sent it says "Locking in…".
- **Keys:** the arrow keys, Home and End move through the options and pick, with one tab stop for the group, as native radios do. 1/2/3 and Enter are handled on the sheet's own element, never on `window`. Enter with no pick does nothing.
- **Focus** lands on the question heading (`tabIndex=-1`) without a focus ring, because the heading isn't a control.
- **Pill icons** come from the Components mockup for the three in-play phases. Half-time uses two bars and full time a flag; those two are our own.

**Checked by eye:** the predict, line-break review and counter-press review fixtures were rendered with headless Chrome at 390 px, in both themes. Two fixes came from it: the heading's focus ring is gone, and "Your pick" no longer wraps in the row layout. A counter-press review's path covers the whole spell from the loss to the regain, so its moment crop is nearly the full pitch. That is the engine's path, drawn as it is.
**Why:** the plan left these details open; the layouts and fixes came from looking at real labels.
**Affects:**
- **T6** reuses `AnswerGroup` with `outcome` for the reveal.
- **T7** gives the sheet `key={pack_id}`, turns 409 from the answer into a fresh `/next`, and passes `busy` while the answer is sent.

## T6 — Feedback (2026-10-08)
**Plan said:** a `Feedback` screen (S4, with the mix-up variant) with `VerdictMark`, `ProgressBar` and `StatTile`. It shows the verdict, the reveal path, the explanation and takeaway, stat tiles from the outcome facts, the source line ("Source · match {seed} · action {id} · worded by {source}"), the learner sentence and a bar with prior, gain and both ticks. Each state has an icon and words, not colour alone. The path draws over 600 ms, then the copy fades in; with reduced motion, a 120 ms crossfade. Focus goes to the verdict, and the copy is a polite live region.
**We did:** as planned, with these choices:
- **The common mix-up is its own field.** The template Tutor used to append "A common mix-up: “…”" to the explanation, which left the page nothing to set aside. `TutorFeedback`, `Told` and `FeedbackOut` now carry `misconception` (null after a right answer), and the explanation no longer includes it. The terminal adds the same sentence back when it prints, so `btl demo-viewer`'s output was byte-identical before the path fix below. The page shows the mix-up in quotation marks under a "Common mix-up" label with ⚠: it is a belief people hold, not a fact, and the quotes keep it from reading as one. 2b's Tutor will write the field the same way.
- **A play that changes hands now stays in one direction (a bug fix).** The match context gives each action in its own team's attacking direction, but the play's path (`picture.path` and `reveal_path`) took every action as it came. A counter-press spans both teams, so the opponent's actions were mirrored: the reveal drew a line to the pressing team's own keeper and back, and T5's review crop was nearly the whole pitch because of it. `_play_path` now turns the other team's points round into the picture's direction. A test compares the path with `seen_by` over three seeds, and fails without the fix. Line-breaking passes never change hands, so they are unchanged. Counter-press pack ids change with their paths, so the misconception chosen from the id can change: in the demo, one counter-press now gets a different one, and that is the only change in `btl demo-viewer`'s output. The README excerpt doesn't include it. The terminal draws its own path from the match, so its pictures were never affected.
- **Stat tiles.** Every outcome fact gets a tile, with the pack's display text exactly as sent. The labels and units are written in `Feedback.support.ts`: "Lines broken", "Gap" (m), "Chance added", "Chance before", "Chance after", "Won back in" (s), "Players pressing", "From goal" (m). Facts that name a player or a part of the pitch (`receiver`, `receiver_zone`, `player`) get no tile, because the explanation says them and they aren't measurements. A fact the page doesn't know still gets a tile, labelled from its name (`passes_before_regain` → "Passes before regain"). Counts show as the pack words them ("one"), not as digits.
- **The learner model's move:** "Line-breaking passes: 43% → 24%" (shares from the API, rounded as the update sentence rounds them), then the model's own update sentence, then the bar. On the bar, a fall is shown as the stretch lost, outlined in dashes, rather than a shorter bar that would hide it. The bar is a `meter` whose spoken text gives both values and both thresholds. The tick labels ("80 unlocks next", "95 mastered") come from the API's thresholds.
- **"You picked A: Pass to #14 Niels Rosinga. It was C."** The second sentence appears only after a wrong pick. The answer tiles reuse `AnswerGroup` in its reveal state, and the pitch keeps the option arrows under the drawn path.
- **Left out:** the mockup's close button, Simpler/Deeper (out of scope) and "Show me again" (needs playback). The handoff's defensive-line overlays still aren't drawn, as T4 noted.

**Checked by eye:** the three fixtures at 390 px in both themes, in headless Chrome. That's how the mirrored counter-press path showed up. Shorter tile labels came from it too: "Scoring chance change" took three lines.
**Why:** the plan left these details open; the misconception field and the path fix were needed for the reveal to be right.
**Affects:**
- **T7** shows `Feedback` after an answer, with the question that was asked, and `onContinue` fetches `/next`.
- **The fixtures** were recaptured: feedback now has `misconception`, and the counter-press fixtures have the corrected path.
- **T4's crop test** for a play from one end to the other used the counter-press fixture's mirrored path. It now uses a made-up end-to-end path, so it still checks that both goal lines show.
- **2b:** a model's feedback fills `misconception` separately.

## T7 — The loop in the browser (2026-10-09)
**Plan said:** Welcome → MatchStep → question → feedback → … → FullTime → next match, against the real API; resuming after a reload; the desktop side panel; an accessibility and reduced-motion pass; Lily plays one match by hand in both themes, at a phone width and on desktop.
**We did:** as planned, with these choices:
- **The flow is a reducer** (`App.support.ts`), tested on its own. `App.tsx` makes the requests and dispatches what comes back.
  - **Screens:** welcome, loading, step, question, feedback, full time and error.
  - **The step remembers where the last question was asked,** so it can say "The match moves on from 13:59 to 23:55". A new match starts again from kick-off.
- **`Welcome`** asks for a name and lower-cases it as it is typed. It leaves the rule itself to the API: a refused name shows FastAPI's own message beside the field, with the name kept. Once the record is found, it shows "Match 1 of 3: Home v Away", each concept's bar, and "Watch match 1".
- **Coming back.** The name is remembered in `localStorage` (`btl.viewer`, every access guarded). On load, a remembered viewer goes straight to `/next`, so a reload returns to the waiting question. "Not lily?" in the header forgets the name. If the server no longer has the record (404), the page forgets it and asks for a name.
- **`MatchStep`** takes a span of match time (`from` clock → `to`, the question's `delivered`) plus the clubs and `onArrive`, not a question, so a playback component can take its place later.
  - It shows Match N, the clubs and the clock, then the phase pill and a heading such as "Play has stopped for a free kick at 23:55" or "Settled possession at 03:35".
  - Then why the question comes now ("A question about the play at 11:42, saved until play stopped").
  - Then "See the question", or "Make your read" for a live question.

  Every phrase is built from payload fields. The score shows only for a live question, as in T5.
- **`FullTime`** shows the score, the number of questions, and each concept from kick-off to now as a bar. "On to match N" takes the viewer to the next match's first question, since `/next` has already moved them on (T2). After the last match, "See where you stand" shows the finished status.
- **Errors.** A 409 on an answer fetches `/next` again, without asking the viewer. Any other failure shows `ErrorPanel` with the reason and "Try again", which repeats exactly the request that failed: start, next, status or the answer.
- **The desktop side panel.** From 900 px, the companion is a 420 px (`--panel-w`) panel on the right, scrolling on its own. Beside it, on `--bg-deep`, a dashed area stands for the viewer's stream, with the match and clock above it, as in `D-Live`. That area is `aria-hidden`, because the panel says everything in it. The question screen shows the keys (1 2 3, Enter) at desktop width only.
- **Shared styles** in `base.css`: `.primary-button`, `.text-button`, `.visually-hidden`, and `.screen-heading`, which lets a heading take focus without a ring.
- **Accessibility:**
  - Each screen's heading takes focus when it opens.
  - Loading is a `role="status"` region; an error is `role="alert"`.
  - The panel is the page's `main` landmark, under the `h1` brand.
  - The step's entrance slides 8 px over 240 ms, or crossfades in 120 ms with reduced motion.
- **Tests:**
  - the reducer;
  - each new screen;
  - an App test against a fake server: name → question by keyboard → feedback → full time, plus resuming, a 409, a refused name, a failure and retry, a missing record, and changing name.

  jsdom has no media queries, so the side panel's layout was checked in the browser rather than in a test.

**End to end** (`btl serve` with a temporary learners folder, Chrome driven by puppeteer-core from outside the repo, by keyboard only):
- One whole match: five questions answered, all review questions at dead balls; the last was asked at full time.
- A reload before the second question came back to the same question.
- No question response held `correct`, `correct_key`, `outcome`, `reveal_path`, `explanation` or `chosen`, and no console errors.
- A live question (viewer seed 2, at 03:35) went through the same steps with "Make your read".
- Screenshots of every screen at 390 px and 1440 px in both themes led to one fix: the clock on the step no longer wraps under a long fixture.
- The test learner records were deleted.

**Why:** the plan left these details open.
**Affects:**
- **Lily's hand check** (one match by hand in both themes, at a phone width and on desktop) is still to do.
- **T8:** the README's "Try the web page" section can use `npm run build` then `uv run btl serve`, and screenshots like these.
- **Later playback:** `MatchPlayback` takes `MatchStep`'s props.

## Fixes after Lily's check (2026-10-09)
**Plan said:** nothing. These came from T7's screenshots, after Lily's hand check.
**We did:**
- **The score is written with an en dash ("1–0") in the evidence pack,** so every view shows it the same way. The page no longer swaps the hyphen itself. In JetBrains Mono an en dash fills its character cell, so on screen it looks close to a hyphen.
- **Shirt numbers stay readable on the pitch:**
  - the ball sits just outside the carrier's disc, 2.1 m right and up instead of 1.1 m, and no longer covers the second digit;
  - the path and the option lines start at the ball as drawn, not at the carrier's centre;
  - home discs are drawn over away rings.

  A screenshot had shown the carrier as "13" when the question named "#16": the data was right, and the ball and the path covered the "6".

**Why:** a number the viewer can't read sends them to the wrong player.
**Affects:** the handoff puts the ball about 1.5 m from the carrier; it is now about 3 m. Pack ids change, because the score's text changed.
