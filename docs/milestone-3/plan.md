# Milestone 3 Plan: Deploy it properly

> Agreed 2026-10-22. This plan is frozen; where implementation diverges, see [implementation-notes.md](implementation-notes.md). Milestone 3's branch is `feature/deploy`.
> Milestone 2 is done and merged: **2a** the learning engine in the terminal, **2c** the web page, **2d** the basics, **2e** getting started and **2b** the AI Tutor (41d8e5d).

## Context

The learning loop runs in a browser, with model-worded questions and feedback, but only on Lily's Mac: `btl serve` listens on `127.0.0.1`, the learner records are JSON files in `data/learners/`, and the Tutor signs in with Lily's `az login`. Milestone 3 puts it on a public URL.

**The goal.** One `azd up` builds the app, creates every Azure resource from code (Bicep), and serves a public demo URL. No secrets exist anywhere: not in the repo, not in files, not in app settings. A visitor opens the URL, plays through matches, and keeps their progress between visits.

**This milestone is Lily's main Azure learning goal,** so explaining matters as much as building:
- Before any resource is created, what it is, why we need it and what it costs.
- Lily writes the first Bicep module herself (Log Analytics and the Container Apps environment), with every line explained.
- Each role assignment is walked through when it is made.

**Decided (Lily, 2026-10-22): the simplest deploy and persistence that meet the goal.**
- **Persistence: Azure Blob Storage,** one JSON blob per viewer, the blob's ETag as the stale-write check. It is the JSON store moved to Azure. Cosmos DB was the first idea; Blob is simpler for one document read and written whole, uses an ordinary Azure role, and its emulator (Azurite) is mature on Apple Silicon.
- **Foundry: reuse Lily's existing resource,** with a new small deployment for the demo (`gpt-5.4-nano-demo`), so the public demo has its own token cap and the 250K deployment stays for `tutor-eval`. The deployment and the app's role on it are two documented `az` commands: the one exception to "everything from code", because Bicep reaching into the hand-made resource group would put it at risk from `azd down`.
- **A separate resource group** for the demo, in the same subscription and region (eastus2), so `azd down --purge` removes exactly the demo.
- **Telemetry is JSON log lines on stdout,** which Container Apps already sends to Log Analytics. No Application Insights or OpenTelemetry. Lines may carry the random viewer id.
- **Each visitor gets a random id made in the browser** (`crypto.randomUUID()`), so the API doesn't change. No sign-in.
- **The wording cache stays in memory.** After a cold start a pending question is worded again, as 2b already accepts.
- **Limits:** a model budget per viewer, a global daily cap of 2,000 model calls, and the demo deployment's token cap. Past any of them, the template words it. No per-IP limits.
- **Everything stays free within the subscription's $150 monthly credit.** The subscription's spending limit is on (Lily checked), which is the hard stop; budgets alert at $150 for the subscription and $10 for the demo. Alerts go to Lily's email, kept in the azd environment, not the repo.
- **The emulator's published key** may be used by opt-in tests, read from an environment variable, never committed.
- **No CI/CD.** Deploys are `azd` commands Lily runs, or approves.
- **Keep Azure Container Registry (Basic),** about $5 a month from the credit and the only fixed cost. The Container App itself is free at minimum 0 replicas, inside the monthly free grant. A public image on GitHub's registry would cost nothing, but then `azd up` would no longer build the app.

**Not in Milestone 3:** AKS, Static Web Apps, sign-in, multiple regions, a custom domain, FSRS, the Jev grader, Cosmos DB, Application Insights, per-IP limits, a shared wording cache, CI/CD.

**Budget:** about 4.75 days, ending with the hackathon's close on 2026-10-27. A public URL comes early (T5); everything after it improves it. The video fits around the work.

## How it works

