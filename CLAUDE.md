# CLAUDE.md — Between the Lines

## Git workflow
- GitHub remote, no PRs. One branch per milestone, named after the milestone (M1 "The Data Engine": `feature/data-engine`;
  M2a "The loop in the terminal": `feature/learning-loop`; M2c "The web page": `feature/web-page`;
  M2d "The basics": `feature/the-basics`). 2c and then 2d are built before 2b, because Azure isn't set up yet.
- Each plan task is one commit on the milestone branch, made after Lily reviews the diff.
- When a milestone is done, merge it into main with `git merge --no-ff`, so each milestone shows up as one merge in the graph.
- Claude commits locally only; Lily pushes when ready. CI runs on every push, to any branch.

## What this is
Adaptive football-learning tool on synthetic match data. Milestone 1 built the data engine; Milestone 2
is split into 2a (the learning engine, played in the terminal), 2b (the Foundry Tutor and Verifier),
2c (the web page) and 2d (the basics).
Milestone 2c puts the learning loop in a browser: a React page over a small FastAPI layer.
Milestone 2d adds the basics: restarts, offside, and fouls and cards.

## Learning design rules
- The match never depends on the viewer. Adaptation lives in which moments we ask about, when, and
  how. Candidate moments come from the detectors, never from `match.planted`, so the loop would work
  unchanged on real data.
- Never prompt during a transition. Delivery is decided by phase of play, computed from match events
  only (`concepts/phase.py`). Deferred questions are review questions, never predict.
  A question about a restart or a foul is asked at its own stoppage or not at all; these are the
  only live questions asked in a dead ball.
- The curriculum is `btl/learn/concept_map.yaml`; only `learn/concept_map.py` reads it.
- The learner model sits behind the `KnowledgeModel` protocol. The attempt log is the source of truth;
  a model's state is derived from it. Only the session chooses which model to use.
- Every number shown to the viewer comes from the evidence pack, through a fact slot such as
  `{B.threat_added}`. `tutor/` never imports sim, value, concepts or plant.
- `learn/` takes time as a parameter and never reads the clock.
- The browser computes no football and invents no numbers: everything it shows comes from the API.
  Question payloads are built from the question view only, so the right answer never leaves the
  server before the viewer answers.

## Hard rules
- All data synthetic: fictional league/clubs/players only. No real league, club, or player names or marks.
- No betting framing (no odds, stakes, "tips", wagers) in code, data, docs, or CLI output.
- Python 3.11 exactly (socceraction supports 3.9–3.11).
- All code is new, written during the hackathon. Libraries are fine; copied code is not.
- Every setup step goes in docs/setup.md in the same commit that needs it.

## Docs
- `docs/milestone-N/` holds what was written for that milestone: `plan.md` plus write-ups. Split
  milestones get their own folder (`docs/milestone-2a/`).
- `docs/` root holds living references that every milestone updates (setup, event schema, concept map).
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
- Pure functions where possible; I/O only in `btl/io.py`, `btl/store/`, `btl/cli/` and `btl/api/`.

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
- No network, no files outside tmp_path. Slow tests marked `@pytest.mark.slow`.

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
- Design reference: `docs/milestone-2c/design/`. It guides the look; the repo decides behaviour and data.
