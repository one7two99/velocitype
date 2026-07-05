# Velocitype — Architecture Overview

_Factual summary for external architecture analysis. Version `0.26.1` (see `backend/app/version.py` == `frontend/package.json`). All statements below are taken from the code in this repository._

## 1. Overview

- **Purpose:** Self-hosted, adaptive touch-typing trainer for split keyboards (Ferris Sweep / Corne, Colemak-DH & QWERTY). Combines keybr-style adaptive per-key learning with monkeytype-style session UX. AI coaching (analysis + drill word lists) runs against a **local Ollama** model by default, with an optional **Mistral (EU cloud)** provider per user.
- **Languages:** Python 3.12 (backend), TypeScript (frontend).
- **Frameworks / key libs:**
  - Backend: FastAPI, async SQLAlchemy 2.0 + asyncpg, Alembic, Pydantic v2 / pydantic-settings, PyJWT (RS256), passlib[argon2], httpx, redis, `cryptography` (Fernet).
  - Frontend: React 18 + Vite 6, TypeScript, Zustand (state), TanStack Query (data), recharts (charts), react-router.
- **Folder layout:**
  - `backend/app/` — `routers/` (HTTP endpoints), `services/` (business logic incl. LLM adapters), `engine/` (pure adaptive algorithm + layout definitions), `models/` (SQLAlchemy tables), `schemas/` (Pydantic DTOs), `auth/` (JWT/cookies/rate-limit/password), `db/` (session, seed, wait-for-db, redis). `backend/alembic/` — migrations.
  - `frontend/src/` — `pages/`, `components/` (incl. `TypingEngine/`, `FerrisHeatmap/`), `hooks/` (`useTypingEngine.ts`), `stores/`, `api/` (client + endpoints + types).
  - `caddy/` — reverse proxy config. `db/init/` — Postgres role bootstrap. `secrets/` — JWT PEM keys + `keygen.sh` (gitignored keys; **excluded from the zip**).

## 2. Docker stack

Two compose files: `docker-compose.yml` (base, `name: velocitype`) and `docker-compose.override.yml` (dev overrides, auto-applied). Single user-defined bridge network **`velocitype_net`**; only Caddy publishes ports to the host.

| Service | Image | Ports (host→cont) | Volumes | Depends on | Role |
|---|---|---|---|---|---|
| **caddy** | `caddy:2-alpine` | `${HTTP_PORT:-80}:80`, `${HTTPS_PORT:-443}:443` (dev `.env`: 8080/8443) | `./caddy/Caddyfile:ro`, `./frontend/dist:/srv:ro`, `caddy_data`, `caddy_config` | api (started), frontend (completed) | Reverse proxy: serves SPA from `/srv`, proxies `/api/*` → `api:8000`; sets security headers/CSP. |
| **frontend** | built from `./frontend/Dockerfile` (`node:22-alpine`) | — | `./frontend/dist:/app/dist` | — | **One-shot builder**: runs `npm run build` into the `dist` bind mount that Caddy serves, then exits. |
| **api** | built from `./backend/Dockerfile` (`python:3.12-slim`) | override: `8000:8000` | (dev) mounts `./backend/app`, `./backend/alembic` read-only | db (healthy), redis (healthy), ollama (healthy) | FastAPI app. Prod entrypoint stages JWT secrets via `gosu`, drops to `appuser`, runs uvicorn. Dev command waits for DB → `alembic upgrade head` → `app.db.seed` → uvicorn `--reload`. |
| **db** | `postgres:16-alpine` | override: `5432:5432` | `pg_data`, `./db/init:/docker-entrypoint-initdb.d:ro` | — | PostgreSQL. Superuser `postgres`; init script provisions a least-privilege app role. |
| **redis** | `redis:7-alpine` | override: `6379:6379` | `redis_data` | — | Redis (password-protected, appendonly). Used for per-IP fixed-window rate limiting (`app/auth/rate_limit.py`). Refresh tokens are stored in Postgres, not Redis. |
| **ollama** | `ollama/ollama:latest` | — | `ollama_data` | — | Local LLM server (`:11434`, internal). Optional GPU block commented in compose. |
| **ollama-pull** | `ollama/ollama:latest` | — | — | ollama (healthy) | One-shot: `ollama pull "$OLLAMA_MODEL"` (default `qwen3.5:4b`), then exits. |

