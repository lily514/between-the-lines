# Milestone 3: Implementation notes

Where implementation diverged from [plan.md](plan.md), or something surprising was learned. One note per occurrence, added in the same commit as the change.

## T1 — Server ready for a container (2026-10-22)
**Plan said:** `/api/health`; a lock per viewer, with the wording cache and the prepared-match cache locked on their own; the prepared-match cache bounded, with a prepared match's memory measured; `btl serve` options with `BTL_*` fallbacks, including `--host`, `--port` and `--store memory|json`.
**We did:** as planned, with these choices:
- **`/api/health` is left out of the OpenAPI schema.** The page never calls it, so the page's generated types don't change, and the API contract is untouched.
- **Each viewer's lock lives only while a request holds it** (a `WeakValueDictionary`). A plain dictionary would keep a lock for every visitor ever seen.
- **A match is prepared outside the cache's lock.** Two viewers meeting the same new match at the same moment may both prepare it; the results are identical, and neither waits for the other.
- **The wording cache keeps the first words stored.** Its lock is never held during a model call. If two viewers ask for the same words at once, both are worded, and both get whichever was stored first. Without that rule, the second wording could replace words a viewer had already seen, breaking "a question is worded once".
- **The environment fallbacks are on `btl serve` only.** `btl learn` and `btl demo-viewer` keep reading only their command line, as before.
- **`--store` defaults to `json`,** so `btl serve` on Lily's Mac behaves exactly as before.

**Measured:** a prepared match holds about 2 MB (1.7–2.3 MB over three seeds, with `tracemalloc`). So the cache of 32 matches stays under about 75 MB, well inside the container's 1 GiB.

**Checked:** with the old single lock put back temporarily, the new test where one viewer's slow question shouldn't hold up another fails; with a lock per viewer it passes.
**Why:** the plan left these details open.
**Affects:** T3 (the container sets `BTL_HOST=0.0.0.0` and the other variables); T5 (the probes use `/api/health`).
