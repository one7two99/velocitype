FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# System deps: libpq not required for asyncpg; build tools kept minimal.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl gosu \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -r requirements.txt

# Application code
COPY alembic.ini .
COPY alembic ./alembic
COPY app ./app
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

# Create the unprivileged runtime user. The entrypoint starts as root only to
# stage the Docker-secret JWT keys readable (file secrets inherit host perms),
# then drops to this user via gosu to run the server.
RUN useradd --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /app

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --start-period=30s --retries=5 \
    CMD curl -fsS http://localhost:8000/api/health || exit 1

ENTRYPOINT ["./entrypoint.sh"]