```
                      ┌──────────── rg-btl-demo (azd, Bicep) ─────────────────────────────┐
browser ── HTTPS ──►  │ Container App "web" (1 replica max, 0 or 1 min)                   │
  random viewer id    │   btl serve: page + /api + learning engine, threat model baked in │
  in localStorage     │   │ pulls image (AcrPull)        │ stdout JSON lines              │
                      │   ▼                              ▼                                │
                      │ Container Registry (Basic)   Log Analytics ◄─ Container Apps env  │
                      │   ▲ azd remote build         (KQL queries)                        │
                      │ User-assigned identity ──► Storage account: blob per viewer       │
                      │   │                         (Storage Blob Data Contributor)       │
                      │ Budget $10 (group)                                                │
                      └───┼───────────────────────────────────────────────────────────────┘
                          │ Cognitive Services OpenAI User (az command, documented)
                          ▼
     Lily's Foundry resource (existing group) ── gpt-5.4-nano-demo, 10K tokens/min (az command)
     Budget $150 (subscription scope, Bicep)
```

- **One container** serves the built page, the API and the learning engine, exactly as `btl serve` does locally. The threat model is fitted when the image is built, so no visitor waits for it.
- **One replica at most.** The prepared-match cache, the wording cache and the limits live in memory; with one replica they are correct without shared state. 0.5 vCPU is plenty for a demo. Minimum replicas is a parameter: 0 normally (it scales to zero and costs nothing idle), 1 while judges are likely to visit (no cold start).
- **The app signs in as its managed identity** to pull its image, call the model and read and write blobs. No key or connection string exists.

## Decisions

### Azure resources and cost

Prices are pay-as-you-go list prices as known on 2026-10-22; task 0 checks them in the Azure pricing calculator and notes any difference.

| Resource | SKU / mode | What it is, and why | Idle per month | Per demo session* |
|---|---|---|---|---|
| Resource group `rg-btl-demo` | | A folder for everything the demo owns; `azd down` deletes it as one unit | $0 | |
| Log Analytics workspace | Pay as you go, 30-day retention, daily cap 0.15 GB | Stores the app's console logs; queried with KQL. The first 5 GB a month are free, and the cap keeps it inside that | $0 | <$0.001 |
| Container Apps environment | Consumption | The boundary the app runs in: its network, and where its logs go | $0 | |
| Container App `web` | 0.5 vCPU, 1 GiB, max 1 replica | The app, with HTTPS ingress and scale to zero | $0 at min 0; about $8–12 at min 1 | ~$0 (inside the monthly free grant) |
| Container Registry | Basic | Holds the image. azd builds it in the registry (remote build), so deploying needs no local Docker | **about $5** | a build is a few cents |
| User-assigned managed identity | | The app's identity in Entra ID; every role is granted to it | $0 | |
| Storage account | StorageV2, Standard LRS, hot, shared keys off | One private container, `learners`, one blob per viewer | <$0.01 | <$0.0001 |
| Budgets | Subscription ($150) and resource group ($10) | Email alerts. **A budget alerts; it never stops spending** | $0 | |
| Demo model deployment (existing resource) | gpt-5.4-nano, Global Standard, capacity 10 (10K tokens a minute) | The demo's own token cap | $0 | about 1–2¢ (about 50 calls: 44k tokens in, 4.6k out) |

\* One visitor playing three matches with the model Tutor.

**Totals:** about $5 a month idle; about $1–2 more for a judging week at minimum 1 replica; a few cents per session. **Worst case:** the demo deployment used flat out all day is about 14M tokens, about $3 a day. The global cap of 2,000 model calls a day (about 2.4M tokens) holds it to about $0.50 a day, and the spending limit is the backstop.

**Region: eastus2.** Lily's Foundry resource and its quota are there, and Container Apps, Storage and the registry are all available there. One region keeps app-to-model and app-to-storage latency at a few milliseconds and avoids cross-region data transfer. "Global Standard" means a call may be *processed* in any region; the region decides where the resource and its quota live. All data is synthetic, so residency doesn't matter.

### Identity and roles

**A user-assigned managed identity,** not a system-assigned one. A system identity is born with the app, so on the first deploy the app tries to pull its image before its AcrPull role exists. A user-assigned identity exists first, so every role is in place before the app starts; it also survives the app being recreated. The app is told the identity's client id in `AZURE_CLIENT_ID`.

