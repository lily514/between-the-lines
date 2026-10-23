# CLAUDE.md — Between the Lines

## Git workflow
- GitHub remote, no PRs. One branch per milestone, named after the milestone (M1 "The Data Engine": `feature/data-engine`;
  M2a "The loop in the terminal": `feature/learning-loop`; M2c "The web page": `feature/web-page`;
  M2d "The basics": `feature/the-basics`; M2e "Getting started": `feature/getting-started`;
  M2b "The AI Tutor": `feature/ai-tutor`; M3 "Deploy it properly": `feature/deploy`; M4 "Match day":
  `feature/match-day`). 2c, 2d and then 2e were built before 2b, while Azure wasn't set up yet.
- Each plan task is one commit on the milestone branch, made after Lily reviews the diff.
- When a milestone is done, merge it into main with `git merge --no-ff`, so each milestone shows up as one merge in the graph.
- Claude commits locally only; Lily pushes when ready. CI runs on every push, to any branch.

## What this is
Adaptive football-learning tool on synthetic match data. Milestone 1 built the data engine; Milestone 2
is split into 2a (the learning engine, played in the terminal), 2b (the Foundry Tutor and Verifier),
2c (the web page), 2d (the basics) and 2e (getting started).
Milestone 2c puts the learning loop in a browser: a React page over a small FastAPI layer.
Milestone 2d adds the basics: restarts, offside, and fouls and cards.
Milestone 2e adds getting started: picking a team to support, and a team sheet before each match
that grows with the viewer.
Milestone 2b adds the AI Tutor: model-worded questions and feedback, checked by the Verifier, in the
terminal and on the page.
Milestone 3 deploys the page and API: one `azd up` builds the container and creates every Azure
resource from Bicep, serving a public demo URL, with managed identity and no secrets.
Milestone 4 gives the page a home base: a Matches screen, the curriculum map from any screen,
halftime and full-time scouting reports, and preferences. Matches still step from moment to moment.

## Learning design rules
- The match never depends on the viewer. Adaptation lives in which moments we ask about, when, and
  how. Candidate moments come from the detectors, never from `match.planted`, so the loop would work
  unchanged on real data.
- Never prompt during a transition. Delivery is decided by phase of play, computed from match events
  only (`concepts/phase.py`). Deferred questions are review questions, never predict.
  A question about a restart or a foul is asked at its own stoppage or not at all; these are the
  only live questions asked in a dead ball. One question per stoppage: the live one wins and a saved
  review waits. No live question in the last 30 s of a half; it becomes a report replay.
- Reports and the curriculum map are built on the server from the attempt log; level words
  (Getting there, Solid, Sharp, Mastered) come from the API, never from the browser.
- The viewer's team chooses which matches they watch and how they are shown, never which moments
  are asked about. The team sheet uses only matches the viewer has finished.
- The curriculum is `btl/learn/concept_map.yaml`; only `learn/concept_map.py` reads it.
- The learner model sits behind the `KnowledgeModel` protocol. The attempt log is the source of truth;
  a model's state is derived from it. Only the session chooses which model to use.
- Every number shown to the viewer comes from the evidence pack, through a fact slot such as
  `{B.threat_added}`. `tutor/` never imports sim, value, concepts or plant.
- `learn/` takes time as a parameter and never reads the clock.
- The browser computes no football and invents no numbers: everything it shows comes from the API.
  Question payloads are built from the question view only, so the right answer never leaves the
  server before the viewer answers.
- Model text reaches the viewer only through the Verifier; on any failure the template is used.
  Question prompts are built from the question view only. No viewer id, name or club goes in a prompt.
  A question is worded once: replays reuse the words the viewer saw.
- Each visitor's viewer id is a random id made by the browser; there is no sign-in. Limits on model
  calls fall back to the template, as any other model failure does.

## Hard rules
- All data synthetic: fictional league/clubs/players only. No real league, club, or player names or marks.
- No betting framing (no odds, stakes, "tips", wagers) in code, data, docs, or CLI output.
- Python 3.11 exactly (socceraction supports 3.9–3.11).
- All code is new, written during the hackathon. Libraries are fine; copied code is not.
- Every setup step goes in docs/setup.md in the same commit that needs it.

