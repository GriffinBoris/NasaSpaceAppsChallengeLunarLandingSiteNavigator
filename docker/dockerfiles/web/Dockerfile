FROM node:22-bookworm-slim AS frontend-base

WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json ./

RUN --mount=type=cache,target=/root/.npm npm ci

COPY frontend/ ./

FROM frontend-base AS frontend

RUN npm run build

FROM ghcr.io/astral-sh/uv:0.13.5 AS uv

FROM python:3.12-slim-bookworm AS backend

COPY --from=uv /uv /usr/local/bin/uv

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_LINK_MODE=copy \
    PATH="/opt/venv/bin:$PATH" \
    DJANGO_SETTINGS_MODULE=core.settings.dev_docker

RUN apt-get update \
    && apt-get install -y --no-install-recommends libegl1 libgl1 libgomp1 libgfortran5 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml uv.lock README.md ./
COPY backend/pyproject.toml backend/pyproject.toml

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --all-packages --all-groups --no-install-workspace

COPY backend/ backend/
COPY --from=frontend /app/frontend/dist/ frontend/dist/
COPY --chmod=755 docker/entrypoints/web.sh /usr/local/bin/start-web

RUN groupadd --gid 1000 django \
    && useradd --uid 1000 --gid django --create-home django \
    && chown -R django:django /app

USER django
WORKDIR /app/backend

CMD ["start-web"]
