# Velocitype

> The world's fastest typing trainer doesn't run in the cloud, it runs on your
> localhost. Every session gets torn apart by a local AI model, every mistake
> turned into a targeted drill. Made by split keyboard nerds who obsess over every
> layer and homerow mod, for the people who get it. Not a single byte leaves your
> machine. Your keyboard, your data, your speed.

Self-hosted, adaptive touch-typing trainer for split-keyboard enthusiasts —
combining keybr-style **progressive key unlocking** with monkeytype-style session
UX, built for the **Ferris Sweep** and **Corne** (Colemak-DH and QWERTY) from day
one. Every session is analysed **locally**: per-key weaknesses, same-finger
bigrams, rolls and rhythm consistency are computed in code, then a **local** LLM
(Ollama) turns them into plain-language coaching and targeted drills — nothing is
ever sent to an external API unless you explicitly opt in.

- **Website:** <https://one7two99.github.io/velocitype/>
- **Repository:** <https://github.com/one7two99/velocitype>

---

- **Backend:** FastAPI (Python 3.12), async SQLAlchemy + asyncpg, PostgreSQL 16, Redis 7
- **Frontend:** React 18 + TypeScript + Vite, Zustand, TanStack Query, recharts
- **Edge:** Caddy 2 (reverse proxy, security headers, static SPA)
- **Auth:** Argon2id, RS256 JWT in `httpOnly`/`SameSite=Strict` cookies, refresh-token rotation
- **Coaching:** local Ollama LLM by default (nothing leaves your machine); each
  user can optionally switch to **Mistral** (EU cloud) in Settings and enter their
  own API key (stored encrypted). Ollama models can be downloaded from Settings.

## Features

- **Progressive key unlocking (keybr-style).** Start on a small set of keys; the
  next unlocks once every active key holds a configurable share of your target
  speed over a configurable window. Toggle it, tune the threshold/window, or reset
  progression in Preferences. Lessons and AI drills only ever use unlocked keys.
- **Per-key analysis.** A sortable, searchable breakdown — hand, finger, attempts,
  errors, latency and a weakness score — with the keys "needing work" pre-flagged.
- **Bigram, SFB & rhythm analysis.** Bigram stats classify same-finger bigrams
  (SFB), inward/outward rolls and alternation, plus inter-key **rhythm
  consistency** and a **hitch** (hesitation) counter; trigram rolls/redirects are
  derived on read. Same-finger bigrams are highlighted throughout.
- **Targeted drills.** Tick weak keys *or* bigrams in the Analysis tables and
  generate a coach drill aimed at exactly those, with coverage verification and a
  deterministic fallback if the model is unavailable.
- **Board-shaped heatmap.** A Ferris/Corne heatmap coloured by how much each key
  holds you back, with locked keys shown until you unlock them.
- **Local or EU-cloud coach.** Ollama by default; optional per-user Mistral (EU).
  Provider, model and even the coaching prompts are per-user settings.
- **Your data, on your terms.** Sessions and stats live in your own Postgres and
  **sync across your browsers**; **Delete all data** (password-confirmed) really
  removes every row — sessions, keystrokes, per-key and bigram stats, provider
  config (including any stored Mistral key) and prompt overrides.
- **Dashboard & trends.** Key stat cards, an "All Completed Sessions" chart
  (distinct keys, average and peak WPM, accuracy per session), a 30-day trend and
  your personal bests.

## Screenshots

|  |  |
|---|---|
| **Trainer** — distraction-free sessions with a coach-drill banner | **What your coach sees** — weak keys, weak bigrams (SFB-flagged) and rhythm |
| ![Trainer](docs/screenshots/trainer.png) | ![AI-Coach](docs/screenshots/ai-coach.png) |
| **Board-shaped heatmaps** — speed & consistency on your split layout | **Bigram breakdown** — class, error %, rhythm, one-click targeted drills |
| ![Heatmaps](docs/screenshots/heatmaps.png) | ![Analysis — bigram breakdown](docs/screenshots/analysis-bigram.png) |
| **Dashboard** — per-session trends, 30-day trend and personal bests | **Settings** — layout, session goal and progressive key unlocking |
| ![Dashboard](docs/screenshots/dashboard.png) | ![Settings — training](docs/screenshots/settings-training.png) |