## Azure and deployment
- `azure.yaml`, `Dockerfile` and `.dockerignore` sit at the repo root; Bicep lives in `infra/` (`main.bicep` at
  subscription scope, one hand-written module per concern in `infra/modules/`). No Azure Verified Modules.
- Bicep is the source of truth for the deployed app's configuration. The app reads environment variables only
  in `cli/` (`BTL_*`, plus `AZURE_CLIENT_ID`), as fallbacks for `btl serve`'s options.
- The app runs as one replica: the prepared-match cache, the wording cache and the model-call limits live in
  memory and rely on it.
- Managed identity for everything: pulling images, calling the model, reading and writing blobs. No secrets,
  keys or connection strings anywhere: not in the repo, not in files, not in app settings. The one exception
  is Azurite's published key, read from `BTL_AZURITE_KEY` by opt-in tests only, never committed.
- Lily's real values (subscription, tenant, Foundry endpoint, alert email) live in the azd environment
  (`.azure/`, gitignored) or her shell. The repo uses placeholders.
- Everything comes from code except two documented `az` commands: the demo model deployment on Lily's
  existing Foundry resource, and the app's role on it (`docs/deployment.md`).
- Everything stays within the subscription's $150 monthly credit. The spending limit stays on; the budgets
  and the daily model-call cap stay in place.
- **Command safety rules:**
  - Ask before running any command that creates, changes or deletes Azure resources or could cost money,
    including `azd up`, `azd provision`, `azd deploy`, `azd down`, `az … create/update/delete`, role
    assignments and `docker push`.
  - Preview infrastructure changes first (`azd provision --preview`) and summarise what will change.
  - Never write secrets, keys or connection strings into files, the repo or app settings.
  - Name the subscription in every `az` command (`--subscription`), since Lily's login defaults to another tenant.

## Docs
- `docs/milestone-N/` holds what was written for that milestone: `plan.md` plus write-ups. Split
  milestones get their own folder (`docs/milestone-2a/`).
- `docs/` root holds living references that every milestone updates (setup, event schema, concept map,
  deployment).
- Name documents in full words, never abbreviations (`expected-threat.md`, not `xt.md`).
- `plan.md` is frozen once committed. Divergences go in `docs/milestone-N/implementation-notes.md`.
- Whenever implementation differs from the plan, or something surprising is learned, add a note
  **in the same commit** and point it out when presenting the diff. Note format:
      ## T<N> — <task name> (<YYYY-MM-DD>)
      **Plan said:** …   **We did:** …   **Why:** …   **Affects:** later tasks, or "nothing"
- At milestone end, add a short summary at the top: the biggest changes, what was cut, and what carries over.

## Commands (run from backend/)
- Install: `uv sync`
- Test: `uv run pytest` (fast) · `uv run pytest -m slow` (batch xT fit)
- Lint/format: `uv run ruff check --fix && uv run ruff format`
- Types: `uv run pyright`
- CLI: `uv run btl --help` · learning loop: `uv run btl learn --viewer NAME`, `uv run btl demo-viewer`
- Web page: `uv run btl serve` (serves the API and the built page)
- AI Tutor: add `--tutor foundry` to `btl learn`, `btl demo-viewer` or `btl serve` · `uv run btl tutor-ping` ·
  `uv run btl tutor-eval`
- Opt-in tests: `uv run pytest -m blob` (needs Azurite in Docker and `BTL_AZURITE_KEY`) ·
  `uv run pytest -m container` (builds and runs the image in Docker)

## Commands (run from the repo root; each needs Lily's go-ahead except the preview)
- `azd provision --preview` · `azd up` · `azd deploy` · `azd down --purge`

## Commands (run from frontend/)
- Install: `npm ci` (Node 24, see `.nvmrc`)
- Dev server: `npm run dev` (proxies `/api` to `btl serve`)
- Test, lint, build: `npm test` · `npm run lint` · `npm run build`
- API types: `npm run api-types` (regenerate after any change to the API)

