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

## Optional: check generated names against real ones

The committed repo contains no real club, player, place, or league names, not even as a list of names to avoid. To check that generated leagues never produce one, keep a private list at `backend/private/real-names.txt`. The whole `backend/private/` folder is gitignored, so the list is visible in your editor but never committed.

- One real name per line, `#` for comments. Matching ignores case and looks for the name anywhere inside each generated name.
- `uv run pytest` fails if any name style could produce a listed full name, and also scans 200 generated leagues for listed names. Without the file (in CI or a fresh clone), these tests are skipped.
- Source lists for the name pools are in `docs/name-sources.md`.

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