Named volumes: `caddy_data`, `caddy_config`, `pg_data`, `redis_data`, `ollama_data`.

## 3. Ollama / LLM binding

- **Adapter:** `backend/app/services/ollama.py`.
  - `generate(prompt, system=None, *, model=None, num_predict=300)` → `POST {OLLAMA_BASE_URL}/api/generate`, `stream=False`. Options set: `temperature=0.8`, `num_predict` (caps output length), `repeat_penalty=1.4`, `top_p=0.9`, and `think=False` (disables qwen3 reasoning trace). A `<think>…</think>` block is stripped via regex `_clean()`. Raises `OllamaError` on failure/empty response.
  - `status(model)` → `GET /api/tags`, checks reachability + whether the target model is installed.
  - `list_models()` → `GET /api/tags`. `pull_model(name)` → streaming `POST /api/pull` (NDJSON), writes progress into an in-memory dict `_PULLS` (single uvicorn worker).
- **Provider facade:** `backend/app/services/llm.py` — `LLMConfig(provider, model, api_key)`; `generate/status/list_models` dispatch to Ollama or Mistral. Coach code depends only on this facade. Provider errors are wrapped as `LLMError`.
- **Mistral (optional):** `backend/app/services/mistral.py` — `POST {MISTRAL_BASE_URL}/v1/chat/completions` (`temperature=0.6`, `max_tokens`), reads `choices[0].message.content`; `list_models` via `GET /v1/models`. Base `https://api.mistral.ai`; default model `mistral-small-latest` (config).
- **Callers:** `backend/app/services/coach.py` — `analyze()` (`max_tokens=280`) and `drill()` (`max_tokens=160`) call `llm.generate(cfg, …)`; `status()` calls `llm.status(cfg)`. Per-user provider/model/key resolved by `coach.get_ai_config()`.
- **Model config:** default model `qwen3.5:4b` (`Settings.ollama_model` in `backend/app/config.py`; also `OLLAMA_MODEL` in compose). Timeout `ollama_timeout_s=240.0`.
- **Modelfile:** **none.** No custom Ollama `Modelfile` exists; the model is obtained via `ollama pull qwen3.5:4b` (the `ollama-pull` service). Per-user model choice + downloading additional models is done at runtime via the API (see §6).

## 4. Typing-metric data model

**All typing metrics are computed in code — never by the LLM.** The LLM only receives a compact stats summary (for prose analysis) and focus keys (for drills).

- **Session-level metrics — computed client-side** in `frontend/src/hooks/useTypingEngine.ts`:
  - `wpmRaw = correctChars / 5 / minutes`
  - `wpmNet = max(0, wpmRaw − errorWordCount / minutes)`
  - `accuracy = correctChars / totalChars`
  - `consistency = 1 − CV` (coefficient of variation of per-second gross-WPM samples; `Math.sqrt(variance)/mean`)
  - Sent via `POST /api/sessions/{id}/complete` and persisted in the **`sessions`** table (`wpm_raw`, `wpm_net`, `accuracy`, `consistency`, `duration_s`, `word_count`, `mode`, timestamps).
- **Raw keystrokes:** `POST /api/sessions/{id}/keystrokes` stores each event in **`keystrokes`** (`ts_offset_ms`, `expected_char`, `actual_char`, `correct`, `hold_ms`).
- **Per-key aggregation — computed server-side** in `backend/app/services/key_stats.py` (`_per_key_aggregates`, `apply_keystrokes`) and stored in **`key_stats`** (composite PK `user_id, layout_id, character`): `attempts`, `errors`, `avg_latency_ms`, `latency_n`, `latency_sq_sum` (running spread), `last_session_seq` (recency). Latency = inter-key interval (or `hold_ms` when present).
- **Derived per-key values:** per-key consistency = `1 − CV` of latencies (`adaptive.latency_consistency`); per-key WPM = `12000 / avg_latency_ms` (frontend `FerrisHeatmap`/`AnalysisPage`). The adaptive weakness score (`backend/app/engine/adaptive.py`) = `0.5·error_rate + 0.3·normalized_latency + 0.2·recency_penalty`.
- **Bigrams / trigrams / rhythm:** **not** captured or persisted as metrics. N-grams appear only as *shells* for drill generation (`COMMON_BIGRAM_SHELLS` / `COMMON_TRIGRAM_SHELLS` in `adaptive.py`). "Rhythm" is represented indirectly by per-key latency spread (consistency), not as an explicit n-gram timing model.
- **Schema / migrations:** SQLAlchemy models in `backend/app/models/`; Alembic migrations `0001_initial` → `0004_user_ai_config`. Tables: `users`, `sessions`, `keystrokes`, `key_stats`, `refresh_tokens`, `api_keys`, `layouts`, `user_prompts`, `user_ai_config`.

