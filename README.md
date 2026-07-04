# TypeForge

Self-hosted, adaptive touch-typing trainer for split-keyboard enthusiasts —
combining keybr-style adaptive key learning with monkeytype-style session UX,
built for the Ferris Sweep (Colemak-DH) from day one.

- **Backend:** FastAPI (Python 3.12), async SQLAlchemy + asyncpg, PostgreSQL 16, Redis 7
- **Frontend:** React 18 + TypeScript + Vite, Zustand, TanStack Query, recharts
- **Edge:** Caddy 2 (reverse proxy, security headers, static SPA)
- **Auth:** Argon2id, RS256 JWT in `httpOnly`/`SameSite=Strict` cookies, refresh-token rotation
- **Coaching:** local Ollama LLM (no external API) for analysis + drill generation

## Quick start

Requires Docker (Compose v2) and OpenSSL.

```bash
cp .env.example .env
./secrets/keygen.sh          # generates the RS256 JWT keypair into secrets/
docker compose up --build
```

Then open **http://localhost:8080/** and register an account (there is no seeded
user; the first registration logs you in). The API docs are at
`http://localhost:8080/api/docs`.

> Ports default to **8080 (HTTP)** / **8443 (HTTPS)** via `.env` to avoid clashing
> with anything on 80/443. Use `http://` locally — the HTTPS port uses Caddy's
> self-signed cert. Change `SITE_ADDRESS` / `HTTP_PORT` / `HTTPS_PORT` for a real
> deployment.

On startup the API waits for the database, runs Alembic migrations, and seeds the
keyboard layouts (Ferris Sweep Colemak-DH + QWERTY). The `frontend` service builds
the SPA into `frontend/dist`, which Caddy serves.

## Architecture

```
Internet ─▶ Caddy (8080/8443)
              ├─ /api/*  ─▶ FastAPI (8000) ─▶ PostgreSQL (5432)
              │                             └▶ Redis (6379)
              └─ /*      ─▶ SPA (frontend/dist)
```

Only Caddy is exposed to the host in production; Postgres/Redis stay on the
internal Docker network. The app connects to Postgres as a least-privilege
`typeforge_app` role (provisioned by `db/init/01-app-role.sh`).

## Development

**Backend tests** (need a reachable Postgres + Redis — the dev override exposes
them on `localhost:5432` / `localhost:6379`):

```bash
cd backend
pip install -r requirements.txt
TEST_DATABASE_URL=postgresql+asyncpg://typeforge_app:dev_app_change_me@localhost:5432/typeforge \
REDIS_URL=redis://:dev_redis_change_me@localhost:6379/15 \
pytest
```

The suite creates its own tables and ephemeral JWT keys; if the test database is
unreachable, integration tests skip rather than fail.

**Frontend dev server** (hot reload; proxies `/api` to the Dockerized backend on
:8080):

```bash
cd frontend
npm install
npm run dev            # http://localhost:5173
npm run build          # type-check (tsc) + production bundle into dist/
```

## AI Coach (local Ollama)

The **Coach** page generates a coaching analysis and targeted practice drills from
your stats using a **local** [Ollama](https://ollama.com) model — nothing is sent
to any external LLM API.

- A bundled `ollama` service runs the model; a one-shot `ollama-pull` fetches
  `OLLAMA_MODEL` (default `qwen3.5:4b`, ~3.4 GB) into a volume on first `up`.
- The app stays fully usable while the model downloads; coaching shows a
  "downloading" state, and drill generation falls back to the deterministic
  adaptive generator if the model is unavailable.
- **CPU note:** without a GPU, generation is slow (a few tokens/sec) — an
  analysis can take up to a minute or two. Configure a GPU by uncommenting the
  `deploy.resources` block on the `ollama` service in `docker-compose.yml`.
- To use an existing host Ollama instead of the bundled service, set
  `OLLAMA_BASE_URL=http://host.docker.internal:11434` (the host must listen on
  `0.0.0.0`, i.e. `OLLAMA_HOST=0.0.0.0 ollama serve`).

Endpoints (session-authenticated): `GET /api/coach/status`,
`POST /api/coach/analyze`, `POST /api/coach/drill`.

## Continuous integration

`.github/workflows/ci.yml` runs on every push / PR:

- **backend** — `pytest` against Postgres+Redis service containers, then `pip-audit`
- **frontend** — `npm ci`, `npm run build` (incl. type-check), then `npm audit`

## Project layout

```
backend/     FastAPI app (routers, models, schemas, engine, services), Alembic, tests
frontend/    React SPA (components, hooks, pages, stores, api client)
caddy/       Caddyfile (reverse proxy + security headers)
db/init/     least-privilege role provisioning
secrets/     keygen.sh (JWT keypair; *.pem gitignored)
```

## Adaptive engine

The core differentiator lives in `backend/app/engine/adaptive.py` — a pure,
unit-tested weighted key-pool scorer (`w_error·error_rate + w_latency·norm_latency
+ w_recency·recency`) that surfaces the weakest keys and generates lessons
weighting them ~3× within realistic bigrams/trigrams.

## Versioning

Releases follow [Semantic Versioning](https://semver.org) against a declared
public surface; see [CHANGELOG.md](./CHANGELOG.md).

**Public surface** (what the version speaks about):

- the HTTP REST API under `/api/*` (routes and response fields)
- the MCP contract (`/api/mcp/*` + API-key auth)
- the deployment contract: `.env` variables, `docker-compose.yml` service names,
  and the PostgreSQL schema

**Bump rules**

- **MAJOR** — a backward-incompatible change to the public surface: removing or
  renaming a route, response field, env var, or compose service; a DB migration
  that isn't backward-safe; or a change to the auth/cookie contract.
- **MINOR** — backward-compatible additions: new routes, new optional fields or
  request params, new features, or additive DB migrations (auto-applied on
  startup).
- **PATCH** — backward-compatible bug fixes with no public-surface change.

**Pre-1.0 caveat.** While at `0.x`, per SemVer §4 the public surface is not yet
guaranteed stable: minor releases may include additive DB migrations, and
behaviour may still shift. We nonetheless apply the rules above consistently.
**1.0.0** will be cut once the REST API and DB schema are considered stable
enough to promise compatibility.

**Single source of version.** `backend/app/version.py` (`__version__`) and
`frontend/package.json` (`version`) must match — CI fails otherwise. The backend
reports it at `GET /api/version` and in `GET /api/health`; the frontend shows it
in the top-bar badge.

**Release process.** Bump both version files, add a `CHANGELOG.md` entry and a
`frontend/src/releaseNotes.ts` entry (the in-app release notes), then tag
`vX.Y.Z`.

The full product spec is in `TypeForge_MVP_BriefingPack.md`.
