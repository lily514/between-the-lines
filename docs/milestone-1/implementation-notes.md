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