## Layout
Monorepo layout: Python lives in `backend/` (src layout: `backend/src/btl/`, tests in
`backend/tests/` mirroring package paths). `frontend/` holds the web page (Vite + React + TS).
One concept per module. Subpackages: schema, league, sim, plant, value, concepts, learn, tutor, store,
cli, api, plus `replay.py`. `api` holds the HTTP routes the page calls; the page itself is `frontend/`.

## Python style
- ruff format (line length 100); ruff rules: E, F, I, B, UP, SIM, RUF, N, D (Google convention).
- pyright in strict mode over src and tests. No bare `Any`; if unavoidable, comment why.
- Domain objects: `@dataclass(frozen=True, slots=True)`. Vocabularies: `enum.IntEnum`/`StrEnum`.
- IDs are `NewType`s (GameId, TeamId, PlayerId, ActionId) — never raw ints in signatures.
- Python 3.11 syntax only: no `type X = ...` aliases or `def f[T]()` generics (ruff `target-version = "py311"`).
- Randomness: always an explicit `numpy.random.Generator` parameter. Never the global `random`/`np.random`.
  Same seed ⇒ identical output, always. Each concern (league, engine, shape, planter) gets its own
  stream spawned from the match seed via `SeedSequence.spawn`, so one part never shifts another.
- Units: metres and seconds. Pitch is 105 × 68 (SPADL). Coordinate convention is documented in
  `btl/schema/__init__.py`; do not invent another one. Direction flipping happens only in `frames.py`.
- pandas only in `schema/frames.py`, `io.py` (parquet files), `value/`, and `cli/`. Everything else uses typed dataclasses.
  pandas and socceraction are only partly typed, so only those edge modules may start with `# pyright: basic`; nowhere else.
- Pure functions where possible; I/O only in `btl/io.py`, `btl/store/`, `btl/cli/`, `btl/api/` and `btl/tutor/azure.py`.
  Only `btl/tutor/azure.py` and `btl/store/blob.py` import an Azure SDK.

## Naming
- Modules/functions: snake_case; functions are verbs (`simulate_match`), data types are nouns (`Snapshot`).
- Constants: UPPER_SNAKE in the module that owns them. Tunable sim parameters live in `sim/params.py`.
- Tests: `test_<behaviour_in_plain_words>`.

## Docstrings & comments
- Every module has a one-paragraph docstring saying what it is for.
- Public functions/classes: Google-style docstring (Args/Returns/Raises only when not obvious from types).
- Private helpers: no docstring unless the logic is non-obvious.
- Comments explain *why*, not *what*. Football definitions (e.g. what counts as "line-breaking")
  are written once, in the detector's docstring, with the thresholds named as constants.

## Testing
- pytest + hypothesis. Each commit adds tests for what it adds.
- Hand-built mini matches in `tests/fixtures/` for detector and schema tests (readable, < 15 events).
- Property tests for invariants (coords in bounds, time monotonic, SPADL schema valid).
- Simulator realism is tested with *bands* over many seeds, never exact numbers.
- No network, no files outside tmp_path. Model calls use `FakeClient` or `ReplayClient`. Slow tests marked `@pytest.mark.slow`.
- Tests that need Docker are opt-in: `@pytest.mark.blob` (Azurite on localhost) and `@pytest.mark.container`.
  The default run stays offline and fast, and needs neither Docker nor Azure.

## Commits
- Short imperative subject line, no prefixes: `Add possession-chain simulator`, `Plant line-breaking moments`.
- Add a body only when the *why* isn't obvious from the diff.
- One plan task = one commit, tests included.

## Frontend style
- Follows the workspace CLAUDE.md (tabs, no semicolons, single quotes, one component per `.tsx`,
  helpers in `.support.ts`).
- Component CSS uses the tokens in `src/styles/tokens.css` only, never a hex value.
- Components are grouped in folders, as in `../Web/orbit-web`: one folder per screen under `src/components/`
  (its main component is `index.tsx`, with `index.css`, `index.support.ts` and tests beside it), and pieces
  used by more than one screen go in `src/components/Shared/`. `App.tsx` sits at the top of `components/`.
- Design reference: `docs/milestone-2c/design/`, plus `docs/milestone-2e/design/` and `crests/` for the picker, team
  sheet and crests, and `docs/milestone-4/design/` for Matches, the map, reports and preferences. It guides the
  look; the repo decides behaviour and data.
