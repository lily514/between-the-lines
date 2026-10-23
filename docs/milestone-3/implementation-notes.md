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

## T3 — The container (2026-10-22)
**Plan said:** a multi-stage `Dockerfile` at the repo root (page, build, runtime): `python:3.11-slim` with a pinned uv, the image's own Python, `uv sync --locked --no-dev --no-editable`, `btl fit-xt` at build time; a non-root user, a `HEALTHCHECK`, `CMD btl serve`; an opt-in smoke test; measure the image's size, its cold start, and whether `httpx2` is there without dev dependencies.
**We did:** as planned, with these choices:
- **uv is pinned to 0.12.23,** the version that wrote `uv.lock`.
- **Dependencies install before the source is copied** (`--no-install-project` first), so a code change doesn't reinstall them.
- **The app's files belong to root,** and the app runs as uid 10001, so it can read its code, page and threat model but not change them. The smoke test checks both.
- **The model's call log goes to `/tmp`** (`BTL_TUTOR_LOG=/tmp/tutor-log.jsonl`), the one place the app may write. Otherwise the first model call with `--tutor foundry` would fail to write the log in `/app/data`. T9 replaces the file with log lines.
- **The image's defaults are the demo's:** the memory store and the template Tutor, listening on `0.0.0.0:8000`.
- **`.dockerignore`** keeps out everything the image doesn't need, above all `backend/private/` (the real-names list), `backend/data/` and `.azure/`.
- **The smoke test** (`tests/test_container.py`, `-m container`) builds the image and runs it on a free local port. It checks that the server answers, that Docker calls it healthy, that the threat model wasn't fitted at startup, the user it runs as, the page, and one question through to its feedback.

**Measured** on Lily's Mac (arm64):
- **The first build takes about a minute,** 11 s of it fitting the threat model; later builds take seconds while nothing changes.
- **The container answers its health check 1.9 s after it starts.** That is the whole cold start, since the threat model is already in the image.
- **The image is 755 MB.** Most of it is the scientific stack (numpy, pandas, scipy and pyarrow, which socceraction needs). That's well inside the registry's 10 GB, so trimming it isn't worth the time now.
- **`httpx2` is there:** `openai` depends on it, so `tutor/azure.py`'s import works without dev dependencies. It is still only an indirect dependency; declaring it directly would guard against openai dropping it, and is left as a small follow-up.

**Why:** the plan left these details open; the log path came from the read-only files.
**Affects:** T5 (azd builds this `Dockerfile` remotely; the probes use `/api/health`); T6 (`BTL_TUTOR=foundry` works with the log in `/tmp`); T9 (the log file gives way to log lines).

## T4 — Lily's module: Log Analytics and the Container Apps environment (2026-10-23)
**Plan said:** Lily writes `infra/modules/environment.bicep` (Log Analytics and the Container Apps environment), with each line explained; `azure.yaml`, `main.bicep`, `main.parameters.json` and `bicepconfig.json` around it; `az bicep lint` and `az bicep build` clean; a CI Bicep build step; `setup.md` covers azd, Bicep and `azd auth login --tenant-id`.
**We did:** as planned. Lily wrote the module in three steps (parameters, the workspace, then the environment, the diagnostic setting and the outputs). Her choices:
- **Logs reach the workspace through Azure Monitor and a diagnostic setting, not the workspace's shared key** (Lily's choice, 2026-10-23). The environment's `appLogsConfiguration.destination` is `azure-monitor`, a `Microsoft.Insights/diagnosticSettings` resource on the environment sends `allLogs` to the workspace, and the workspace has `disableLocalAuth: true`. The other route, `destination: 'log-analytics'`, needs the workspace's key, read in Bicep with `listKeys()` and stored in the environment. That breaks "no secrets anywhere", even though the key never reaches the repo.
- **The free settings:** pay-as-you-go (`PerGB2018`), 30-day retention, and a daily cap of 0.15 GB (`json('0.15')`, since Bicep has no decimals), about 4.5 GB a month inside the free 5 GB.
- **The Consumption workload profile,** and no zone redundancy.