> Live site: <https://one7two99.github.io/velocitype/>

## Quick start

Requires Docker (Compose v2) and OpenSSL.

```bash
git clone https://github.com/one7two99/velocitype.git
cd velocitype
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
keyboard layouts (Ferris Sweep Colemak-DH + QWERTY, Corne Colemak-DH + QWERTY).
The `frontend` service builds the SPA into `frontend/dist`, which Caddy serves.

## Architecture

```
Internet ─▶ Caddy (8080/8443)
              ├─ /api/*  ─▶ FastAPI (8000) ─▶ PostgreSQL (5432)
              │                             └▶ Redis (6379)
              └─ /*      ─▶ SPA (frontend/dist)
```

Only Caddy is exposed to the host in production; Postgres/Redis stay on the
internal Docker network. The app connects to Postgres as a least-privilege
`velocitype_app` role (provisioned by `db/init/01-app-role.sh`).

## Development

**Backend tests** (need a reachable Postgres + Redis — the dev override exposes
them on `localhost:5432` / `localhost:6379`):

```bash
cd backend
pip install -r requirements.txt
TEST_DATABASE_URL=postgresql+asyncpg://velocitype_app:REDACTED@localhost:5432/velocitype \
REDIS_URL=redis://:REDACTED@localhost:6379/15 \
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

## AI Coach (local Ollama, optional Mistral EU)

The **AI-Coach** page generates a coaching analysis and targeted practice drills
from your stats. By default this uses a **local** [Ollama](https://ollama.com)
model — nothing is sent to any external LLM API. Each user can instead switch to
**Mistral** (a European provider, chosen for EU data protection over US/Chinese
frontier labs) in Settings and supply their own API key, which is stored
encrypted. Local stays the default.

- A bundled `ollama` service runs the model; a one-shot `ollama-pull` fetches
  `OLLAMA_MODEL` (default `qwen3.5:4b`, ~3.4 GB) into a volume on first `up`.
  Additional models can be browsed and downloaded from **Settings → AI** — no
  shell required.
- The coach is grounded in the metrics computed in code: it calls out weak keys,
  weak **same-finger bigrams**, rhythm **hitches** and awkward **redirects**
  without inventing numbers, and drills can target specific keys or letter pairs.
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
`POST /api/coach/analyze`, `POST /api/coach/drill` (accepts optional `focus_keys`
/ `focus_bigrams`), `GET /api/coach/metrics` (includes `weak_bigrams` +
`trigram_rollup`), and `GET /api/stats/ngrams` (per-bigram table with class +
consistency).

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

The core differentiator lives in `backend/app/engine/`:

- `adaptive.py` — a pure, unit-tested weighted key-pool scorer
  (`w_error·error_rate + w_latency·norm_latency + w_recency·recency`) that surfaces
  the weakest keys and generates lessons weighting them ~3× within realistic
  pseudo-words, honouring the set of currently unlocked keys.
- `ngrams.py` — pure bigram/trigram classification (SFB, rolls, alternation,
  redirects) and n-gram weakness scoring (SFBs get a score bonus), feeding both the
  Analysis tables and what the coach sees.

Bigram statistics are persisted in `ngram_stats`; a one-off backfill
(`python -m app.db.backfill_ngrams`) seeds existing users from their retained
keystrokes.

## Versioning

Releases follow [Semantic Versioning](https://semver.org) against a declared
public surface; see [CHANGELOG.md](./CHANGELOG.md). Current release: **0.32.0**.

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

The full product spec is in `Velocitype_MVP_BriefingPack.md`.
