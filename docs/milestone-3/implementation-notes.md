# Milestone 3: Implementation notes

Where implementation diverged from [plan.md](plan.md), or something surprising was learned. One note per occurrence, added in the same commit as the change.

## Summary (2026-10-23)

Milestone 3 is done. The demo is public on Azure Container Apps, built and created from code by `azd up`. It signs in to everything as its managed identity, so no key exists anywhere. It keeps each visitor's progress in Blob Storage, words questions and feedback with the model within daily limits, and reports every step of the loop to Log Analytics. T1 to T10 are in, and Lily went through every command that changed Azure before it ran.

**Biggest changes from the plan**
- **The credential is chosen in `tutor/azure.py`, not `cli/`** (T6). The 2b code used the Azure CLI's sign-in, not `DefaultAzureCredential`, so a managed identity needed a small code change. Only `azure.py` and `store/blob.py` may import an Azure SDK.
- **The limits count wordings, not calls** (60 per viewer and 1,000 a day, which bound the calls at the plan's 120 and 2,000). They sit in front of the wording cache, so cached words stay free (T6).
- **Logs reach Log Analytics without a key,** through Azure Monitor and a diagnostic setting (Lily's choice in her module, T4). So the tables are `ContainerAppConsoleLogs` with `Log`, not the plan's `…_CL` with `Log_s`.
- **azd doesn't keep `SERVICE_WEB_RESOURCE_EXISTS` for an app in our own Bicep.** Two hooks in `azure.yaml` do; without them, the second provision would have restored the placeholder image. The preview caught it (T5).
- **Two more events:** `full_time`, for the funnel, and `wording_fallback` through a new callback on the Verifier. There's no access log, because the platform already records each request (T9).
- **The demo deployment's capacity went from 10 to 30** (Lily's choice, T9). A capacity unit is 1,000 tokens *and one request* a minute, and capacity 10 throttled a single fast player.
- **Random viewer ids come from `crypto.getRandomValues`, not `randomUUID`,** and "Start over" asks first (T2).

**Measured**
- **The image:** 755 MB, with the threat model fitted when it is built.
- **Starting up:** healthy 1.9 s after the container starts locally. A cold start from zero replicas in Azure takes 26.6 s; a warm request takes about 0.15 s.
- **The first `azd up`** took 21 minutes, 18 of them the Container Apps environment. Later ones take about 4 minutes.
- **The model on the live demo:** 80% of first tries that got a reply passed, the 95th percentile of call time was 4.6 s, and the whole milestone's test traffic cost about $0.007 in tokens. The subscription has spent $0.57 of its $150 this month.

**Cut:** nothing from the plan. CI/CD and Cosmos DB were out of scope from the start. The teardown test (`azd down --purge`, then `azd up`) wasn't run before the hackathon's close, because it would delete every learner record and might change the public address.

**Carries over**
- **One replica, because the wording cache and the limits live in memory.** More replicas would need both shared (Blob Storage or a cache service), and per-IP limits.
- **Long-term storage:** one blob per attempt plus a head blob, or Cosmos DB with one item per attempt, if queries across viewers are wanted.
- **The image is mostly the scientific stack;** a smaller one would make cold starts quicker.
- **A visitor's progress lives in one browser's id;** real sign-in is the next step for identity.
- **`httpx2` comes in through `openai`** and isn't declared directly.
- **CI deploys nothing.** OpenID Connect from GitHub, with a separate deployer identity, is the plan's stretch idea.

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

## T6 — The model, in the cloud (2026-10-23)
**Plan said:** `cli/` chooses `ManagedIdentityCredential` when `AZURE_CLIENT_ID` is set; the two `az` commands in `docs/deployment.md`, run with Lily's go-ahead after a read-only quota check; limits of 120 model calls per viewer and 2,000 a day, with "template (daily limit)"; then `BTL_TUTOR=foundry`, model-worded text on the URL.
**We did:** as planned, with these choices:
- **The credential is chosen in `tutor/azure.py`, not `cli/`,** since only `azure.py` may import an Azure SDK. `FoundrySettings` gains an optional `client_id`, and `default_credential` gives the managed identity when it is set, otherwise the Azure CLI in the named tenant. `cli/` reads `AZURE_CLIENT_ID` into the settings, and asks for `BTL_FOUNDRY_TENANT` only without it.
- **The limits count wordings, not calls:**
  - **60 per viewer and 1,000 a day.** A wording is one question or one feedback, and costs at most two calls, so these bound the calls at the plan's 120 and 2,000. Counting calls exactly would mean following each call back to its viewer through the Verifier's records, from several viewers at once.
  - **The limit sits in front of the wording cache** (`LimitedTutor` over `CachedTutor`, in `api/limits.py`). Cached words are free and never counted, so a reload past the limit still shows the same words. Uncached words past it come from the template; only feedback carries a source to say so.
  - **The API marks whose request it is in a context variable,** set with each viewer's lock. The Tutor protocol never sees the viewer, and no viewer reaches a prompt.
  - **The variables are `BTL_WORDINGS_PER_VIEWER` and `BTL_WORDINGS_PER_DAY`,** not the plan's `BTL_MODEL_CALLS_*`.
- **`docs/deployment.md` starts here,** as a living reference: what is deployed, the two commands, the limits, costs, and taking it down. T10 adds the diagram and the queries.

**Checked against Azure:**
- **Quota:** gpt-5.4-nano Global Standard in eastus2 allows 5,000 and the existing deployment uses 250, so the demo's 10 fits (read-only check).
- **Lily approved the two `az` commands.** `gpt-5.4-nano-demo` was created (Global Standard, capacity 10), and the identity now holds exactly AcrPull on the registry and Cognitive Services OpenAI User on the Foundry resource.
- **The preview** showed only the container's variables changing.
- **`azd up` (Lily's go-ahead)** took 4 minutes, and the `postdeploy` hook set `SERVICE_WEB_RESOURCE_EXISTS=true` by itself.
- **On the public URL,** a round trip was worded by the model: the question took 5.4 s, including preparing the match, and the feedback 2.3 s, with source `gpt-5.4-nano-demo`. The role worked at once, with no wait.

**Learned:**
- **In Azure, the service names the model by its deployment** (`gpt-5.4-nano-demo`), so that is what the source line shows. Locally it showed `gpt-5.4-nano`.
- **The provision's revision ran the old image with the new variables** (`…0000001`). That image doesn't know `AZURE_CLIENT_ID` and stops without a tenant, so the revision never took traffic; single-revision mode kept the previous one serving until the deploy replaced both.
- **KQL treats `last` as a reserved word.**
- **The first round trip after the deploy failed with 404 on `/next`.** The system log shows why. During the switchover the platform woke the previous revision from zero (17:53:28), moved traffic to the new one (17:53:42) and deactivated the old one (17:54:13). The new viewer was created in the old revision's memory, and its next request reached the new revision, which had never seen it. A second round trip worked. With the memory store every deploy or restart forgets every viewer, and a request that straddles a switchover can be forgotten at once; T8's Blob store, shared by every revision, is the fix.

**Why:** counting calls exactly per viewer would need the viewer inside the Tutor chain, which the design keeps out.
**Affects:** T9 (a `limit_reached` event from `LimitedTutor`); T10 (the docs build on `deployment.md`).

## T7 — The Blob store (2026-10-23)
**Plan said:** `store/blob.py`; the contract suite passes against Azurite under `-m blob`; the network-import test allows `store/blob.py` to import `azure`; `azure-storage-blob` added; `btl serve --store blob`; `docs/setup.md` covers Azurite and `BTL_AZURITE_KEY`.
**We did:** as planned:
- **`BlobLearnerStore(container)`** keeps `<viewer id>.json`, the JSON store's own document, typed `application/json`.
  - `create` uploads without overwriting, which the SDK sends as `If-None-Match: *` (exists → `LearnerExistsError`).
  - `put` uploads with `If-Match: <etag>` (412 → `StaleWriteError`; a missing blob → `KeyError`).
  - The etag is the blob's own ETag.
- **`blob_container(account_url, container, client_id, tenant)`** signs in with the managed identity when there is a client id, otherwise with `az login` in `BTL_FOUNDRY_TENANT`. It sits in `store/blob.py` because only that module and `tutor/azure.py` may import an Azure SDK; the four lines of credential choice are therefore written twice.
- **`btl serve --store blob`** takes `--blob-account-url` (`BTL_BLOB_ACCOUNT_URL`) and `--blob-container` (`BTL_BLOB_CONTAINER`, default `learners`), and stops with a message if the URL is missing.
- **The contract suite is unchanged.** `STORES` gains `blob`, and the fixture marks it `blob`, so it runs only with `-m blob`.
  - Each test gets a fresh Azurite container.
  - The fixture skips with the reason when `BTL_AZURITE_KEY` is unset or Azurite doesn't answer, with no retries and a 2 s timeout, so a missing emulator never hangs the run.
- **Three Blob-only tests** (`tests/store/test_blob.py`) cover what the contract doesn't: `put` for a learner who isn't stored, a write after another server changed the blob, and the blob's document and content type.
- **The network-import test** now expects exactly `btl.store.blob` and `btl.tutor.azure`.

**Checked:** with Azurite 3.35.0 in Docker, all nine Blob tests pass (the six contract tests and the three of its own); without the key they skip with the reason, and the default run deselects them. The default run passes, with ruff and strict pyright.
**Learned:**
- **Azurite needs `--skipApiVersionCheck`** for the current SDK (12.31).
- **The SDK types one parameter of `create_container` as a bare `dict`,** so the test fixture ignores that one pyright rule on that line, with a comment.
- **`btl serve --store blob` can't be tried against Azurite:** the server signs in with Entra ID tokens, which Azurite doesn't take over plain HTTP. T8 tries it against the real account.

**Why:** the plan left these details open.
**Affects:** T8 (Bicep sets `BTL_STORE=blob` and `BTL_BLOB_ACCOUNT_URL`, and grants the identity Storage Blob Data Contributor on the `learners` container).

## T8 — Storage in the cloud (2026-10-23)
**Plan said:** `storage.bicep` with shared keys off and the two roles; `BTL_STORE=blob`; previewed, then provisioned; progress survives a reload and a new revision (a second `azd deploy`), which also proves the app's data role works.
**We did:** as planned:
- **`storage.bicep`:**
  - a StorageV2 account (Standard LRS, hot) with `allowSharedKeyAccess: false`, `defaultToOAuthAuthentication: true` (so the portal signs in with Entra ID), no public blob access, HTTPS and TLS 1.2 only;
  - the blob service and a private `learners` container;
  - Storage Blob Data Contributor **on the container**, not the account, for the app's identity, and for the developer when azd passes one.
- **The app's variables** become `BTL_STORE=blob`, plus `BTL_BLOB_ACCOUNT_URL` and `BTL_BLOB_CONTAINER` from the module's outputs. The app module reads those outputs, so Bicep creates the storage and its roles before the app's new revision.

**Checked against Azure:**
- **The preview** (Lily's go-ahead to run `azd up` followed it) showed the account, blob service, container and Lily's role assignment to create. The app's role showed as unsupported, as T5's AcrPull did, since its principal is only known during the deployment.
- **`azd up`** took 3 m 51 s. Both role assignments exist on `learners`, and the account has shared keys and public access off.
- **A new viewer's record is in the container** (`<id>.json`, 560 bytes), listed with `az storage blob list --auth-mode login` as Lily, which proves her data role. Read back through the API it shows the same match, bars and waiting question: what a reload sees.
- **After a second `azd deploy` (Lily's go-ahead)** and a new revision, the same viewer reads back unchanged. That is the acceptance check, and it also proves the app's data role.

**Learned:**
- **The first request after the deploy hit the T6 switchover problem once more.** A viewer was created by the outgoing revision, which still used the memory store, and the next request reached the new one: 404. That viewer isn't in storage. It was the last time: every revision now shares the container.
- **azd passes `AZURE_PRINCIPAL_ID` to the parameters during each provision without saving it** in the environment file; `azd env get-value` shows nothing. The developer's role was created with Lily's object id all the same.
- **The new data role worked at once:** no 403 while it took effect.

**Why:** the plan's design held.
**Affects:** T10 (the README's honest limits: progress lives in one browser's id, and nothing else identifies a visitor).

## T9 — Events and queries (2026-10-23)
**Plan said:** JSON log lines and the access log; the events `question_asked`, `answer_graded`, `mastery_updated`, `model_call`, `wording_fallback` and `limit_reached`; three KQL queries over `ContainerAppConsoleLogs`, checked against the live workspace, in the README.
**We did:** as planned, with these choices:
- **`api/events.py`** writes each event as one JSON line through the `btl.events` logger. Only `btl serve` sends that logger to stdout, so the terminal stays quiet.
- **Who writes which event:**
  - `api/app.py` writes the loop's own events.
  - **`full_time` is new:** the funnel needs finished matches.
  - `cli/` writes `model_call` from each `CheckRecord`.
  - `wording_fallback` comes from a new `on_fallback` callback on `VerifiedTutor`, with a `Fallback(kind, pack_id, concept, reasons)`. Its check records alone can't say when the template was finally used.
  - `limit_reached` comes from `LimitedTutor`. `Allowance.take` now returns which limit is spent ("viewer" or "day"), or None, instead of a yes or no.
- **No uvicorn access log.** Container Apps already records every request at its ingress (`ContainerAppHTTPLogs`, seen in T5), and an access log would add a health-probe line every 10 s.
- **`question_asked` repeats on a reload,** so the queries count distinct questions by `pack_id`.
- **The README gains "Watching the demo":** the funnel, who worded the feedback by concept, the model by day, and a fourth query, why the template was used.
- **Logging is process-wide state,** so the CLI tests that run `serve` leave it alone, and one test checks the stdout handler itself and cleans up after it.

**Checked against Azure:**
- **`azd deploy` (Lily's go-ahead) took 2 m 54 s.**
- **Two scripted viewers each played a whole match** through the model. The container's live log stream (`az containerapp logs show`) shows every event as one JSON line.

**Learned:**
- **Log Analytics has no `percentileif`.** The model query keeps the seconds of successful calls in their own column and takes percentiles of that, since percentiles skip empty values.
- **The deployment's 10K tokens a minute cap is easy to reach for a script.** The second scripted viewer, answering at once and straight after the first, got `RateLimitError: Error code: 429` on most calls, and every one fell back cleanly to the template: the guardrail worked as designed. A person reading each question and feedback uses far fewer tokens a minute.
- **The events reached the workspace about 8 minutes after they were written.**
- **Two fixes after running the queries:**
  - The fallback label says "Template: fallback", not "Verifier fallback", since a failed call (such as a 429) falls back too; the reasons query tells them apart.
  - The first-try pass rate counts only calls that got a reply. Counting the 429s gave 46%, which isn't comparable with 2b's evaluation.

**The queries against the live workspace** (the two scripted viewers):

| Query | Result |
|---|---|
| Funnel | 2 visitors, 13 questions, 13 answers (3 right), 2 matches finished |
| Who worded the feedback | the model or the template's fallback, per concept, with shares |
| The model | 30 calls, first try passed 75% of those that got a reply, 11 with no reply, 1.59 s median and 7.33 s at the 95th percentile, 17,449 tokens in and 1,747 out, about $0.006 |
| Why the template | "no reply" 6 times for feedback and 5 for questions: all the token cap, none a failed check |

**The cap, raised (Lily's go-ahead):** the demo deployment went from capacity 10 to 30, the plan's `az` command run again with `--sku-capacity 30`. Azure reports what a capacity unit gives: **1,000 tokens and 1 request a minute**. So capacity 10 had allowed only 10 requests a minute, and the scripted viewer's ~15 calls a minute met the request limit before the token one. Capacity 30 allows 30,000 tokens and 30 requests a minute, about two or three people playing at once. The cap costs nothing in itself (tokens are paid per use), and the daily limits still bound the spending. `docs/deployment.md` shows capacity 30.

**Why:** the plan left the events' sources open; the access log was redundant with the platform's own.
**Affects:** T10 (the README's honest limits mention the cap under load).

## T10 — Docs (2026-10-23)
**Plan said:** `docs/deployment.md` as a living reference (the architecture in Mermaid, `azd up`, the two `az` commands, the minimum-replicas switch for judging, teardown, costs, what each role allows); the README gets "Try it online", the URL, the queries and honest limits.
**We did:** as planned. Most of `deployment.md` was written as the work happened (T6, T8, T9). T10 adds:
- the architecture diagram, which shows every resource, every sign-in and the one role that allows each;
- "From nothing to a public URL", in order;
- "Changing it": code against infrastructure, the minimum-replicas switch, cold starts, the first deploy's placeholder, watching the logs live;
- a note that teardown deletes every learner record.

The README gains:
- a status row for Milestone 3;
- "Try it online", with the URL;
- two honest limits: the model's small ceiling, and the demo sleeping;
- links to `deployment.md` and the Milestone 3 docs.

`setup.md` ends its azd steps with a pointer to `deployment.md`.

**Checked:** the diagram renders with Mermaid's own renderer (mermaid-cli 11.4.2). Its subgraph title names `rg-btl-demo`, since Mermaid doesn't decode `&lt;` in labels.
**Why:** the plan's design held.
**Affects:** T11 (the live checklist follows `deployment.md`).

## T11 — Wrap-up (2026-10-23)
**Plan said:** the live checklist; the implementation-notes summary; the `--no-ff` merge; the teardown test if time allows.
**We did:**
- **The live checklist passed:**
  - the page loads on a desktop and on a true 390 px phone viewport;
  - a question round trip is worded by the model;
  - the same viewer reads back unchanged after a reload;
  - the events reach Log Analytics and the queries return rows;
  - a property-level what-if shows `azd provision` would change nothing real;
  - both budgets exist.
- **The summary** is at the top of these notes.

**Learned:** Chrome's plain `--headless --window-size=390,…` can't make a window that narrow, so its phone screenshot looked clipped. A real mobile viewport (puppeteer, 390 px) shows the page fits exactly, with no overflow.
**Not done:** the teardown test, for the reasons in the summary.
**Why:** the plan's checklist held.
**Affects:** nothing.

## After T11 — A readable app name in the URL (2026-10-27)
**Plan said:** nothing; T5 named the container app `ca-web-${resourceToken}` with every other resource.
**We did:** named it `between-the-lines`, so the demo URL starts with the project instead of a hash:
`https://between-the-lines.whitesky-8ac56dd8.eastus2.azurecontainerapps.io/`. Only the first label of the host is
ours; the rest is the Container Apps environment's domain, which Azure generates when the environment is created
and which can't be chosen or re-rolled. Replacing that half needs a custom DNS suffix on the environment (a domain
we own plus a wildcard certificate), or a per-app custom domain with a free managed certificate — both wanted a
domain purchase, so neither was done.

A container app's name has to be unique only inside its resource group, and each azd environment gets its own
(`rg-<env>`), so dropping the resource token here can't clash.

**Learned:** the rename wants a particular order. `app-image.bicep` keeps the deployed image by reading the
existing app *by name*, so with `SERVICE_WEB_RESOURCE_EXISTS=true` the new name points that lookup at a resource
that doesn't exist yet. `azd provision --preview` passed anyway, but what-if resolves a `reference()` it can't
follow instead of failing on it, so the preview doesn't settle whether a real provision would. Setting the flag
false for one run sidesteps the question: `azd env set SERVICE_WEB_RESOURCE_EXISTS false`, then `azd up`
(provision puts the new app on the placeholder image, deploy replaces it with the real one and the postdeploy
hook sets the flag back), then delete the old `ca-web-oeafow3mvh7xi`.

The old app has to go by hand. The preview lists it as `Skip`: Bicep deploys incrementally and never deletes what
it no longer names, and it keeps the `azd-service-name: web` tag that `azd deploy` matches on, so leaving both in
place would make a later deploy ambiguous. It serves the old URL until it is deleted, so the demo is never down.

The same preview reports property-level `Modify`s on the environment (`peerAuthentication`,
`peerTrafficConfiguration`) and the registry (`anonymousPullEnabled`, `dataEndpointEnabled`, `encryption`,
`azureADAuthenticationAsArmPolicy`). These are the known what-if noise from T11: defaults Azure fills in that the
template doesn't name, unchanged by this commit.
**Why:** a hash in front of a demo URL reads badly, and the fix costs nothing.
**Affects:** nothing. `MIN_REPLICAS` and every other setting carry over; the new app is the same Bicep.
