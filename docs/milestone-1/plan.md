# Milestone 1 Plan: The Data Engine

> **Between the Lines** (repo `between-the-lines`, package and CLI `btl`).
> Agreed 2026-10-06. This plan is frozen; where implementation diverges, see [implementation-notes.md](implementation-notes.md).

## Context

This is a solo project for the "Inside the Game" hackathon (closes 2026-10-27, which leaves about 3 weeks). It is an adaptive football-learning tool that pauses synthetic matches at "teachable moments". Milestone 1 builds only the **data engine**: a SPADL-compatible event schema with position snapshots, a simple match simulator that can plant teachable moments on request, xT valuation via socceraction, 3–4 concept detectors, tests, and a CLI for inspection. There is no UI, Azure, LLM, or learner model yet.

The goals are learning, a clean portfolio repo, and fun. So the plan favours **small showable steps** and **explicit timeboxes** over realism.

Starting point:
- An empty GitHub repo.
- `uv` not yet installed; a local Python 3.11 is available.
- Python 3.11 is required because socceraction only supports 3.9–3.11. The project CLAUDE.md states this explicitly, since the wider workspace defaults to 3.12+.

---

## What it looks like

All names and numbers below are invented for illustration.

**Input**: a command:
```
btl simulate --seed 7 --plant line_breaking_pass:1,2,3
```
- `--seed 7` makes the match repeatable: the same seed always gives the same match.
- `--plant` (optional) asks for teachable moments, here three line-breaking passes, easy → medium → hard.
- Optionally, which two fictional clubs play.

A one-off step, `btl fit-xt --matches 200`, simulates 200 matches and learns the Expected Threat grid from them.

**Output 1: the event list.** About 1,500 ball actions per match, in order:
```
  #   time   team          player            action    result   from → to          threat   tags
412  23:41  Harrowgate FC  #4 Odell Brask    pass      success  (38,30) → (52,22)  +0.004
413  23:43  Harrowgate FC  #8 Teo Malvern    dribble   success  (52,22) → (58,25)  +0.006
414  23:45  Harrowgate FC  #8 Teo Malvern    pass      success  (58,25) → (79,31)  +0.041   line-breaking
415  23:47  Harrowgate FC  #9 Ilan Corve     shot      fail     (79,31) → (105,33)
```
Positions are in metres on a 105 × 68 pitch. "Dribble" here just means carrying the ball. This table is SPADL: we hand it to socceraction, and socceraction fills in the threat column.

**Output 2: snapshots.** Where all 22 players stood at any event. M1 draws them as rough text; the later UI draws the real pitch from the same data.
```
 |  A        a           a       |     A = Harrowgate (attacking →)
 |      A         a  a           |     a = Wexmoor (defending)
 |  A      (8)•  a      a     A  |     • = ball, (8) = Teo Malvern
 |      A         a  a           |
 |  A        a           a       |
```

**Output 3: concept tags.** Our detectors label events with football ideas (line-breaking pass, pressing, switch of play, counter-attack).

**Output 4: planted moments.** The raw material for the future quiz, e.g. *"Moment 2 (medium): pause at #413 as Malvern receives. Answer: #414, a pass through the gap between two midfielders."* Nobody is quizzed in M1.

```
seed + plant request ──► simulator ──► events + snapshots
                                            │
                     socceraction (threat) ─┤
                     concept detectors ─────┤
                                            ▼
                     btl inspect: table + tags + planted moments
```

## Glossary
- **SPADL**: a standard table format for football events (one row per action: who, what type, where it started and ended, success or fail). It comes from the socceraction library.
- **xT (Expected Threat)**: a pitch grid where each cell holds the probability that having the ball there leads to a goal soon. An action's value is xT(end cell) − xT(start cell). The grid is learned by counting moves, shots, and goals in match data.
- **Snapshot**: the frozen positions of all players at one event, used to draw the pitch when a match pauses.

## 1. Draft CLAUDE.md

This is the draft as proposed during planning. The committed `CLAUDE.md` at the repo root is authoritative.

