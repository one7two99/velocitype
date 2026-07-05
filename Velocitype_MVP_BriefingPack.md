# Velocitype — MVP Briefing Pack
**For implementation with Claude Code**
Version 1.0 | June 2026

---

## Mission

> Velocitype — the world's fastest typing trainer doesn't run in the cloud, it runs on your localhost. Every session gets torn apart by a local AI model, every mistake turned into a targeted drill. Made by split keyboard nerds who obsess over every layer and homerow mod, for the people who get it. Not a single byte leaves your machine. Your keyboard, your data, your speed.

Build the world's best touch typing trainer for serious keyboard enthusiasts on split keyboards. Velocitype combines the adaptive key-learning intelligence of keybr.com with the clean, competitive session UX of monkeytype.com — self-hosted, privacy-respecting, and built for the Ferris Sweep from day one.

---

## 1. Architecture Overview

### Stack

| Layer | Technology | Rationale |
|---|---|---|
| Frontend | React 18 + TypeScript + Vite | Fast HMR, type safety, component isolation |
| Backend API | FastAPI (Python 3.12) | Async, OpenAPI auto-docs, strong typing via Pydantic v2 |
| Database | PostgreSQL 16 | Reliable, relational session/metric storage |
| Cache / PubSub | Redis 7 | Sub-millisecond keystroke buffer, session state |
| Reverse Proxy | Caddy 2 | Automatic HTTPS, minimal config |
| Container Runtime | Docker Compose v2 | Single-command deployment |

### Service Topology

```
Internet
    │
  Caddy (443/80)
    │
    ├── /api/*  ──→  FastAPI (8000)
    │                    │
    │               PostgreSQL (5432)
    │               Redis (6379)
    │
    └── /*      ──→  Vite Static Build (served by Caddy)
```

All services on an internal Docker network `velocitype_net`. Only Caddy exposes ports to host.

---

## 2. Security Requirements (non-negotiable)

- **Auth**: JWT (RS256, asymmetric keys) with refresh token rotation. Tokens stored in `httpOnly` + `SameSite=Strict` cookies — never `localStorage`.
- **Passwords**: Argon2id hashing via `passlib`. Minimum 12 chars enforced.
- **Rate limiting**: Per-IP via Redis on all auth endpoints (5 req/min login, 3 req/min register).
- **CORS**: Explicit allowlist, no wildcard in production.
- **Headers**: Caddy sets `Content-Security-Policy`, `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin`.
- **Input validation**: All API inputs validated by Pydantic v2 models. No raw SQL — SQLAlchemy ORM only.
- **Secrets**: All secrets via environment variables. `.env` in `.gitignore`. `docker-compose.yml` references `${VAR}` only.
- **DB**: PostgreSQL not exposed outside Docker network. `postgres` superuser password required, app uses a least-privilege `velocitype_app` role.
- **Dependencies**: `pip-audit` and `npm audit` in CI pre-commit hook.

---

## 3. Data Models

### `users`
```sql
id            UUID PRIMARY KEY DEFAULT gen_random_uuid()
username      VARCHAR(32) UNIQUE NOT NULL
email         VARCHAR(255) UNIQUE NOT NULL
password_hash TEXT NOT NULL
created_at    TIMESTAMPTZ DEFAULT now()
last_login    TIMESTAMPTZ
is_active     BOOLEAN DEFAULT true
```

### `sessions`
```sql
id              UUID PRIMARY KEY DEFAULT gen_random_uuid()
user_id         UUID REFERENCES users(id) ON DELETE CASCADE
layout_id       VARCHAR(64) NOT NULL   -- e.g. "ferris_sweep_colemak_dh"
mode            VARCHAR(32) NOT NULL   -- "adaptive", "fixed_text", "custom"
duration_s      INTEGER                -- for timed modes
word_count      INTEGER                -- for word-count modes
started_at      TIMESTAMPTZ DEFAULT now()
completed_at    TIMESTAMPTZ
wpm_raw         NUMERIC(6,2)
wpm_net         NUMERIC(6,2)
accuracy        NUMERIC(5,4)           -- 0.0–1.0
consistency     NUMERIC(5,4)           -- stddev-derived, lower = better
```

