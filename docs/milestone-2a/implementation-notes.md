# Milestone 2a: Implementation notes

Where implementation diverged from [plan.md](plan.md), or something surprising was learned. One note per occurrence, added in the same commit as the change.

## T1 — Groundwork (2026-10-08)
**Plan said:** a public function `line_breaking.lines_broken(snapshot, team_id, start, end)`, used by the detector; CLI tests pass with `FORCE_COLOR` set.
**We did:**
- `lines_broken` is a method on `LineBreakingPass`, not a module function. It returns the width of the gap the pass goes through in each line it breaks, nearest first, so its length is the number of lines broken. `detect` now calls it.
- A root `tests/conftest.py` clears `FORCE_COLOR` before the CLI is imported. The CLI itself is unchanged.

**Why:**
- The rule's thresholds (how far apart players can be and still form a line, and how many make a line) are fields of the detector. A module function would need them as extra arguments, or would ignore a detector built with other values. The answer options also need the gap widths, not only the count.
- The CLI's rich console is created when `btl.cli.app` is imported, and rich reads `FORCE_COLOR` at that moment, so the tests' per-call environment couldn't undo it. With the variable set, output was coloured, and `btl replay` believed it ran in a terminal: it animated and waited for Enter. Honouring `FORCE_COLOR` is right for real use, so the fix belongs in the tests.

**Affects:** T7 measures answer options with `LineBreakingPass().lines_broken`.