```markdown
# CLAUDE.md — Between the Lines  (DRAFT — not yet agreed)

Overrides ../CLAUDE.md where they conflict (notably: Python 3.11 instead of 3.12+).

## Git workflow
- GitHub remote, no PRs. One branch per milestone, named after the milestone (M1 "The Data Engine": `feature/data-engine`).
- Each plan task is one commit on the milestone branch, made after Lily reviews the diff.
- When a milestone is done, merge it into main with `git merge --no-ff`, so each milestone shows up as one merge in the graph.
- Claude commits locally only; Lily pushes when ready. CI runs on every push, to any branch.

## What this is
Adaptive football-learning tool on synthetic match data. Milestone 1 = data engine only.

## Hard rules
- All data synthetic: fictional league/clubs/players only. No real league, club, or player names or marks.
- No betting framing (no odds, stakes, "tips", wagers) in code, data, docs, or CLI output.
- Python 3.11 exactly (socceraction supports 3.9–3.11).
- All code is new, written during the hackathon. Libraries are fine; copied code is not.
- Every setup step goes in docs/setup.md in the same commit that needs it.

## Docs
- `docs/milestone-N/` holds what was written for that milestone: `plan.md` plus write-ups.
- `docs/` root holds living references that every milestone updates (setup, event schema).
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
- CLI: `uv run btl --help`

## Layout
Monorepo layout: Python lives in `backend/` (src layout: `backend/src/btl/`, tests in
`backend/tests/` mirroring package paths). `frontend/` arrives in a later milestone.
One concept per module. Subpackages: schema, league, sim, value, concepts, cli.

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
- pandas only in `schema/frames.py`, `value/`, and `cli/`. Everything else uses typed dataclasses.
  socceraction has no type hints, so only those edge modules may start with `# pyright: basic`; nowhere else.
