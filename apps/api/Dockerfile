# syntax=docker/dockerfile:1.7
# Saathi API: multi-stage (uv builder -> python:3.12-slim runtime), non-root uid 10001.
# Target image < 200 MB. TODO(ci): pin both base images by digest (@sha256:...) and let
# Dependabot bump them.

ARG PYTHON_IMAGE=python:3.12-slim-bookworm
ARG UV_IMAGE=ghcr.io/astral-sh/uv:0.9

FROM ${UV_IMAGE} AS uv

# ---------------------------------------------------------------- builder
FROM ${PYTHON_IMAGE} AS builder
COPY --from=uv /uv /uvx /bin/
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/app/.venv
WORKDIR /app
# Dependency layer: cached until uv.lock / pyproject.toml change.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-dev --no-install-project
COPY pyproject.toml uv.lock README.md alembic.ini ./
COPY src ./src
COPY migrations ./migrations
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-editable

# ---------------------------------------------------------------- runtime
FROM ${PYTHON_IMAGE} AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH" \
    PORT=8000 \
    WEB_CONCURRENCY=1
RUN groupadd --system --gid 10001 saathi \
 && useradd --system --uid 10001 --gid saathi --no-create-home --shell /usr/sbin/nologin saathi
WORKDIR /app
COPY --from=builder --chown=10001:10001 /app/.venv /app/.venv
COPY --from=builder --chown=10001:10001 /app/alembic.ini /app/alembic.ini
COPY --from=builder --chown=10001:10001 /app/migrations /app/migrations
USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD ["python", "-m", "saathi_api.healthcheck"]
# Render injects PORT. 1 worker fits the 512 MB free instance.
CMD ["sh", "-c", "exec uvicorn saathi_api.main:app --host 0.0.0.0 --port ${PORT} --workers ${WEB_CONCURRENCY} --proxy-headers --forwarded-allow-ips='*' --no-server-header"]