## 5. Word-list (drill) generation

- **Location:** `backend/app/services/coach.py::drill()`, with a deterministic fallback `backend/app/engine/adaptive.py::generate_lesson()`.
- **Focus selection (input):** either the adaptive top-weakest keys (`adaptive.weakest_keys`, n=5) **or** explicit `focus_keys` supplied by the client (from the per-key Analysis table), validated against the active layout. The focus string is annotated with per-key severity, e.g. `q (50% errors, ~33 wpm)` (`_annotate_focus`).
- **Prompt:** user-overridable templates in `DEFAULT_PROMPTS` (`drill_system`, `drill_user`), with `{{focus}}` substituted (`_inject`). Effective prompts resolved per user via `get_effective_prompts` (overrides stored in `user_prompts`). Default `drill_system` instructs the model to output **only** drill words.
- **Input format to the model:** natural-language instruction + the focus keys (as annotated text). **No structured/JSON input.**
- **Output format:** **plain space-separated words — not JSON.** No JSON schema is used for drills (nor for analysis, which returns prose). The raw output is sanitized to typeable words for the active layout (`_sanitize_lesson`) and verified to actually over-represent the focus keys (`_covers_focus`); on failure it retries once, else falls back to the deterministic generator. Returned as `CoachDrill` (`lesson`, `word_count`, `weak_keys`, `source` = provider name or `"fallback"`, `model`).

## 6. API surface (selected)

All under `/api`; session auth via httpOnly cookies unless noted. Prefixes from `backend/app/routers/`.

**Auth** (`/api/auth`): `POST /register`, `POST /login`, `POST /refresh`, `POST /logout`, `GET /me`, `PATCH /password`, `PATCH /email`, `DELETE /me`.

**Sessions** (`/api/sessions`): `POST /start`, `POST /{id}/complete`, `POST /{id}/keystrokes`, `GET ""` (history), `GET /{id}`.

**Stats** (`/api/stats`): `GET /overview`, `GET /keys` (per-key heatmap data), `GET /progress`.

**Lessons** (`/api/lessons`): `GET /next` (adaptive lesson), `GET /layouts`.

**Coach / AI** (`/api/coach`): `GET /status` (active provider/model + readiness), `GET|PUT /config` (per-user provider/model/Mistral key; key stored encrypted, never returned), `GET /models` (list provider models), `POST /models/pull` + `GET /models/pull` (download an Ollama model, async + poll), `GET|PUT /prompts` (editable prompts), `GET /metrics` (stats the coach sees), `POST /analyze` (prose analysis), `POST /drill` (word-list generation; optional `focus_keys`).

**MCP** (`/api/mcp`): `GET /summary`, `GET /recommendations`, `POST /keys`, `GET /keys`, `DELETE /keys/{id}` (long-lived API keys for external integrations).

**Health/meta:** `GET /api/health`, `GET /api/version` (in `backend/app/main.py`).

## 7. Open items / TODO / FIXME

- **No `TODO`/`FIXME`/`XXX`/`HACK` markers** are present in `backend/app` or `frontend/src`.
- Observations from the code (not code-marked, factual):
  - **Ollama model-pull progress is in-memory** (`_PULLS` in `ollama.py`), valid only for a single uvicorn worker; progress is lost on restart (comment notes this).
  - **Mistral model choice is UI-curated** to two entries (`mistral-small-latest` → "Mistral Small 4", `mistral-medium-latest` → "Mistral Medium 3.5") in `frontend/src/components/AiProvider.tsx`; the `-latest` aliases resolve to those versions currently.
  - **CSP** in `caddy/Caddyfile` is intentionally strict/self-only ("loosen as the frontend's asset needs are known").
  - **Session `mode` comment** in `models/session.py` lists `adaptive|fixed_text|custom` but `coach_drill` is also used in practice.
  - The **git repository/remote is still named `adi-infra/typeforge`** although the product was rebranded to Velocitype; CHANGELOG compare-URLs point there intentionally.
