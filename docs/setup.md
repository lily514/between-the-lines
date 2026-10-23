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

Each `btl serve` option can also come from an environment variable, which is how the container is configured: `BTL_HOST`, `BTL_PORT`, `BTL_STORE` (`json` or `memory`), `BTL_LEARNERS`, `BTL_MODEL`, `BTL_FRONTEND`, `BTL_TUTOR` and `BTL_TUTOR_LOG`. An option given on the command line wins. `GET /api/health` answers `{"status": "ok"}` once the server is listening.

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
   The tenant is always named, because `az login` may default to a different one.
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