### `keystrokes`
```sql
id            BIGSERIAL PRIMARY KEY
session_id    UUID REFERENCES sessions(id) ON DELETE CASCADE
ts_offset_ms  INTEGER NOT NULL           -- ms since session start
expected_char TEXT NOT NULL
actual_char   TEXT NOT NULL
correct       BOOLEAN NOT NULL
hold_ms       INTEGER                    -- key hold duration
```

### `key_stats`  *(aggregated, updated after each session)*
```sql
user_id       UUID REFERENCES users(id) ON DELETE CASCADE
layout_id     VARCHAR(64)
character     VARCHAR(8)
attempts      INTEGER DEFAULT 0
errors        INTEGER DEFAULT 0
avg_latency_ms NUMERIC(8,2)
updated_at    TIMESTAMPTZ DEFAULT now()
PRIMARY KEY (user_id, layout_id, character)
```

### `refresh_tokens`
```sql
id          UUID PRIMARY KEY
user_id     UUID REFERENCES users(id) ON DELETE CASCADE
token_hash  TEXT NOT NULL
expires_at  TIMESTAMPTZ NOT NULL
revoked     BOOLEAN DEFAULT false
created_at  TIMESTAMPTZ DEFAULT now()
```

---

## 4. API Endpoints

### Auth
```
POST   /api/auth/register
POST   /api/auth/login
POST   /api/auth/logout
POST   /api/auth/refresh
GET    /api/auth/me
```

### Sessions
```
POST   /api/sessions/start          → session_id, lesson content
POST   /api/sessions/{id}/complete  → final metrics
GET    /api/sessions/{id}           → session detail
GET    /api/sessions                → paginated history (user-scoped)
```

### Keystrokes  *(optional real-time path)*
```
POST   /api/sessions/{id}/keystrokes  → bulk keystroke batch (sent on complete)
```

### Stats
```
GET    /api/stats/overview            → WPM trend, accuracy trend, top errors
GET    /api/stats/keys                → per-key error rate + latency heatmap data
GET    /api/stats/progress?days=30    → time-series WPM/accuracy
```

### Lessons
```
GET    /api/lessons/next              → adaptive next lesson for user
GET    /api/lessons/layouts           → available keyboard layouts
```

### MCP / External API
```
GET    /api/mcp/summary               → structured JSON: user stats snapshot for LLM consumption
GET    /api/mcp/recommendations       → AI-ready prompt payload for coaching analysis
```
*MCP endpoints are authenticated via a long-lived API key (separate from session JWTs), generated per-user in settings. This is the integration point for Claude Web.*

---

## 5. Adaptive Learning Engine

This is Velocitype's core differentiator. Implemented as a pure Python module `engine/adaptive.py`.

### Algorithm: Weighted Key Pool

Each key maintains a **score** derived from:

```
score(k) = w_error × error_rate(k)
         + w_latency × normalized_latency(k)
         + w_recency × recency_penalty(k)
```

Default weights: `w_error=0.5`, `w_latency=0.3`, `w_recency=0.2`

- **error_rate**: errors / attempts over last N sessions (sliding window, N=10)
- **normalized_latency**: key latency relative to user's personal median (so fast typists aren't penalized for absolute speed)
- **recency_penalty**: keys not seen in >3 sessions get a small boost to prevent neglect

### Lesson Generation

1. Identify the user's **5 weakest keys** by score.
2. Build a lesson corpus weighting weak keys at 3× frequency.
3. Insert weak keys into bigrams and common trigrams (not random strings) for realistic muscle memory.
4. Minimum lesson length: 40 words or 60 seconds of estimated typing time, whichever is longer.
5. **Graduation**: a key exits the weak pool when error_rate < 3% AND avg_latency < 1.3× user median for 3 consecutive sessions.

