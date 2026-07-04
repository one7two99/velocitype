#!/bin/sh
# Production entrypoint. Starts as root, stages secrets for the unprivileged
# user, runs migrations + seed, then drops privileges to serve.
# The dev override replaces this command with a --reload variant.
set -e

APP_USER=appuser
KEYDIR=/app/runtime-secrets

# Docker file-based secrets inherit the host file's ownership/permissions, which
# are typically owner-only (0600) and not readable by an arbitrary container
# uid. Copy them to an app-owned, tightly-scoped location.
if [ -r /run/secrets/jwt_private ]; then
    mkdir -p "$KEYDIR"
    cp /run/secrets/jwt_private "$KEYDIR/jwt_private"
    cp /run/secrets/jwt_public "$KEYDIR/jwt_public"
    chown -R "$APP_USER:$APP_USER" "$KEYDIR"
    chmod 400 "$KEYDIR/jwt_private"
    chmod 444 "$KEYDIR/jwt_public"
    export JWT_PRIVATE_KEY_PATH="$KEYDIR/jwt_private"
    export JWT_PUBLIC_KEY_PATH="$KEYDIR/jwt_public"
fi

gosu "$APP_USER" python -m app.db.wait_for_db
echo "Running migrations ..."
gosu "$APP_USER" alembic upgrade head
echo "Seeding layout definitions ..."
gosu "$APP_USER" python -m app.db.seed
echo "Starting API ..."
exec gosu "$APP_USER" uvicorn app.main:app --host 0.0.0.0 --port 8000