- Pure functions where possible; I/O only in `btl/io.py` and `btl/cli/`.

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
```

**Reasoning behind the less obvious choices:**
- **NewType IDs.** They let pyright catch a `player_id` passed where a `team_id` belongs. That bug is easy to write in event code, and the type hint makes the signature document itself.
- **Explicit RNG, split into streams.** Determinism is the backbone of testing a simulator. If seed 42 always gives the same match, any test failure can be replayed exactly. Separate streams mean planting a moment doesn't reshuffle the rest of the match.
- **Bands, not exact numbers.** Exact-value tests on a stochastic sim break with every tuning tweak, and band tests double as the definition of "believable enough". They are our stopping rule against the sim becoming a time sink.
- **Docstring vs comment policy.** You want "well documented", and the workspace house rule is "comment only what isn't obvious". Module and public docstrings plus sparse why-comments satisfy both.

---

## 2. Package & folder structure

**Decided:** follow the workspace monorepo layout from day one. The Python package lives under `backend/`, and `frontend/` arrives in a later milestone without moving any files.

```
between-the-lines/
├── README.md                 # pitch, quickstart, demo commands
├── CLAUDE.md
├── LICENSE
├── .github/workflows/ci.yml  # ruff + pyright + pytest on push to any branch (working-directory: backend)
├── backend/
│   ├── pyproject.toml        # uv-managed project, tool config (ruff, pyright, pytest)
│   ├── uv.lock
│   ├── .python-version       # 3.11
│   ├── src/btl/              # (tree below)
│   └── tests/
├── docs/
│   ├── setup.md              # living: every setup step, in order (feeds the future devcontainer)
│   ├── event-schema.md       # living: schema + SPADL mapping + coordinate convention
│   └── milestone-1/
│       ├── plan.md           # this plan, frozen once committed
│       ├── implementation-notes.md  # where and why implementation diverged from the plan
│       └── expected-threat.md  # what xT is, how we fit it, and the synthetic-data caveat
backend/src/btl/
│   ├── __init__.py
│   ├── schema/
│   │   ├── __init__.py       # coordinate convention docstring; public re-exports
│   │   ├── ids.py            # GameId, TeamId, PlayerId, ActionId NewTypes
│   │   ├── vocab.py          # ActionType / Result / BodyPart enums mirroring SPADL config; ConceptId
│   │   ├── event.py          # Event dataclass (one SPADL action + our extension fields)
│   │   ├── snapshot.py       # PlayerPosition, Snapshot (readable view of one moment's positions)
│   │   ├── match.py          # Match container: meta, teams, events, position array, planted moments
│   │   ├── possession.py     # derive possessions from SPADL events (shared definition of "who has the ball")
│   │   └── frames.py         # Match <-> pandas, validation, and the only place directions are flipped
│   ├── league/
│   │   ├── names.py          # fictional name generator (syllable-based) + real-name denylist check
│   │   └── league.py         # League, Club, Player, squad generation, fixtures
│   ├── sim/
│   │   ├── pitch.py          # pitch geometry, zones, distance/angle helpers
│   │   ├── shape.py          # formation templates -> 22 player positions for a ball location
│   │   ├── params.py         # all tunable probabilities/durations in one frozen dataclass
│   │   ├── chain.py          # one possession chain: sample actions until turnover/stoppage
│   │   ├── engine.py         # simulate_match(): kickoff -> periods -> events; assigns event numbers
│   │   └── stats.py          # summary stats (passes, completion, shots, goals) for band tests
│   ├── plant/
│   │   ├── spec.py           # MomentSpec / PlantRequest: declarative "what to plant"
│   │   ├── templates.py      # one scripted-sequence builder per concept, parameterised by difficulty
│   │   └── planter.py        # schedules specs into match time; the engine calls templates when due
│   ├── value/
│   │   └── xt.py             # fit/save/load/rate wrappers around socceraction.xthreat
│   ├── concepts/
│   │   ├── base.py           # ConceptTag, MatchContext (direction-normalised), Detector protocol
│   │   ├── registry.py       # explicit ALL_DETECTORS tuple
│   │   ├── switch_of_play.py
│   │   ├── line_breaking.py
│   │   ├── pressing.py
│   │   └── counter_attack.py # 4th detector (cuttable)
│   ├── io.py                 # save/load a Match as a directory of parquet + meta.json
│   └── cli/
│       ├── app.py            # typer app: simulate, events, fit-xt, tags, moments
│       └── render.py         # rich tables + ASCII pitch for a snapshot
backend/tests/                # mirrors src/btl/…, plus fixtures/
```

**Why this shape:**
- **src layout.** Tests run against the *installed* package, which catches packaging mistakes early. It is the modern default and looks right in a portfolio.
- **`plant/` is separate from `sim/`.** Planting is the product-specific idea; the sim is generic. Keeping them apart means the sim stays simple and the planter is easy to read on its own.
- **`concepts/` depends only on `schema/` and `value/`, never on `sim/` or `plant/`.** Detectors must work on any SPADL-plus-snapshot data, which keeps them honest (more on this under the risks).
- Run every command from `backend/`, as the workspace conventions require.

---

## 3. Key design decisions

### 3.1 Project tooling
| Option | Pros | Cons |
|---|---|---|
| **uv** ✅ | One fast tool for Python version, venv, lockfile, and running; the rest of the workspace already uses it; the devcontainer story is trivial | New to install (not on this machine) |
| pip-tools + venv | Very transparent, minimal magic | Several tools to juggle; no Python version management; slower |
| Poetry | Mature, popular | Slower, its own resolver quirks, and nothing your other projects use |

**Recommendation: uv**, plus ruff, pyright (strict), pytest, and hypothesis. Use `uv python pin 3.11` so the project doesn't depend on pyenv being present (simpler for the future Codespace). Setup steps: `brew install uv`, `uv python install 3.11`, then `uv sync`.

### 3.2 Data models
| Option | Pros | Cons |
|---|---|---|
| **Frozen dataclasses for the domain + pandas at the socceraction boundary** ✅ | Zero-dependency, fast in the sim's hot loop, reads cleanly, type-checker-friendly; socceraction already validates DataFrames with its own pandera `SPADLSchema` | Hand-written conversion code (small); no free JSON serialization |
| Pydantic v2 everywhere | Validation and JSON for free; will be handy when an API appears in M2+ | Validation cost on ~300k events per xT batch; duplicates socceraction's validation; tempts us to put logic in models |
| pandas-first (DataFrames everywhere) | Native to socceraction; vectorised | Weak typing (bad for a "typed Python" portfolio), harder to read in the sim loop, column-name typos fail at runtime |

**Recommendation: dataclasses in the sim and domain, with DataFrames as the analytics view.** `frames.py` is the single place that converts between them. When an API arrives later, pydantic can wrap *responses* at that boundary without changing the core.

### 3.3 How the simulator generates play
| Option | Pros | Cons |
|---|---|---|
| **Possession-chain Markov model over pitch zones** ✅ | Simple and fast; naturally produces SPADL-shaped sequences; each probability is a readable, tunable number | Players don't "really" exist between events; positions must be inferred |
| Agent-based (22 agents, decisions, movement) | Realistic positions and emergent tactics | A physics/AI engine, i.e. the classic time sink, and it would be continuous tracking (explicitly out of scope) |
| Template stitching (hand-written possession patterns glued together) | Very controllable | Repetitive and visibly fake; lots of authoring |

**Recommendation: Markov possession chains, plus a formation "shape model" for positions.**
- The state is (team in possession, ball zone, game phase). In each step the engine samples the action type given the zone (pass/cross/dribble/shot/clearance), the end location from a per-type kernel biased toward goal, and success from a base rate × a distance penalty × a team-strength modifier. A failure produces the opponent's defensive event (interception/tackle) and flips possession. A ball leaving the pitch produces a throw-in, goal kick, or corner. Shots convert with a simple distance/angle probability.
- Actor choice: pick a player whose formation role fits the zone.
- **Snapshots without tracking:** `shape.py` computes all 22 positions as a deterministic function of (formation, ball position, team in possession) plus seeded jitter. The block shifts with the ball, and the defending side is more compact. It's cheap (22 points), so **the sim emits a snapshot for every event**. That lets snapshot-based detectors (line-breaking) run on natural play too, not only on planted moments. The *schema* still treats snapshots as optional per action.
- **Positions are stored as one numpy array per match** (events × 22 × 2), not as 33k small objects. `Snapshot` is a readable view built on request for one moment. Batch runs for threat fitting pass `with_snapshots=False`; 200 matches × 33k objects would be slow and memory-hungry for data that step never reads.

### 3.4 Specifying and planting teachable moments
Specification: declarative and data-only.
```python
PlantRequest(moments=(
    MomentSpec(concept=ConceptId.LINE_BREAKING_PASS, difficulty=1),
    MomentSpec(concept=ConceptId.LINE_BREAKING_PASS, difficulty=2),
    MomentSpec(concept=ConceptId.LINE_BREAKING_PASS, difficulty=3),
), ordering="increasing_difficulty")
# CLI: btl simulate --seed 7 --plant line_breaking_pass:1,2,3
```

| Planting option | Pros | Cons |
|---|---|---|
| Rejection sampling (simulate and keep matches where the moment occurs naturally) | No special code paths | Unreliable for rare moments; can't control difficulty or timing |
| Bias the Markov probabilities around a target time | Stays "natural" | Indirect; hard to guarantee the exact geometry a question needs |
| **Scripted injection** ✅ | Guaranteed, timed, difficulty-controlled; the snapshot is crafted for the question | Needs one template per concept; splices must look seamless |

**Recommendation: scripted injection, during generation only.** Nothing is spliced into a finished match, because that would renumber events and break references like "pause at #413". The planter picks target minutes, spread out and ordered by difficulty. When play reaches one, the engine hands control to the concept's template, which writes a short sequence (build-up, *pause action*, *answer action*) and its snapshot, then resumes normal play from the resulting state. Difficulty is geometric, e.g. for line-breaking: 1 = wide gap and only one forward option; 2 = narrower gap; 3 = narrow gap plus an attractive safe sideways option as a decoy. Each planted moment records `PlantedMoment(spec, pause_action_id, answer_action_id, snapshot_action_id)`. That record is the future question/answer key.

**Key test:** every planted moment must be **found independently by the detector** with the same ordering of difficulty. This one test validates both sides, and it's why detectors may not import from `plant/`.

### 3.5 Detector structure

**How detectors relate to socceraction.** socceraction does not label football concepts. In this project it only defines the event format (SPADL) and computes threat (xT). The detectors are our own code in `btl/concepts/`. They read the same SPADL event table plus the snapshots, and write a **separate tags table** keyed by event number. The SPADL table stays pure, and `btl inspect` joins the two for display.

```
event table (SPADL) ──┬──► socceraction ──► threat values ──┐
                      │                                     ├──► btl inspect joins them by event #
