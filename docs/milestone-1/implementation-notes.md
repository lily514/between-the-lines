# Milestone 1: Implementation notes

Where implementation diverged from [plan.md](plan.md), or something surprising was learned. One note per occurrence, added in the same commit as the change.

## T1 — Project skeleton (2026-10-07)
**Plan said:** pin Python with `uv python pin 3.11` so the project doesn't depend on pyenv.
**We did:** also set `python-preference = "only-managed"` under `[tool.uv]` in `pyproject.toml`.
**Why:** with only the pin, uv picked an existing Anaconda Python 3.11.4 from the search path. The pin fixes the version, not where the interpreter comes from.
**Affects:** nothing; `docs/setup.md` includes `uv python install 3.11`.

## T2 — socceraction trial run (2026-10-07)
**Plan said:** pin socceraction exactly; if it fights modern packages, first try pinning older versions.
**We did:** pinned `socceraction==1.5.3`, and constrained `multimethod<1.11` via `constraint-dependencies` in `pyproject.toml`.
**Why:** socceraction caps pandera at 0.17, and pandera 0.17 imports `multimethod.overload`, which was deprecated in multimethod 1.11 and removed in 2.0. Without the constraint, `import socceraction.spadl` fails. The rest of the stack resolves fine: numpy 1.26.4 (socceraction caps it below 2), pandas 2.3.3, scipy 1.17.1.
**Affects:** nothing yet. The pin is the first thing to revisit if we ever upgrade.

## T2 — Discoveries in socceraction (2026-10-07)
**Plan said:** keep extension fields in a separate frame "even if its schema is strict"; verify the coordinate convention.
**We did:** confirmed both. `SPADLSchema` is strict and rejects extra columns. Converters store the home team attacking left → right in both periods, exactly as planned.
**Why it matters:** two surprises for T9. Expected Threat's interpolation option is broken (SciPy removed `interp2d`), so we use the plain 16 × 12 grid. And `save_model` writes only the bare grid, so our model file with fitting details (matches, seed, simulator version) will be our own JSON format.
**Affects:** T9.

## T2 — Pyright and socceraction (2026-10-07)
**Plan said:** only edge modules may relax type checking, with `# pyright: basic`.
**We did:** also set `reportMissingTypeStubs = false` project-wide.
**Why:** socceraction has inline type hints but no `py.typed` marker. Without this setting, every import of it is an error, even in files that are otherwise fully typed. It's narrower than switching whole files to basic mode.
**Affects:** nothing.

## T3 — Schema (2026-10-07)
**Plan said:** `Match` holds meta, teams, events, the position array, and planted moments; the position array is events × 22 × 2.
**We did:** `Match` holds only the game id, the two team ids, the events, and optional positions. Positions cover any number of tracked players, each described by a `PlayerSlot`, with `NaN` for unknown positions.
**Why:** the league, its clubs, and planted moments don't exist yet. Each will be added to `Match` by the task that creates it (T4 and T13). A fixed 22 would rule out the partial snapshots the plan says other data sources may supply, and would make small test fixtures needlessly large.
**Affects:** T4 and T13 extend `Match`.

## T3 — Smaller schema choices (2026-10-07)
**Plan said:** no detail on these.
**We did:** `original_event_id` is derived from the game and action ids (`"g1-e0003"`), not stored. Direction flipping is a `left_to_right=True` option on `to_spadl_frame` and `to_snapshot_frame`, not a separate function. The possession rule is written up in `docs/event-schema.md`.
**Why:** the fewest moving parts; the flag keeps every flip inside `frames.py`, as planned.
**Affects:** nothing.
