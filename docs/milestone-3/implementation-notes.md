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

## T2 — A random viewer id (2026-10-22)
**Plan said:** the page makes `crypto.randomUUID()` and keeps it as `btl.viewer`; no name field; "Not lily?" becomes "Start over", which makes a new id; the API is unchanged; a UUID passes `check_viewer_id`.
**We did:** as planned, with three changes:
- **The id is 128 random bits from `crypto.getRandomValues`,** written as 32 lower-case hex characters, not `crypto.randomUUID()`. `randomUUID` only exists on secure pages (HTTPS or localhost), so the page would break if opened by a network address over plain HTTP. `getRandomValues` works everywhere, and the id is just as unguessable. It fits the API's viewer id rule; a frontend test checks 100 ids against the rule, and a backend test checks examples of the format with `check_viewer_id`.
- **"Start over" asks first** ("Start over? Your progress here can't be found again." with "Yes, start over" and "Keep going", focus on "Keep going"). With a typed name, a viewer could always type it again; a forgotten random id is gone for good, so one click shouldn't lose a viewer's progress. It is one shared component (`Shared/StartOver.tsx`), used in the header and on the welcome screen.
- **The page never shows the id:** the welcome says "Welcome" rather than "Welcome, lily". An id kept in this browser that the API refuses (one edited by hand, say) is forgotten, and the reason is shown above Start.

**Learned:** a viewer can no longer carry on in the browser from `btl learn` (or the other way round), since nobody types the id. The records are still the same kind; the README says so.
**Why:** `randomUUID`'s secure-page rule, and a click that can't be undone.
**Affects:** nothing in the API: its schema and the page's generated types are unchanged.