Around the module:
- `main.bicep` is at subscription scope, creates `rg-${environmentName}`, and allows only eastus2. Names come from one `resourceToken`, and every resource carries the `azd-env-name` tag.
- `azure.yaml` builds the root `Dockerfile` in Azure's registry (`remoteBuild: true`).
- `bicepconfig.json` makes the secret and location rules errors.
- CI gains an `infra` job that builds and lints without signing in.
- `.azure/` is gitignored, and the Bicep extension is recommended for the workspace.

**Learned:**
- **The log tables are `ContainerAppConsoleLogs` (column `Log`) and `ContainerAppSystemLogs`,** not the plan's `ContainerAppConsoleLogs_CL` with `Log_s`, which belong to the key route.
- **`az bicep build` must run from the repo root:** from `backend/`, the relative path fails with "Could not find a part of the path".
- **Commands run with `!` inside a Claude Code session** inherit a temp folder Lily's user can't write to, so Bicep fails before reading the file. Lily's own terminal is unaffected.

**Why:** the plan left the logs route open; route B keeps the rule with no exceptions.
**Affects:** T9 (its KQL queries use `ContainerAppConsoleLogs` and `Log`); T5 (`main.bicep` gains the registry, identity, app and budget modules).

## T5 — Registry, identity, app and budgets: the public URL (2026-10-23)
**Plan said:** the rest of the modules except storage; `azd provision --preview` summarised for Lily, then `azd up` with her go-ahead; the public URL serves the page with the memory store and template Tutor; a second `azd provision` keeps the deployed image.
**We did:** as planned:
- **Modules:**
  - `identity.bicep`;
  - `registry.bicep` (Basic, admin user off, AcrPull for the identity on the registry alone);
  - `app.bicep` (0.5 vCPU, 1 GiB, at most one replica, probes on `/api/health`, pulls with the identity);
  - `app-image.bicep` (keeps the running image on later provisions);
  - `budget.bicep` ($10 for the group).
- **The $150 budget** sits in `main.bicep` at subscription scope.
- **Role ids** were looked up with `az role definition list`; AcrPull's id as remembered was wrong.
- **Lily approved `azd up`** after the preview. It took 21 minutes: 18 to create the Container Apps environment, under 3 to build the image in the registry and deploy it.
- **The public URL serves the page.** A question round trip with a new random viewer took 0.16 s to start, 0.77 s for the first question (preparing the match) and 0.14 s for the feedback, worded by the template.
- **Both budgets were created,** so the credit subscription accepts them. The app runs the image from our registry, with min 0 and max 1 replicas.

**Learned:**
- **azd 1.37 doesn't maintain `SERVICE_WEB_RESOURCE_EXISTS` for an app defined in our own Bicep;** it does that only for templates it generated. A preview after the first deploy showed the next provision would have restored the placeholder image and taken the site down. Two hooks in `azure.yaml` now keep it: `postdeploy` sets it to `true`, and `postdown` back to `false`. They change only the local azd environment.
- **The first deploy has a short broken window.** The placeholder (Microsoft's hello-world image) doesn't answer on port 8000, so its startup probes fail and it restarts. Single-revision mode keeps traffic on it until our revision is healthy. A request in that window waited 240 s and got a 504; the system log shows the whole sequence. This happens only on the very first deploy.
- **What-if noise:** Azure stores the three probes as liveness, readiness, startup, so `app.bicep` lists them in that order and previews don't report a change. Properties Azure fills in (`traffic`, `exposedPort`, `runningStatus`, the registry's defaults) show as `-`, and values from other resources as `[reference(…)]`; neither is a real change. azd's preview summary leaves out identities, role assignments, diagnostic settings and budgets; `az deployment sub what-if` shows them.
- **The diagnostic setting reports an extra category group, `audit`,** alongside `allLogs`.
- **A second `azd provision` (Lily's go-ahead) kept the image and the revision,** and took 57 s.
- **A cold start from zero replicas took 26.6 s** for the first request; warm requests take about 0.15 s. Locally the container is healthy in 1.9 s, so most of the wait is Azure placing the replica and pulling the 755 MB image onto a node that hasn't cached it (to confirm from the system log in T9). Minimum 1 replica while judges visit avoids it, as planned. A smaller image would pull faster; that is an idea for later, not a task.

**Why:** the plan didn't foresee azd's limit; the preview caught it before anything broke.
**Affects:** T6 and T8 (each later provision keeps the image); T10 (the docs explain the first-deploy window and the hooks).
