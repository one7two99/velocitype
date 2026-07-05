#!/bin/sh
# Runs once, on first cluster init, as the postgres superuser.
# Creates the least-privilege application role and its database, so the API
# never connects as a superuser (Section 2: least-privilege velocitype_app role).
set -e

: "${APP_DB:?APP_DB must be set}"
: "${APP_USER:?APP_USER must be set}"
: "${APP_PASSWORD:?APP_PASSWORD must be set}"

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname postgres <<-SQL
    -- Application login role: no superuser, no createrole, no createdb.
    DO \$\$
    BEGIN
        IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '${APP_USER}') THEN
            CREATE ROLE ${APP_USER} LOGIN PASSWORD '${APP_PASSWORD}'
                NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT;
        END IF;
    END
    \$\$;

    -- The app owns its own database (needed for Alembic DDL) but nothing else in
    -- the cluster. Ownership is scoped strictly to this database.
    SELECT 'CREATE DATABASE ${APP_DB} OWNER ${APP_USER}'
    WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '${APP_DB}')\gexec
SQL

# Lock down the public schema in the app database and grant it to the app role.
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$APP_DB" <<-SQL
    REVOKE ALL ON SCHEMA public FROM PUBLIC;
    GRANT ALL ON SCHEMA public TO ${APP_USER};
    ALTER SCHEMA public OWNER TO ${APP_USER};
SQL

echo "Provisioned least-privilege role '${APP_USER}' owning database '${APP_DB}'."