snapshots ────────────┴──► our detectors ──► tags table ────┘
```

| Option | Pros | Cons |
|---|---|---|
| Plain functions in a dict | Minimal | Thresholds become magic numbers or kwargs soup |
| **Protocol + small frozen-dataclass detectors + explicit registry tuple** ✅ | Thresholds are named, typed fields; each detector is one file plus one test file; adding a concept = add a file + one line in `ALL_DETECTORS` | Slightly more ceremony |
| Config/rule DSL | Non-coders could add rules | Massive overkill for 4 concepts |

```python
class Detector(Protocol):
    concept: ConceptId
    needs_snapshots: bool
    def detect(self, ctx: MatchContext) -> list[ConceptTag]: ...

@dataclass(frozen=True, slots=True)
class ConceptTag:
    concept: ConceptId
    game_id: GameId
    action_id: ActionId          # the key action
    span: tuple[ActionId, ActionId]
    difficulty: float | None     # 0–1, detector-defined
    evidence: Mapping[str, float]  # e.g. {"lines_broken": 2, "gap_width_m": 3.1}; read-only by convention
```
`MatchContext` bundles the SPADL frame (with names), the snapshot lookup, possessions from `schema/possession.py`, and optional xT values. **Everything in it is already normalised so the team on the ball attacks left → right**, so no detector flips coordinates itself. Detectors never touch raw `Match` internals and never trust the simulator's own `possession_id`, so they would also work on non-simulated data.

Proposed definitions. Each one is written into its detector's docstring; the thresholds are starting values to tune.

| Concept | What it means in football | The rule | Needs snapshots? |
|---|---|---|---|
| **Switch of play** (built first, to prove the framework) | Moving the ball quickly to the other side of the pitch, where the defence is thin | A successful pass or cross that travels ≥ 30 m across the pitch and ends on the opposite flank | No |
| **Line-breaking pass** | Defenders stand in rough lines (defence, midfield); a pass *through* a line skips those players | Cluster the opposition's outfield players into lines by x. A successful pass that starts behind a line of ≥ 3 players and ends beyond it breaks that line. Difficulty comes from the gap width at the crossing point and the number of lines broken | **Yes** |
| **Pressing (counter-press)** | After losing the ball, a team hunts it straight back instead of retreating | The team regains possession within 5 s of losing it, in the opponent's half | No |
| **Counter-attack** (cuttable) | Winning the ball and attacking fast before the opponent reorganises | A possession won in your own half reaches the opposition box within 12 s. It pairs with pressing: pressing wins the ball, the counter exploits it | No |

**Rule for detectors:** a detector never imports from `plant/`. It must find planted moments from its football rule alone, so the planted-means-detected test in 3.4 really checks both sides.

### 3.6 Other smaller decisions (recommendations only)
- **CLI: typer + rich.** Typer gives typed commands from function signatures, and rich makes the event tables genuinely showable.
- **Storage: plain files on disk, in a gitignored `backend/data/` folder.** Parquet for tables (keeps column types, compact, pandas reads it natively) and JSON for small human-readable metadata. All file reading and writing lives in `btl/io.py`.
  ```
  backend/data/
  ├── league.json                      # clubs and players for the league seed
  ├── models/
  │   └── expected-threat.json         # the learned 16 × 12 grid + how it was fitted (matches, seed)
  └── matches/
      └── match-0007/
          ├── meta.json                # seed, clubs, schema version, planted moments
          ├── events.parquet           # one row per event: SPADL columns + our extension columns
          └── positions.parquet        # one row per player per event: event #, player, x, y
  ```
  - **Not stored: threat values and tags.** They're recomputed on `inspect` in milliseconds, so they can never be stale after a detector rule changes.
  - **The seed is the real backup.** Any match can be regenerated exactly, so the files are a convenience for inspecting results, not a source of truth.
  - **`schema_version` in meta.json** means old files fail loudly instead of loading wrongly.
  - No database in M1. Azure storage comes in a later milestone; these files map directly onto blob storage.
  - **Committed to git: one sample match only**, in `backend/examples/sample-match/`, about 100 KB, with planted moments. It is regenerated at T15 and linked from the README. The threat grid is *not* committed: it would go stale silently as the simulator changes, and refits make noisy diffs. Visitors run `btl fit-xt` once instead.
- **License: MIT** (public portfolio).

### 3.7 Architecture notes (gotchas we designed around)
1. **Explicit detector list, not a decorator.** A `@register` decorator only runs if its module is imported, so a forgotten import would silently drop a detector. `ALL_DETECTORS` is visible and type-checked.
2. **Separate random streams.** With one shared generator, planting a moment would reshuffle every random draw after it. `SeedSequence.spawn` gives the league, engine, shape, and planter their own streams.
3. **Positions as an array.** A snapshot for every event means about 33k positions per match. One numpy array per match plus `with_snapshots=False` for batch runs keeps threat fitting fast.
4. **Plant during generation, never splice afterwards.** Event numbers are assigned in one place as events are emitted, so "pause at #413" can't go stale.
5. **One place flips direction.** `frames.py` normalises events *and* snapshots so the team on the ball attacks left → right. Detectors never flip coordinates themselves.
6. **One definition of possession.** SPADL has no possession column. `schema/possession.py` derives possessions from events, and pressing and counter-attack both use it.
7. **pandas stays at the edges.** pandas types are loose and socceraction has no type hints. Confining them to `frames.py`, `value/`, and `cli/` keeps strict pyright meaningful everywhere else.
8. **Small ones.** Concept names are a `ConceptId` enum, so a typo fails at type-check time rather than silently. Python 3.11 syntax only (ruff `target-version = "py311"`). The `evidence` mapping on tags is read-only by convention.

---

## 4. Event schema sketch

**Canonical SPADL columns** (what `to_spadl_frame()` emits, *exactly* these, validated with `socceraction.spadl.SPADLSchema`):

| Column | Type | Our source |
|---|---|---|
| game_id | int | `Match.meta.game_id` |
| original_event_id | str | sim event id, e.g. `"g12-e0345"` |
| action_id | int | 0..n-1, order within game |
| period_id | int | 1, 2 |
| time_seconds | float | seconds since period start |
| team_id / player_id | int | fictional league IDs |
| start_x, start_y, end_x, end_y | float | metres, 0–105 × 0–68 |
| type_id | int | `ActionType` enum value (pass, cross, throw_in, …, dribble, goalkick) |
| result_id | int | `Result` (fail, success, offside, owngoal, yellow_card, red_card) |
| bodypart_id | int | `BodyPart` (foot, head, other, …) |

**Extension fields** (on `Event` and in a separate `events_ext` frame keyed by `(game_id, action_id)`, *not* in the SPADL frame, so socceraction sees pure SPADL even if its schema is strict):
`possession_id: int`, `phase: Phase` (open_play / set_piece / transition), `planted_moment_id: int | None`.

**Snapshot** (comparable to StatsBomb 360 freeze frames):
```python
@dataclass(frozen=True, slots=True)
class PlayerPosition:
    player_id: PlayerId; team_id: TeamId; x: float; y: float
    is_actor: bool; is_goalkeeper: bool

