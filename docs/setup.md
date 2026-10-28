# Setup

Every step needed to get from a clean machine to a working environment, in order. This file feeds the future dev container, so keep it complete and update it in the same commit as any change that needs a new step.

## Local (macOS)

1. Install [Homebrew](https://brew.sh) if it isn't already installed.
2. Install uv, which manages Python, the virtual environment, and dependencies:
   ```sh
   brew install uv
   ```
3. Install the Python version uv will use. The project only accepts a uv-managed Python 3.11 (`python-preference = "only-managed"` in `pyproject.toml`), so system, pyenv, or Anaconda installs are ignored:
   ```sh
   uv python install 3.11
   ```
4. From `backend/`, create the virtual environment and install dependencies from the lockfile:
   ```sh
   cd backend
   uv sync
   ```
5. Check everything works:
   ```sh
   uv run pytest
   uv run ruff check
   uv run ruff format --check
   uv run pyright
   uv run btl --help
   ```

## The web page's API

`uv sync` also installs FastAPI and uvicorn. From `backend/`, `btl serve` serves the learning loop's API on <http://127.0.0.1:8000> (under `/api`), using the same learner records as `btl learn` (`data/learners/`). If the page has been built (`frontend/dist`), it serves that too; otherwise it says so and serves the API only.

```sh
uv run btl serve
uv run btl openapi --out ../frontend/src/api/openapi.json   # the schema the page's types are made from
```

Each `btl serve` option can also come from an environment variable, which is how the container is configured: `BTL_HOST`, `BTL_PORT`, `BTL_STORE` (`json` or `memory`), `BTL_LEARNERS`, `BTL_MODEL`, `BTL_FRONTEND`, `BTL_TUTOR`, `BTL_TUTOR_LOG`, and with `--tutor foundry` the daily limits `BTL_WORDINGS_PER_VIEWER` and `BTL_WORDINGS_PER_DAY` (`docs/deployment.md`). An option given on the command line wins. `GET /api/health` answers `{"status": "ok"}` once the server is listening.

## The web page

The page lives in `frontend/`: Vite, React and TypeScript, installed with npm.

1. Install Node 24, the version in `frontend/.nvmrc`. Either use [nvm](https://github.com/nvm-sh/nvm) (`nvm install` from `frontend/`) or Homebrew:
   ```sh
   brew install node@24
   ```
2. From `frontend/`, install dependencies from the lockfile:
   ```sh
   cd frontend
   npm ci
   ```
3. Check everything works:
   ```sh
   npm run typecheck
   npm run lint
   npm test
   npm run build
   ```

**Working on the page** takes two terminals: `uv run btl serve` in `backend/`, and `npm run dev` in `frontend/`. Vite serves the page with hot reload and passes `/api` requests on to `btl serve` on port 8000. **To try the finished page** with one command, run `npm run build` once, then `uv run btl serve` alone serves both at <http://127.0.0.1:8000>.

**After changing the API** (routes or response shapes), regenerate the page's types in the same commit:
```sh
cd backend && uv run btl openapi --out ../frontend/src/api/openapi.json
cd ../frontend && npm run api-types
```
A backend test fails if `openapi.json` is out of date, and a frontend test fails if `schema.d.ts` doesn't match it.

**After changing what the detectors find, the questions, or the evidence facts**, regenerate the page's scene fixtures in the same commit. Each is a real moment from seed 7's matches, one per concept asked about now, with its evidence pack, snapshot, timed path and the question each level asks; the page's animated scenes draw from them:
```sh
cd backend && uv run btl scene-fixtures   # writes frontend/src/scenes/fixtures/<concept>.json
```
A backend test fails if the committed fixtures are out of date.

## Optional: the demo video's clips

`frontend/scripts/capture-demo.ts` records the demo video's six clips: it plays the page in headless Chromium as a fixed viewer, records each clip with the DevTools screencast at full device pixels, and writes MP4s, a still per clip and `manifest.json` to `demo-captures/` at the repo root (gitignored). Each take starts its own `btl serve` on port 8766 with a memory store.

1. Install ffmpeg, and Playwright's Chromium from `frontend/`:
   ```sh
   brew install ffmpeg
   cd frontend
   npx playwright install chromium
   ```
2. Build the page, then record (`--only 03,05` re-records some clips, `--dry` saves a screenshot at each beat instead):
   ```sh
   npm run build
   node scripts/capture-demo.ts
   ```

The threat model must already be fitted (`backend/data/models/expected-threat.json`), or the first take waits while `btl serve` fits it. In a sandbox that blocks the system temp folder, set `TMPDIR` to a folder you can write to before both commands.

## Optional: the container (Docker)

The public demo runs as one container: the built page, the API and the learning engine, with the threat model fitted when the image is built. Building it locally needs [Docker Desktop](https://www.docker.com/products/docker-desktop/); deploying to Azure doesn't, since azd builds the image in Azure.

1. Install Docker Desktop and start it.
2. From the repo root, build and run the image:
   ```sh
   docker build -t btl .
   docker run --rm -p 127.0.0.1:8000:8000 btl
   ```
   The page is at <http://127.0.0.1:8000>. By default the container uses the template Tutor and keeps learner records in memory, so they are gone when it stops. Its `BTL_*` variables (see "The web page's API") change that, for example `docker run -e BTL_TUTOR=foundry …`.
3. The smoke test builds the image, starts it, checks its health, and plays one question through to its feedback. It is opt-in, because it needs Docker; from `backend/`:
   ```sh
   uv run pytest -m container
   ```

On Apple Silicon, Docker builds an arm64 image. Azure runs amd64, which is fine, because azd builds the deployed image in Azure's registry.

## Optional: the Blob learner store (Azurite)

In Azure, learner records are blobs in Azure Blob Storage (`--store blob`). Its tests run against [Azurite](https://learn.microsoft.com/azure/storage/common/storage-use-azurite), Microsoft's storage emulator, in Docker Desktop. They are opt-in, so the default `pytest` run needs neither.

1. Start Azurite (blobs only, kept in memory, so nothing outlives it):
   ```sh
   docker run -d --rm --name btl-azurite -p 127.0.0.1:10000:10000 \
     mcr.microsoft.com/azure-storage/azurite:3.35.0 \
     azurite-blob --blobHost 0.0.0.0 --inMemoryPersistence --skipApiVersionCheck
   ```
   `--skipApiVersionCheck` lets the current Python SDK talk to it.
2. Set `BTL_AZURITE_KEY` to Azurite's account key. Every copy of Azurite uses the same key, which Microsoft publishes on the page above ("Well-known storage account and key"); it opens only a local emulator. It is the one key this project uses, read from the environment by these tests only and never written into the repo.
   ```sh
   export BTL_AZURITE_KEY='<the published key>'
   ```
3. From `backend/`, run the Blob store through the learner store contract, plus its own cases:
   ```sh
   uv run pytest -m blob
   ```
   Without the key, or without Azurite running, these tests skip and say why.
4. Stop Azurite with `docker stop btl-azurite`.

## Optional: the public demo's infrastructure (Bicep and azd)

The public demo is described in Bicep (`infra/`) and deployed with the Azure Developer CLI (azd), which reads `azure.yaml`. Writing and checking the Bicep needs only the first two steps, and creates nothing in Azure.

1. Install the Bicep CLI (into the Azure CLI) and azd:
   ```sh
   az bicep install
   brew tap azure/azd && brew install azd
   ```
2. In VS Code, install the **Bicep** extension (the workspace recommends it): completions, hover docs and lint as you type. Check the Bicep from the repo root, as CI does:
   ```sh
   az bicep build --file infra/main.bicep --stdout > /dev/null
   az bicep lint --file infra/main.bicep
   ```
3. Sign azd in, **naming the tenant**. azd keeps its own sign-in, separate from `az login`, and has the same trap: without the tenant it may use your default one, and Azure refuses the token.
   ```sh
   azd auth login --tenant-id <tenant-id>
   ```
4. Create the azd environment, from the repo root. It lives in `.azure/btl-demo/` (gitignored): the resource group becomes `rg-btl-demo`, and the alert email reaches the budgets as a parameter, never the repo.
   ```sh
   azd env new btl-demo --subscription <subscription-id> --location eastus2
   azd env set ALERT_EMAIL <your-email>
   ```
5. **Preview first**, every time; it changes nothing:
   ```sh
   azd provision --preview
   ```
   The summary lists only the main resource types. The identity, role assignments, diagnostic setting and budgets show in the full what-if: `az deployment sub what-if --subscription <subscription-id> --location eastus2 --template-file infra/main.bicep --parameters environmentName=btl-demo location=eastus2 alertEmail=<your-email>`. Lines marked `-`, which Azure fills in by default, are noise; so are values shown as `[reference(…)]`, which are only known during the deployment.
6. Create everything and deploy, about 20 minutes the first time (most of it the Container Apps environment). It prints the public URL:
   ```sh
   azd up
   ```
   The registry costs about $5 a month from then on; everything else costs nothing while the app is idle. After the first deploy, a hook sets `SERVICE_WEB_RESOURCE_EXISTS=true`, so later provisions keep the deployed image instead of the placeholder. `azd deploy` alone rebuilds and redeploys the app.
7. To have the model word the questions, and for everything else about the running demo (the two commands outside Bicep, changing it, costs, taking it down), see [docs/deployment.md](deployment.md).

## Optional: check generated names against real ones

The committed repo contains no real club, player, place, or league names, not even as a list of names to avoid. To check that generated leagues never produce one, keep a private list at `backend/private/real-names.txt`. The whole `backend/private/` folder is gitignored, so the list is visible in your editor but never committed.

- One real name per line, `#` for comments. Matching ignores case and looks for the name anywhere inside each generated name.
- `uv run pytest` fails if any name style could produce a listed full name, and also scans 200 generated leagues for listed names. Without the file (in CI or a fresh clone), these tests are skipped.
- Source lists for the name pools are in `docs/name-sources.md`.

## Optional: the AI Tutor (Azure)

Everything else runs without Azure: the template Tutor is the default, and the tests never touch the network. To have a model word the questions and feedback (`--tutor foundry`), you need a model deployment in Azure AI Foundry that you can sign in to with Microsoft Entra ID. The app never uses a key.

The values below are placeholders: `<subscription>`, `<tenant-id>`, `<resource-group>` and `<resource-name>` are your own.

1. Install the Azure CLI and sign in:
   ```sh
   brew install azure-cli
   az login
   ```
2. **Name the subscription in every `az` command**, even one with a full `--ids`. If your login's default tenant isn't the subscription's, `az` otherwise sends the default tenant's token, and Azure answers `InvalidAuthenticationTokenTenant`. Find the subscription's tenant with:
   ```sh
   az account show --subscription <subscription> --query tenantId -o tsv
   ```
3. Create an Azure AI services resource (kind `AIServices`) in a resource group, and switch off key access, so only Entra ID sign-in works:
   ```sh
   az cognitiveservices account create --subscription <subscription> \
     --resource-group <resource-group> --name <resource-name> --custom-domain <resource-name> \
     --kind AIServices --sku S0 --location eastus2
   az resource update --subscription <subscription> \
     --resource-group <resource-group> --name <resource-name> \
     --resource-type Microsoft.CognitiveServices/accounts --set properties.disableLocalAuth=true
   ```
4. Deploy the model. The project uses `gpt-5.4-nano`, version `2026-03-17`, Global Standard (it retires on 2027-09-21):
   ```sh
   az cognitiveservices account deployment create --subscription <subscription> \
     --resource-group <resource-group> --name <resource-name> \
     --deployment-name gpt-5.4-nano --model-name gpt-5.4-nano --model-version 2026-03-17 \
     --model-format OpenAI --sku-name GlobalStandard --sku-capacity 250
   ```
5. Give yourself the **Cognitive Services OpenAI User** role on the resource. Owner of the subscription isn't enough: it has no data actions, so calls are refused with 401 until this role is added. If your tenant forbids directory (Graph) lookups, assign the role by your object id, which is the `oid` claim of your access token:
   ```sh
   az account get-access-token --subscription <subscription> --query accessToken -o tsv | python3 -c \
     "import base64,json,sys; p=sys.stdin.read().split('.')[1]; print(json.loads(base64.urlsafe_b64decode(p + '=' * (-len(p) % 4)))['oid'])"
   az role assignment create --subscription <subscription> \
     --role "Cognitive Services OpenAI User" --assignee-object-id <object-id> \
     --assignee-principal-type User \
     --scope "$(az cognitiveservices account show --subscription <subscription> \
       --resource-group <resource-group> --name <resource-name> --query id -o tsv)"
   ```
   **A new role takes a few minutes to work** (about 6 when this was first set up). Until then, calls get 401 `PermissionDenied`.
6. Tell the app where the model is, for example in your shell profile. Only the CLI reads these:
   ```sh
   export BTL_FOUNDRY_ENDPOINT=https://<resource-name>.openai.azure.com/
   export BTL_FOUNDRY_DEPLOYMENT=gpt-5.4-nano
   export BTL_FOUNDRY_TENANT=<tenant-id>
   ```
   The tenant is always named, because `az login` may default to a different one. In Azure the app needs no tenant: it signs in as its managed identity, named by `AZURE_CLIENT_ID` (`docs/deployment.md`).
7. Check the model answers, from `backend/`:
   ```sh
   uv run btl tutor-ping
   ```
   It prints the deployment, how long the call took and the tokens used. A first call takes a second or two.

Optional: connect the resource to an Azure AI Foundry hub project (with Entra ID) to try prompts in its playground. The app doesn't use the hub; it calls the resource's endpoint directly. A small budget alert on the resource group is also worth setting.

## Editor (VS Code)

The repo includes workspace settings in `.vscode/`. Open the repo root as the workspace.

1. Install the recommended extensions when VS Code prompts you: Python, Pylance, and Ruff. Or install Ruff directly:
   ```sh
   code --install-extension charliermarsh.ruff
   ```
2. Run `uv sync` in `backend/` first (step 4 above), so the interpreter the settings point to exists.
3. If imports still show as unresolved, run **Python: Select Interpreter** and choose `backend/.venv/bin/python`.

The settings make ruff the formatter and linter, and turn off Flake8 and Pylint for this workspace, because they don't read the project's ruff configuration. They also mirror the pyright settings from `backend/pyproject.toml`: Pylance only reads configuration from the workspace root.

## Continuous integration

`.github/workflows/ci.yml` runs the same checks on every push, to any branch, in two jobs. The backend job uses `uv sync --locked`, so CI fails if `uv.lock` is out of date. The frontend job uses `npm ci`, which fails if `package-lock.json` doesn't match `package.json`, then runs the type check, lint, tests and build.
