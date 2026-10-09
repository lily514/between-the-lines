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