### Ferris Sweep Layout Definition

```json
{
  "id": "ferris_sweep_colemak_dh",
  "name": "Ferris Sweep — Colemak-DH",
  "hand_map": {
    "q":"L","w":"L","f":"L","p":"L","b":"L",
    "a":"L","r":"L","s":"L","t":"L","g":"L",
    "z":"L","x":"L","c":"L","d":"L","v":"L",
    "j":"R","l":"R","u":"R","y":"R",";":"R",
    "m":"R","n":"R","e":"R","i":"R","o":"R",
    "k":"R","h":"R",",":"R",".":"R","/":"R"
  },
  "finger_map": {
    "q":"LP","w":"LR","f":"LM","p":"LI","b":"LI",
    "a":"LP","r":"LR","s":"LM","t":"LI","g":"LI",
    "z":"LP","x":"LR","c":"LM","d":"LI","v":"LI",
    "j":"RI","l":"RI","u":"RM","y":"RR",";":"RP",
    "m":"RI","n":"RI","e":"RM","i":"RR","o":"RP",
    "k":"RI","h":"RI",",":"RM",".":"RR","/":"RP"
  },
  "thumb_keys": ["space","backspace","enter","shift","layer"]
}
```
*(LP=Left Pinky, LR=Left Ring, LM=Left Middle, LI=Left Index, RI=Right Index, etc.)*

Additional layout shipped at MVP: **QWERTY standard** (for onboarding / baseline comparison).

---

## 6. Frontend — Screen Inventory

### 6.1 Typing Screen  *(primary view)*

The screen a user sees 90% of the time. Must be **zero-latency** perceived.

**Layout:**
```
┌─────────────────────────────────────────────────────┐
│  [WPM: --]   [ACC: --]   [TIME: 0:00]   [ESC: quit] │
├─────────────────────────────────────────────────────┤
│                                                     │
│   the quick brown fox jumps over the lazy dog       │
│   ████████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░     │
│              ^                                      │
│   [typed correctly in green / errors in red/shake]  │
│                                                     │
├─────────────────────────────────────────────────────┤
│  [keyboard heatmap — 36 key Ferris Sweep visual]    │
└─────────────────────────────────────────────────────┘
```

Key UX requirements:
- Cursor is a blinking beam (not block) — caret style.
- Incorrect keystrokes: character turns red + subtle horizontal shake animation (CSS only, no JS jank).
- Word-level undo: `Backspace` corrects within current word only (no going back to previous words — monkeytype behavior).
- Live WPM updates every 500ms using a rolling 10-second window (keybr approach).
- Caret never obscured by text.
- **Restart**: `Tab` + `Enter` = instant new lesson, no mouse required.
- On completion: smooth slide-up results panel (no page navigation).

### 6.2 Results Panel  *(post-session overlay)*

```
┌─────────────────────────────────────────────┐
│  Session Complete                           │
│                                             │
│  WPM     ACC     CONSISTENCY  TIME          │
│   82     97.3%      94.1%     1:00          │
│                                             │
│  [WPM over time sparkline]                  │
│                                             │
│  Weakest keys this session:                 │
│  f(4%) · x(12%) · q(8%)                    │
│                                             │
│  [Next Lesson]   [Try Again]   [Dashboard]  │
└─────────────────────────────────────────────┘
```

### 6.3 Dashboard

- WPM trend (30-day line chart, recharts)
- Accuracy trend (overlaid)
- Per-key heatmap on Ferris Sweep SVG (color-coded by error rate)
- Personal bests table: Best WPM, Best ACC, Best Consistency
- Recent sessions list (last 10, paginated)

### 6.4 Settings

