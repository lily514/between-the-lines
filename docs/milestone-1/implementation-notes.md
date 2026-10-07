# Milestone 1: Implementation notes

Where implementation diverged from [plan.md](plan.md), or something surprising was learned. One note per occurrence, added in the same commit as the change.

## T1 — Project skeleton (2026-10-07)
**Plan said:** pin Python with `uv python pin 3.11` so the project doesn't depend on pyenv.
**We did:** also set `python-preference = "only-managed"` under `[tool.uv]` in `pyproject.toml`.
**Why:** with only the pin, uv picked an existing Anaconda Python 3.11.4 from the search path. The pin fixes the version, not where the interpreter comes from.
**Affects:** nothing; `docs/setup.md` includes `uv python install 3.11`.
