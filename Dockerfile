# syntax=docker/dockerfile:1
# The demo's one container: the built page, the API and the learning engine, served by `btl serve`.
# Build it from the repo root: `docker build -t btl .`. Configure it with BTL_* variables (docs/setup.md).

# 1. The page: Vite builds frontend/ into static files.
FROM node:24-slim AS page
WORKDIR /frontend
# The lockfile first, so the install is cached until a dependency changes.
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# 2. The app: uv installs backend/ and its locked dependencies into /app/.venv, then fits the threat model.
FROM python:3.11-slim AS build
COPY --from=ghcr.io/astral-sh/uv:0.12.23 /uv /bin/uv
# pyproject.toml tells uv to use only its own downloaded Pythons; in the image, the image's 3.11 is the one.
ENV UV_PYTHON_PREFERENCE=only-system \
    UV_PYTHON_DOWNLOADS=never \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv
WORKDIR /src
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --locked --no-dev --no-install-project
COPY backend/ ./
RUN uv sync --locked --no-dev --no-editable
# Fitted now, so no visitor waits for it: the same 200 matches `btl serve` would fit on first use.
RUN /app/.venv/bin/btl fit-xt --out /app/data/models/expected-threat.json

# 3. The runtime: the same Python, with the environment, the threat model and the page, and nothing to build with.
FROM python:3.11-slim
RUN useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin btl
WORKDIR /app
COPY --from=build /app /app
COPY --from=page /frontend/dist /app/frontend
# The files belong to root, so the app can read them but not change them. Records are in memory unless BTL_STORE
# says otherwise, and the model's call log goes to /tmp, the one place the app can write.
ENV PATH=/app/.venv/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    BTL_HOST=0.0.0.0 \
    BTL_PORT=8000 \
    BTL_STORE=memory \
    BTL_TUTOR=template \
    BTL_MODEL=/app/data/models/expected-threat.json \
    BTL_FRONTEND=/app/frontend \
    BTL_TUTOR_LOG=/tmp/tutor-log.jsonl
USER 10001
EXPOSE 8000
# For `docker run`; Azure Container Apps uses its own probes on the same route.
HEALTHCHECK --interval=30s --timeout=3s --start-period=20s \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=2)"]
CMD ["btl", "serve"]