- Theme: Dark / Light / System
- Layout selector (Ferris Sweep Colemak-DH / QWERTY)
- Session mode defaults: duration (15s / 30s / 60s / 120s) or word count (10/25/50/100)
- API key management (for MCP integration)
- Account: change email, change password, delete account

### 6.5 Auth Screens

- Login / Register — minimal, centered card. No OAuth at MVP.

---

## 7. Visual Design Direction

**Aesthetic**: Precision instrument. Think oscilloscope + mechanical keyboard PCB — dark-first, typographic, technical without being cold.

**Palette:**
```
--bg-base:     #0f1117   (near-black, slight blue tint)
--bg-surface:  #1a1d27   (card/panel backgrounds)
--bg-elevated: #22263a   (hover states, active keys)
--accent:      #e8c547   (golden yellow — key highlight, caret, active state)
--accent-dim:  #c4a32e   (secondary accent)
--text-primary:#e8eaf0   (main text)
--text-muted:  #6b7280   (labels, meta)
--correct:     #4ade80   (typed correctly)
--error:       #f87171   (mistyped)
--error-shake: subtle 80ms horizontal keyframe
```

**Typography:**
- Display / WPM numbers: `JetBrains Mono` (communicates terminal precision; already familiar to the target user)
- Body / UI labels: `Inter` (clean, legible)
- Typing text: `JetBrains Mono` at 1.5rem, 1.8 line-height, generous letter-spacing

**Signature element**: The Ferris Sweep keyboard heatmap rendered as an accurate 36-key SVG, with per-key color intensity driven live by session data. It updates after each session and acts as both a metric and a visual identity.

**Motion**: Minimal. Caret blink, error shake, results slide-up. `prefers-reduced-motion` respected globally.

---

## 8. Ferris Sweep SVG Keyboard Component

Implement as `<FerrisHeatmap keys={keyStats} />` React component.

- 36 keys in accurate physical layout (5×3 per hand + 2 thumbs per hand)
- Keys colored on a scale: `--bg-elevated` (no data) → `#f87171` (high error rate)
- Hover tooltip: `{char}: {error_rate}% errors, {avg_latency}ms avg`
- Used in: Dashboard (historical), Results Panel (session), Typing Screen (live, smaller variant, optional toggle)

---

## 9. Docker Compose Structure

```yaml
# docker-compose.yml (production)
services:
  caddy:
    image: caddy:2-alpine
    ports: ["80:80", "443:443"]
    volumes:
      - ./caddy/Caddyfile:/etc/caddy/Caddyfile
      - caddy_data:/data
      - ./frontend/dist:/srv  # built static files

  api:
    build: ./backend
    environment:
      DATABASE_URL: ${DATABASE_URL}
      REDIS_URL: ${REDIS_URL}
      JWT_PRIVATE_KEY_PATH: /run/secrets/jwt_private
      JWT_PUBLIC_KEY_PATH: /run/secrets/jwt_public
    secrets: [jwt_private, jwt_public]
    depends_on: [db, redis]

  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: velocitype
      POSTGRES_USER: velocitype_app
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes: [pg_data:/var/lib/postgresql/data]

  redis:
    image: redis:7-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD}
    volumes: [redis_data:/data]

volumes: [caddy_data, pg_data, redis_data]
secrets:
  jwt_private:
    file: ./secrets/jwt_private.pem
  jwt_public:
    file: ./secrets/jwt_public.pem
```

**`docker-compose.override.yml`** for dev: exposes db/redis ports, uses Vite dev server, hot reload.

---

## 10. Project File Structure