@dataclass(frozen=True, slots=True)
class Snapshot:
    game_id: GameId; action_id: ActionId   # positions at the *start* of this action
    positions: tuple[PlayerPosition, ...]  # 22 for sim data; may be partial for other sources
```
As a frame: long format `game_id, action_id, player_id, team_id, x, y, is_actor, is_goalkeeper`.

**Coordinate convention:** we store what socceraction's converters produce. The home team attacks left→right, and away actions are in the same absolute frame. Before xT we always call `spadl.play_left_to_right(actions, home_team_id)`, and snapshots get the same transform. Internally the sim reasons in "attacking direction" coordinates and converts once on output. *Exact converter conventions get verified against the installed socceraction in T2. This is the place where silent bugs would hide.*

**Vocabulary source of truth:** our enums are hand-written, so they show up in the IDE and pyright, and a test asserts that they match `socceraction.spadl.config.actiontypes/results/bodyparts` name for name and index for index.

---

## 5. Ordered tasks (one commit each, tests included)

Commits 0, 0b and 0c are docs. Commit 0 is the only one made directly on main; everything after it is on `feature/data-engine`. Showable checkpoints are marked ★.

| # | Task | Acceptance criteria |
|---|---|---|
| 0 | `README.md` on main | Short project description and status; gives main a first commit to branch from. |
| 0b | `docs/milestone-1/plan.md` | This plan, as agreed. First commit on `feature/data-engine`. |
| 0c | `CLAUDE.md` (your edited version) | Committed and no longer marked draft. |
| T1 | Project skeleton: uv, py3.11 pin, ruff, pyright strict, pytest, src layout, `btl --help` stub, CI, README quickstart section, LICENSE, `docs/setup.md` | Fresh clone: `uv sync && uv run pytest && uv run ruff check && uv run pyright` all pass; CI green after Lily pushes; setup.md reproduces it from a clean Mac. |
| T2 | socceraction spike + vocab enums | socceraction pinned exactly; enum-matches-config test passes; xT `fit`/`rate` smoke test on a 10-action hand-built frame; the coordinate convention is confirmed and written in `docs/event-schema.md`. **If install fails → see Risk 2 fallback before continuing.** |
| T3 | Schema: ids, Event, Snapshot, Match, possessions, frames | A hand-built 6-event fixture match → `to_spadl_frame()` passes `SPADLSchema.validate`; ext and snapshot frames round-trip; hypothesis: random valid events always validate; the left → right normalisation flips away-team events and snapshots together; the possession helper splits a fixture into the expected possessions. |
| T4 | Fictional league | `generate_league(seed)` is deterministic; 10 clubs × 20 players with positions and shirt numbers; a check against real club and player names finds no matches. |
| T5 | Pitch + shape model | 11 per side, exactly 1 GK, all in bounds; the defending block is measurably more compact than the attacking one; the block shifts with the ball (tests). |
| T6 | Simulator core (open play only) | `simulate_match(home, away, seed)` returns a Match; identical for the same seed; invariants: time monotonic within a period, coords in bounds, possession flips are consistent, SPADL valid; the derived possessions from `schema/possession.py` agree with the engine's own; < 1 s per match; `with_snapshots=False` skips position generation. |
| T7 ★ | CLI v1 + io | `btl simulate --seed 7 --out runs/` then `btl events runs/<id>` shows a readable rich table; save/load round-trips. **First demo-able state.** |
| T8 | Restarts + calibration (**timeboxed: 1 day**) | Kickoffs, throw-ins, goal kicks, corners; band tests over 50 seeds: passes 700–1100, completion 70–88%, shots 15–35, mean goals 1.5–4. When the bands pass, stop tuning. |
| T9 ★ | xT valuation | `btl fit-xt --matches 200 --seed 0` saves the model deterministically; `btl events` shows an xT column; test: mean xT of the final-third grid > own-third grid; `docs/milestone-1/expected-threat.md` written. |
| T10 | Detector framework + switch of play | `ALL_DETECTORS` holds one instance per `ConceptId` (test fails if a concept has no detector); switch-of-play positive/negative fixtures; `btl tags` lists tags. |
| T11 | Line-breaking detector | Fixtures: breaks 1 line, breaks 2 lines, sideways pass (no), long ball over a line with < 3 players (no); a narrower gap scores higher difficulty. |
| T12 | Pressing (counter-press) detector | Fixtures: regain in 4 s in opp half (yes), 7 s (no), own half (no). |
| T13 ★ | Planting framework + line-breaking template | `btl simulate --plant line_breaking_pass:1,2,3` → 3 planted moments, chronologically ordered by difficulty; **each is detected by T11 with matching difficulty order**; the match still passes all T6 invariants. `btl moments <match>` prints each with an ASCII pitch. |
| T14 | Pressing template + counter-attack detector | Planted ⇒ detected test for pressing; counter-attack fixtures: own-half win → box in 9 s (yes), 15 s (no), win in opp half (no). **Cuttable.** |
| T15 ★ | M1 wrap-up | `btl inspect <match>` combines events, xT, and tags; README walkthrough with demo commands; `backend/examples/sample-match/` regenerated and committed; summary written at the top of `implementation-notes.md`; setup.md audited from a clean checkout. |

Rough budget: T1–T7 ≈ 4–5 days, T8 ≤ 1 day, T9–T13 ≈ 4–5 days, T14–T15 ≈ 1–2 days. That leaves room before Oct 27 for the later milestones only if the cuts below are respected.

---

## 6. Risks & where to cut

1. **The simulator as a time sink (biggest).** The temptation is to keep tuning "until it looks real". Mitigations: the band tests in T8 *are* the definition of done, the 1-day timebox applies, and all knobs live in one `params.py`. Cut order if over budget: one formation only → no set pieces beyond kickoff and throw-in → a single team strength → drop period 2 (one long "half").
2. **socceraction installability.** It is unmaintained, and its pandas/pandera/numpy pins may fight modern wheels on 3.11. T2 is deliberately a spike, done *before* any schema code. Fallback: pin older pandas/numpy versions that work. Last resort: write our own xT (about 100 lines of value iteration, all new code) while still emitting valid SPADL, and document that.
3. **Coordinate-direction bugs.** A flipped team quietly produces nonsense xT. Mitigation: one convention, written down in T2, plus a test that a home and an away attack toward their goals both get higher xT near the goal they attack.
4. **Circularity: detectors tuned to the planter.** If a detector just "recognises the template", the test proves nothing. Mitigations: detectors can't import `plant/`, are written from football definitions in docstrings, and also get tested on hand-built fixtures and natural sim play.
5. **Snapshot plausibility.** The shape model can produce odd-looking positions that nobody notices until the UI. Mitigation: the ASCII pitch in T13. Optional stretch: an mplsoccer PNG.
6. **xT on synthetic data is circular.** Accepted; documented in T9.
7. **Accidental real names.** The syllable generator plus a denylist test (T4).
8. **Scope creep toward the learner model and tutor.** `PlantedMoment` stores the question/answer key and nothing more. No question text or explanations in M1.

**Minimum viable M1** (if everything goes wrong): T1–T7, T9, T10, T11, and T13. That's a simulator, xT, two detectors, line-breaking planting, and the CLI. Pressing, the 4th detector, and calibration polish are the cuts.

---

## 7. Decisions taken with Lily
- Layout: `backend/` from day one (workspace monorepo convention).
- Data models: frozen dataclasses + pandas at the socceraction boundary.
- Git: one branch per milestone (`feature/data-engine` for M1); one reviewed commit per task on it; `--no-ff` merge to main at the end of the milestone. No PRs.
- 4th detector: counter-attack (cuttable).
- Name "Between the Lines", package and CLI `btl`, MIT license. Line length 100 and Google docstrings unless changed in the CLAUDE.md draft.
- Type checker: pyright (strict) instead of mypy.
- Pushing: Claude commits locally only; Lily pushes. uv is installed by Claude via Homebrew in T1.
- Commits: short imperative subject, body only when the why isn't obvious (Lily's convention; replaces the Conventional Commits proposal).

## Order of work
1. Commit `README.md` as the first commit on main.
2. Create `feature/data-engine` from main. All remaining M1 work happens there.
3. Commit this plan (`docs/milestone-1/plan.md`) on the branch.
4. Commit the agreed `CLAUDE.md`.
5. T1 through T15, one reviewed commit each. Then `git merge --no-ff feature/data-engine` into main to close M1.

## Verification (for M1 as a whole)
- From `backend/`: `uv sync && uv run pytest && uv run pytest -m slow && uv run ruff check && uv run pyright` pass locally and in CI.
- `uv run btl simulate --seed 7 --plant line_breaking_pass:1,2,3 --out runs/` then `uv run btl inspect runs/<id>` shows events, xT values, concept tags, and the 3 planted moments with pitch snapshots.
- Following docs/setup.md from a clean checkout reproduces the environment.