| Who | Role | Scope | Allows | Where |
|---|---|---|---|---|
| App identity | AcrPull | The registry | Pulling images | Bicep |
| App identity | Storage Blob Data Contributor | The `learners` container | Reading and writing its blobs, nothing else in the account | Bicep |
| App identity | Cognitive Services OpenAI User | Lily's Foundry resource | Calling its deployments; no management rights | `az` command |
| Lily (azd's `principalId`) | Storage Blob Data Contributor | The `learners` container | Looking at records in the portal (with shared keys off, the portal needs a data role too) | Bicep |

Two things each walkthrough covers:
- **Control plane and data plane.** Owner of the subscription can create and delete a storage account (control plane) but can't read a blob in it without a data role (data plane), just as Owner couldn't call the model in 2b until "Cognitive Services OpenAI User" was added.
- **A new role takes a few minutes to work** (about 6 in 2b). Bicep assigns roles before the app's first revision, and the checklist waits for them.

**The code change for the managed identity is small.** 2b's `AzureClient` uses `AzureCliCredential(tenant_id=…)`, chosen on purpose: `DefaultAzureCredential` returned the wrong tenant's token on Lily's Mac (2b plan, "Talking to Azure"). `AzureClient` already takes a `credential`, so `cli/` chooses it: `ManagedIdentityCredential(client_id=…)` when `AZURE_CLIENT_ID` is set, otherwise `AzureCliCredential(tenant_id=BTL_FOUNDRY_TENANT)`. The Blob store gets the same credential. `tutor/` doesn't change.

### Configuration

Bicep is the source of truth for the deployed app's configuration. The app reads environment variables in `cli/` only, as Typer `envvar=` fallbacks on `btl serve`'s options, so the CLI keeps working as it does today.

```
azd env (.azure/<env>/.env, gitignored): AZURE_ENV_NAME, AZURE_LOCATION, AZURE_SUBSCRIPTION_ID,
   ALERT_EMAIL, MIN_REPLICAS, FOUNDRY_ENDPOINT, FOUNDRY_DEPLOYMENT, ...
        │  infra/main.parameters.json maps them to parameters
        ▼
main.bicep ── module outputs ──► the container app's env block, in the same deployment:
        │                           BTL_TUTOR, BTL_STORE, BTL_BLOB_ACCOUNT_URL, BTL_FOUNDRY_ENDPOINT,
        │                           BTL_FOUNDRY_DEPLOYMENT, AZURE_CLIENT_ID, BTL_MODEL_CALLS_PER_DAY, ...
        └── main.bicep outputs ──► back into the azd env (registry endpoint, URL, identity ids)
```

- Every value is a name, an endpoint or an id. None is a secret, so no Key Vault is needed.
- Lily's real values (subscription, tenant, Foundry endpoint, email) stay in the azd environment or her shell. The repo has placeholders, as in 2b.

| Variable | `btl serve` option | Default | In Azure |
|---|---|---|---|
| `BTL_HOST`, `BTL_PORT` | `--host`, `--port` | `127.0.0.1`, `8000` | `0.0.0.0`, `8000` |
| `BTL_MODEL` | `--model` | `data/models/expected-threat.json` | the baked-in file |
| `BTL_FRONTEND` | `--frontend` | `../frontend/dist` | the baked-in page |
| `BTL_STORE` | `--store memory\|json\|blob` (new) | `json` | `memory` until T8, then `blob` |
| `BTL_LEARNERS` | `--learners` | `data/learners` | unused |
| `BTL_BLOB_ACCOUNT_URL`, `BTL_BLOB_CONTAINER` | `--blob-account-url`, `--blob-container` (new) | none, `learners` | from Bicep |
| `BTL_TUTOR` | `--tutor` | `template` | `template` until T6, then `foundry` |
| `BTL_TUTOR_LOG` | `--tutor-log` | `data/tutor-log.jsonl` | off: records go to the log lines |
| `BTL_MODEL_CALLS_PER_VIEWER`, `BTL_MODEL_CALLS_PER_DAY` | (new) | 120, 2000 | from Bicep parameters |
| `BTL_FOUNDRY_ENDPOINT`, `BTL_FOUNDRY_DEPLOYMENT`, `BTL_FOUNDRY_TENANT` | | | endpoint and `gpt-5.4-nano-demo`; the tenant is unused in Azure |
| `AZURE_CLIENT_ID` | | | the app identity's client id |

### The server, ready for a container

- **`GET /api/health`** answers `{"status": "ok"}` without loading anything. `btl serve` loads the course before it starts listening, so a server that answers is ready. Today an unknown path returns `index.html` with 200, so a probe on any other path would be fooled.
- **A lock per viewer** replaces the one lock for every request. Today one viewer's model call (up to 12 s) stalls every other viewer. Two requests for the *same* viewer still take turns, and the store's ETag refuses a clash. The wording cache and the prepared-match cache get their own small locks.
- **The prepared-match cache is bounded** (least recently used, 32 matches to start; T1 measures a prepared match's memory). It is unbounded today, and every random visitor brings a new seed.
- **`httpx2`** is imported at runtime by `tutor/azure.py` but declared as a dev dependency. The container installs without dev dependencies, so T3 finds out whether openai brings it in, and moves it to the runtime dependencies if not.

### The container

A multi-stage `Dockerfile` at the repo root (the build needs both `frontend/` and `backend/`):
1. **page:** `node:24-slim`, `npm ci`, `npm run build`.
2. **build:** `python:3.11-slim` with a pinned `uv` binary copied in. `pyproject.toml` asks uv for its own managed Python (`python-preference = "only-managed"`), which would download a second Python in the image, so the stage sets `UV_PYTHON_PREFERENCE=only-system` and `UV_PYTHON_DOWNLOADS=never`, and uses the image's 3.11. Then `uv sync --locked --no-dev --no-editable`, and **`btl fit-xt`** writes the threat model (deterministic, about 10 s, 5.7 KB).
3. **runtime:** `python:3.11-slim`, the virtual environment, the threat model and the page copied in; a non-root user (uid 10001); `WORKDIR /app`; `HEALTHCHECK` on `/api/health` (with Python's `urllib`, since the slim image has no curl); `CMD btl serve`, configured by the variables above.

Container Apps ignores Docker's `HEALTHCHECK` and uses its own probes, so Bicep sets startup, liveness and readiness probes on `/api/health` too. The `HEALTHCHECK` is for `docker run` and the smoke test.

Lily's Mac builds an arm64 image; Container Apps runs amd64. That's fine, because azd builds the deployed image in the registry, which builds amd64. The local image is for the smoke test.

### Infrastructure as code

**Hand-written Bicep, not Azure Verified Modules.** Verified modules are maintained by Microsoft, with secure defaults, and azd's own templates use them. But each is a large parameter surface over code you don't see, which hides what this milestone is meant to teach, and a failure means debugging the module rather than your resource. This project has about eight resources, so small hand-written modules (20–60 lines each) stay readable and every line can be explained. We own their correctness, which `bicep lint`, `az bicep build` and `azd provision --preview` check before every change. Verified modules stay useful as a reference ("what does Microsoft set that we didn't?").

```
azure.yaml                     # one service, "web": Dockerfile at the root, remote build, host containerapp
Dockerfile, .dockerignore
infra/
├── main.bicep                 # subscription scope: the resource group, the subscription budget, the modules
├── main.parameters.json       # azd env values → parameters
├── bicepconfig.json           # linter rules
└── modules/
    ├── environment.bicep      # Lily's: Log Analytics + Container Apps environment
    ├── identity.bicep         # user-assigned identity
    ├── registry.bicep         # Container Registry + AcrPull
    ├── storage.bicep          # storage account, `learners` container, the two blob roles
    ├── app.bicep              # the container app: image, identity, env, probes, scale
    └── budget.bicep           # the resource group's budget
```

- **Settings that keep it free and keyless:** the registry has its admin user off; the storage account has `allowSharedKeyAccess: false`, no public blob access and TLS 1.2; Log Analytics has the daily cap and 30-day retention.
- **The image on re-provision.** azd creates the app with a placeholder image, then `azd deploy` sets the real one. A later `azd provision` must not put the placeholder back, so `app.bicep` uses azd's usual pattern: when the app already exists, it keeps the current image. T5 explains and tests this.
- **The budgets.** The subscription budget is created at subscription scope, so `azd down` leaves it in place, which is intended. Some credit-based subscription types don't support Cost Management budgets. If `azd provision --preview` or the provision says so, the budgets become a documented portal step, and the spending limit stays the backstop.

### Persistence: the Blob store

`BlobLearnerStore(container: ContainerClient)` in `store/blob.py` implements the existing `LearnerStore` protocol, with one blob per viewer (`<viewer_id>.json`, the same `to_document` JSON the file store writes):

| Protocol | Blob call | Error mapping |
|---|---|---|
| `get(viewer_id)` | download the blob and its ETag | not found → `None` |
| `create(state)` | upload with `If-None-Match: *` (never overwrite) | already exists → `LearnerExistsError` |
| `put(state, etag)` | upload with `If-Match: <etag>` | ETag changed → `StaleWriteError`; no such blob → `KeyError` |

- **The store takes a ready-made container client.** `cli/` builds it with the managed identity (or Lily's `az login` locally); the test fixture builds it with Azurite's key. The store itself has no key path.
- **The contract suite runs unchanged.** The `STORES` registry in `tests/store/test_learner_store.py` gains a `blob` entry carrying a `blob` marker, so it is opt-in. Each test gets a fresh container in Azurite, deleted after. Without the emulator running, or without `BTL_AZURITE_KEY`, those tests skip and say why.
- **No 2 MB limit applies.** A blob can be far larger than a viewer's record (about 10 KB for three matches). The long-term question is the *shape*: rewriting a growing record on every answer. The long-term design is one blob per attempt plus a small head blob, or, if queries across viewers are wanted, Cosmos DB with one item per attempt and a transactional batch per answer. Neither is built.
- **Locally,** `btl serve` keeps the JSON files by default; `--store blob` works against Azurite or the cloud account.

### Guardrails for a public demo

- **A random viewer id.** On a first visit the page makes `crypto.randomUUID()` (lower-case, 36 characters, which fits the existing id rule) and keeps it in `localStorage` as `btl.viewer`. The name field goes. "Not lily?" becomes "Start over", which makes a new id. The API doesn't change. A random id can't be guessed, which also ends "anyone who types a name *is* that viewer". `btl learn --viewer NAME` is unchanged.
- **Limits on what costs money.** The template path is free, so only model calls are limited:
  - **Per viewer:** 120 model calls a day (about two full sessions with repairs).
  - **Global:** 2,000 model calls a day.
  - **The deployment:** 10K tokens a minute. Azure answers 429 past it, which is already a `ModelError`, which already falls back to the template.

  The counts come from the Tutor's `CheckRecord`s, in memory, by UTC day; a restart resets them (accepted: the token cap still holds). Before each request the API checks the allowance; when a limit is spent, that request uses the template Tutor, and feedback's source reads "template (daily limit)". The limits live in `api/`, take the clock as a parameter, and are tested with a fake clock.
- **Model text still reaches the viewer only through the Verifier,** and no viewer id goes in a prompt. The limiter uses the viewer id, but only to count.

### Telemetry

Container Apps sends everything the app writes to stdout to Log Analytics. The app writes one JSON object per line, through Python's `logging` with a JSON formatter set up by `btl serve`:

| Event | Fields | From |
|---|---|---|
| `question_asked` | viewer_id, match_number, concept, level, form, delivery, pack_id | `/next` |
| `answer_graded` | viewer_id, concept, level, correct, source | `/answers` |
| `mastery_updated` | viewer_id, concept, before, after | `/answers` |
| `model_call` | kind, attempt, passed, reasons, error, seconds, tokens in and out | each `CheckRecord` (replaces the JSONL file in Azure) |
| `wording_fallback` | kind, concept, reasons | when the template is used after the model was asked |
| `limit_reached` | scope (viewer or global) | the limiter |

- Events are written by `api/` and `cli/`, never by `learn/`, which stays pure (it already hands back `Asked`, `Told` and `CheckRecord`s).
- Uvicorn's access log goes on at info level, so every request is also a line.
- **Saved queries for the README** (KQL over `ContainerAppConsoleLogs_CL`, parsing `Log_s` as JSON; T9 confirms the table and column names in the new environment):
  1. **The funnel, by day:** visitors, questions asked, answers, matches finished.
  2. **Wording:** model-worded against template share, by concept, and the commonest failed checks.
  3. **The model:** calls, p50 and p95 seconds, tokens and an estimated cost per day, and limits reached.

## Tasks

☁ marks a task with a command that creates or changes Azure resources. Each is previewed first and run only with Lily's go-ahead.

| # | Task | Done when |
|---|---|---|
| 0 | Plan and CLAUDE.md | Plan committed; CLAUDE.md updated (below); prices checked in the pricing calculator |
| T1 | Server ready for a container | `/api/health`; a lock per viewer, with the wording cache and prepared-match cache locked on their own; the prepared-match cache bounded, with a prepared match's memory measured; `btl serve` options with `BTL_*` fallbacks, including `--host`, `--port` and `--store memory\|json`. Tests: health without a course; two viewers' requests run at once, and a stalled fake model for one doesn't hold up the other; the cache drops its oldest match; options read from the environment |
| T2 | A random viewer id | The page makes and keeps a UUID; no name field; "Start over"; the App tests cover a first visit, a return visit and starting over. The API, its schema and types are unchanged. A UUID passes `check_viewer_id` (backend test) |
| T3 | The container | `Dockerfile` and `.dockerignore` as above. An opt-in test (`-m container`) builds the image, starts it with the memory store and template Tutor, waits for `/api/health`, and plays one question through to its feedback. The image's size, cold start and the `httpx2` question are measured and noted. `docs/setup.md`: Docker Desktop, the opt-in tests |
| T4 | **Lily's module:** Log Analytics and the Container Apps environment | Lily writes `infra/modules/environment.bicep`, with each line explained. `azure.yaml`, `main.bicep`, `main.parameters.json` and `bicepconfig.json`. `az bicep lint` and `az bicep build` are clean; CI gains a Bicep build step (no Azure login needed). `docs/setup.md`: azd, Bicep, and `azd auth login --tenant-id`, since azd has the same wrong-tenant trap as `az` |
| T5 ☁ | Registry, identity, app and budgets: the public URL | The rest of the modules except storage. `azd provision --preview` summarised for Lily, then `azd up` with her go-ahead. **The public URL serves the page with the memory store and template Tutor.** A second `azd provision` keeps the deployed image |
| T6 ☁ | The model, in the cloud | `cli/` chooses `ManagedIdentityCredential` when `AZURE_CLIENT_ID` is set (tested with the environment set and unset). The two `az` commands (demo deployment, the app's role), in `docs/deployment.md`, run with Lily's go-ahead, after a read-only look at the subscription's quota. The limits (per viewer, global) with "template (daily limit)". Then `BTL_TUTOR=foundry` deployed: the URL shows model-worded text, and a per-viewer limit of 0 shows the template |
| T7 | The Blob store | `store/blob.py`; the contract suite passes against Azurite under `-m blob`; the network-import test allows `store/blob.py` to import `azure`; `azure-storage-blob` added; `btl serve --store blob`. `docs/setup.md`: starting Azurite and `BTL_AZURITE_KEY` |
| T8 ☁ | Storage in the cloud | `storage.bicep` with shared keys off and the two roles; `BTL_STORE=blob`. Previewed, then provisioned. **Progress survives a reload and a new revision** (a second `azd deploy`), which also proves the app's data role works |
| T9 | Events and queries | The JSON log lines and access log; the event table above; the three KQL queries, checked against the live workspace, in the README |
| T10 | Docs | `docs/deployment.md`, a living reference: the architecture (Mermaid), `azd up`, the two `az` commands, the minimum-replicas switch for judging, teardown (`azd down --purge` plus removing the demo deployment and role), costs, and what each role allows. README: "Try it online", the URL, the queries, honest limits (progress lives in one browser; limits reset on a restart) |
| T11 | Wrap-up | The live checklist (below) done; implementation-notes summary; `--no-ff` merge |

Rough days: 0 0.25, T1 0.5, T2 0.25, T3 0.5, T4 0.5, T5 0.5, T6 0.5, T7 0.5, T8 0.25, T9 0.5, T10 0.25, T11 0.25, so about 4.75.

## CLAUDE.md changes (commit 0)

- **Git workflow:** M3 "Deploy it properly": `feature/deploy`.
- **What this is:** Milestone 3 deploys the page and API: one `azd up` builds the container and creates every Azure resource from Bicep, serving a public demo URL, with managed identity and no secrets.
- **Learning design rules:** each visitor's viewer id is a random id made by the browser; the limits on model calls fall back to the template, as any other failure does.
- **A new section, "Azure and deployment":** the layout (`azure.yaml`, `Dockerfile`, `infra/`); hand-written Bicep is the source of truth for the deployed configuration; the app reads environment variables only in `cli/`; one replica; managed identity for everything; no secrets anywhere, with the emulator key the one exception; real values in the azd environment or Lily's shell, placeholders in the repo; the two documented `az` exceptions; everything stays within the $150 credit; and **the command safety rules**:
  - Ask before running any command that creates, changes or deletes Azure resources or could cost money, including `azd up`, `azd provision`, `azd deploy`, `azd down`, `az … create/update/delete`, role assignments and `docker push`.
  - Preview infrastructure changes first (`azd provision --preview`) and summarise what will change.
  - Never write secrets, keys or connection strings into files, the repo or app settings.
  - Name the subscription in every `az` command.
- **Python style (I/O):** `btl/store/blob.py` joins `tutor/azure.py` as the only modules that import an Azure SDK.
- **Testing:** opt-in markers `blob` (Azurite) and `container` (Docker); the default run stays offline and needs neither.
- **Commands:** `azd provision --preview`, `azd up`, `azd deploy`, `azd down --purge` (each with Lily's go-ahead); `uv run pytest -m blob`, `uv run pytest -m container`.
- **Docs:** `docs/deployment.md` is a living reference.

## Risks and cuts

1. **Time.** About 4.75 days against the hackathon's close, with the video still to make. The order puts the public URL at T5 (about day 2); everything after it improves a working demo.
2. **Budgets unsupported on a credit subscription.** The preview shows it; the spending limit is the hard stop either way, and the budgets become a portal step.
3. **Quota for the demo deployment.** 10K tokens a minute must fit in the subscription's gpt-5.4-nano quota. A read-only look comes first; if it doesn't fit, the demo uses the existing deployment, with the app's daily caps as the only limit.
4. **The image reset on re-provision** (azd's placeholder image). T5 checks a second provision keeps the deployed image.
5. **Tenant traps.** azd signs in on its own (`azd auth login --tenant-id`), and the managed identity has no tenant to get wrong. `setup.md` covers both.
6. **Cold start** with minimum 0 replicas: the first visitor waits for the container to start (seconds, since the threat model is baked in). Minimum 1 for judging.
7. **The log table's name** varies with how the environment sends logs (`ContainerAppConsoleLogs_CL` with `Log_s`, or `ContainerAppConsoleLogs` with `Log`). T9 checks against the live workspace.

**Cut order if short:**
1. Events and saved queries (plain request logs stay).
2. The Blob store in the cloud: the memory store, so progress lasts only while the container runs, documented in the README.
3. The model in the cloud: the public demo uses templates.

Never cut: the limits while the model is on, the budgets and the safety rules.

## Verification

- From `backend/`: `uv run pytest`, `ruff check`, `ruff format --check` and `pyright` pass, offline, with no Docker or Azure. With Azurite running: `uv run pytest -m blob`. With Docker: `uv run pytest -m container`.
- From `frontend/`: `npm test`, `npm run lint` and `npm run build` pass.
- `az bicep lint` and `az bicep build --file infra/main.bicep` are clean; CI runs the build.
- `azd provision --preview` lists exactly the expected resources before each provision.
- **The live checklist** after deploying:
  - the public URL loads, on a phone width and on desktop;
  - a question round trip works, with the model's words (or the template's, past a limit);
  - progress survives a page reload, and a new revision;
  - the events appear in Log Analytics, and the three queries return rows;
  - `azd provision` again changes nothing it shouldn't;
  - the budgets exist (or the portal step is done).
- **Teardown,** once before the close if time allows: `azd down --purge`, then `azd up` again gives a working URL. That proves the code creates everything.

## Order of work

This plan ("Add Milestone 3 plan"), then the CLAUDE.md commit, then T1. Nothing in Azure is created before T5, and each ☁ step is previewed and run only with Lily's go-ahead.