```
velocitype/
├── docker-compose.yml
├── docker-compose.override.yml
├── .env.example
├── secrets/                    # gitignored, keygen script provided
│   └── keygen.sh
│
├── frontend/
│   ├── Dockerfile
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── package.json
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── api/                # typed fetch wrappers
│       ├── components/
│       │   ├── TypingEngine/   # core input handler
│       │   ├── FerrisHeatmap/  # SVG keyboard
│       │   ├── Charts/         # recharts wrappers
│       │   └── ui/             # buttons, inputs, cards
│       ├── hooks/              # useSession, useStats, useAuth
│       ├── pages/              # Trainer, Dashboard, Settings, Auth
│       ├── stores/             # Zustand: session state
│       └── styles/             # global CSS variables
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic/                # DB migrations
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py           # pydantic-settings
│   │   ├── auth/               # JWT, password hashing
│   │   ├── routers/            # auth, sessions, stats, lessons, mcp
│   │   ├── models/             # SQLAlchemy ORM models
│   │   ├── schemas/            # Pydantic v2 request/response schemas
│   │   ├── engine/
│   │   │   ├── adaptive.py     # key scoring + lesson generation
│   │   │   └── layouts.py      # layout definitions + finger maps
│   │   └── db/
│   │       ├── session.py      # async SQLAlchemy session
│   │       └── redis.py        # Redis client
│   └── tests/
│       ├── test_adaptive.py
│       ├── test_auth.py
│       └── test_sessions.py
│
└── caddy/
    └── Caddyfile
```

---

## 11. Typing Engine — Frontend Implementation Notes

The typing engine is the heart of the frontend. Implement as a custom hook `useTypingEngine(lesson: string)`.

**State:**
```typescript
interface TypingState {
  input: string[]          // characters typed per word
  wordIndex: number        // current word
  charIndex: number        // current char in word
  errors: Set<string>      // "wordIdx:charIdx" keys
  startTime: number | null
  keystrokes: KeystrokeEvent[]
  status: 'idle' | 'running' | 'complete'
}
```

**Key invariants:**
- `keydown` listener on `document`, not the input element — prevents focus loss from split keyboard layer switches
- Record `Date.now()` at first keystroke (not on mount) — session starts on first key
- Batch keystrokes in memory; POST to API only on session completion
- WPM calculation: `(correct_chars / 5) / elapsed_minutes` — standard gross WPM
- Net WPM: `gross_wpm - (error_words / elapsed_minutes)`
- Consistency: 100 × (1 - coefficient_of_variation(per_second_wpm_samples))

---

## 12. MCP API Contract

The `/api/mcp/*` endpoints return structured JSON optimized for LLM ingestion.

### `GET /api/mcp/summary`
```json
{
  "user": "philipp",
  "generated_at": "2026-06-27T10:00:00Z",
  "layout": "Ferris Sweep — Colemak-DH",
  "lifetime": {
    "sessions": 142,
    "total_time_minutes": 213,
    "best_wpm": 84,
    "avg_wpm_30d": 79.3,
    "avg_accuracy_30d": 0.971
  },
  "weak_keys": [
    {"char": "q", "error_rate": 0.09, "avg_latency_ms": 312},
    {"char": "x", "error_rate": 0.11, "avg_latency_ms": 298}
  ],
  "trend_7d": {
    "wpm": [74, 76, 75, 78, 80, 79, 82],
    "accuracy": [0.96, 0.97, 0.965, 0.971, 0.973, 0.969, 0.974]
  },
  "coach_prompt": "User is plateauing at ~80 WPM on Colemak-DH / Ferris Sweep. Pinky keys q, x remain weak. Rolling 7-day trend shows improvement. Suggest targeted drill focus."
}
```

Authentication: `Authorization: Bearer {api_key}` where `api_key` is the user's MCP key from Settings. This key is stored hashed in DB; full value shown once on generation.

---

## 13. MVP Acceptance Criteria

Before calling MVP done, all of the following must pass:

- [ ] Register, login, logout, token refresh working with httpOnly cookies
- [ ] Complete a typing session (adaptive mode) end-to-end; metrics saved to DB
- [ ] Results panel displays accurate WPM, accuracy, consistency
- [ ] Dashboard loads with correct charts and key heatmap
- [ ] Adaptive engine produces measurably different lessons based on key_stats
- [ ] Ferris Sweep SVG heatmap renders with correct 36-key layout
- [ ] `docker compose up` from clean state brings up all services and seeds QWERTY + Colemak-DH layouts
- [ ] All API endpoints return 422 on malformed input (Pydantic validation active)
- [ ] Auth endpoints are rate-limited
- [ ] `npm audit` and `pip-audit` report no high/critical CVEs
- [ ] MCP `/api/mcp/summary` endpoint returns valid JSON with API key auth
- [ ] `Tab+Enter` restarts lesson without mouse
- [ ] Error shake animation fires on incorrect keystroke

---

## Post-MVP Milestones

### Milestone 1 — Cadenza / Custom Layout Support
- Layout editor: define key positions, finger assignments, hand assignments via UI
- Import from QMK/ZMK keymap JSON
- User can select any saved layout as their active training layout
- Coda (22-key minimal) variant of Ferris Sweep as second built-in

### Milestone 2 — Advanced Session Modes
- **Custom text**: paste any text to practice (code, prose, specific vocabulary)
- **Code mode**: language-aware corpus (Python, Go, shell); weighted by token frequency
- **Quote mode**: curated quote library, filterable by length and difficulty
- **Timed challenge**: 15s/30s/60s strict — ranked in user's own history

### Milestone 3 — Deep Analytics
- Bigram / trigram error analysis (not just individual keys)
- Hand alternation and same-finger usage metrics
- Per-session replay: scrub through keystroke timeline
- Weekly/monthly PDF progress report (auto-generated, downloadable)
- Plateau detection: alert user when 7-day WPM variance < 1 WPM

### Milestone 4 — Claude Coaching Integration
- Full MCP server implementation (`velocitype-mcp`) exposable to Claude Desktop / Claude Web
- `analyze_progress` tool: Claude ingests stats, returns structured training plan
- `generate_drill` tool: Claude generates custom lesson text targeting specified weaknesses
- Conversation history stored per-user; coaching thread accessible in app

### Milestone 5 — Content & Corpus
- 10,000-word frequency-ranked English corpus (norvig.com word list)
- German corpus (for multilingual users)
- Programming language corpus: Python, TypeScript, Bash, YAML
- Difficulty tiers: beginner (home row only) → intermediate → advanced (full layout)
- Community text submissions (admin-approved)

### Milestone 6 — Polish & PWA
- PWA manifest + service worker: installable, works offline for lesson display
- Keyboard sound profiles: mechanical, silent, custom (Web Audio API)
- Animated key press visualization on virtual keyboard during typing
- Onboarding flow: interactive finger placement tutorial for Ferris Sweep newcomers
- Dark/light/custom theme editor with CSS variable export

---

## Implementation Notes for Claude Code

1. **Start with the backend**: auth → DB models → migrations → session API → adaptive engine. Test each layer before moving to frontend.
2. **Use Alembic from day one**: no manual `CREATE TABLE`. All schema changes through migrations.
3. **Async SQLAlchemy**: use `asyncpg` driver, `AsyncSession` throughout. Do not mix sync/async.
4. **Frontend state**: Zustand for session state (fast, minimal), React Query (`@tanstack/query`) for all server state (sessions, stats, user data). Do not use Redux.
5. **Typing engine**: pure logic, no DOM side effects. All DOM interaction in `useEffect` at the page level. This keeps the engine fully unit-testable.
6. **CSS**: CSS custom properties for all design tokens. No inline styles except dynamic values (e.g., heatmap key color intensity). Tailwind is acceptable but the token system above takes precedence.
7. **Error handling**: FastAPI global exception handler returns RFC 7807 `application/problem+json`. Frontend displays user-readable messages from `detail` field.
8. **Seeding**: `docker compose up` triggers a DB seed script that inserts layout definitions. No manual setup required.
9. **`.env.example`**: must be complete. Running `cp .env.example .env && ./secrets/keygen.sh` should be the only setup step before `docker compose up`.
