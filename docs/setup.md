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

`.github/workflows/ci.yml` runs the same checks on every push, to any branch, using `uv sync --locked` so CI fails if `uv.lock` is out of date.
