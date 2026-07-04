# Changelog

All notable changes to TypeForge are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
While the project is pre-1.0, minor versions may introduce features and patch
versions carry fixes; the public API/UX is not yet considered stable.

## [Unreleased]

## [0.9.0] - 2026-07-05

### Added
- Dashboard now shows two key heatmaps: one coloured by accuracy (error rate) and
  one by speed. The speed heatmap colours each key relative to the target WPM
  (green at/above target, red below), with per-key WPM in the tooltip.

## [0.8.0] - 2026-07-04

### Added
- Target speed (WPM) setting (keybr-style), configurable via a slider in Settings.
- The adaptive engine measures each key against the target: keys below the target
  speed are prioritised for practice and graduate once they reach it
  (`key_wpm = 12000 / avg_latency_ms`). `target_wpm` flows to `/api/sessions/start`,
  `/api/sessions/{id}/complete`, and `/api/lessons/next`.
- Results panel shows WPM against the target with a reached indicator; Dashboard
  adds a target reference line on the trend and a "Keys @ target" count.

## [0.7.0] - 2026-07-04

### Added
- The app version is shown in the top bar (and on the login screen).
- In-app release-notes viewer: click the version to see what's new per version,
  grouped by New / Changed / Fixed. Sourced from `frontend/src/releaseNotes.ts`
  (mirror of this file — keep both in sync on each release).

## [0.6.0] - 2026-07-04

### Added
- Local AI coaching via a self-hosted **Ollama** LLM (no external LLM API): a
  new **Coach** page and endpoints `GET /api/coach/status`,
  `POST /api/coach/analyze` (natural-language coaching from your stats) and
  `POST /api/coach/drill` (LLM-generated drill targeting weak keys, started as a
  custom session). Drill output is sanitized to typeable text and falls back to
  the deterministic adaptive generator when the model is unavailable.
- Bundled `ollama` + one-shot `ollama-pull` Docker services (model configurable
  via `OLLAMA_MODEL`, default `qwen3.5:4b`; `OLLAMA_BASE_URL` to target a host
  instance). GPU is opt-in via a commented `deploy.resources` block.
- Navigation hotkey `c` → Coach.

## [0.5.0] - 2026-07-04

### Added
- Account management: change password (`PATCH /api/auth/password`, rotates all
  refresh tokens), change email (`PATCH /api/auth/email`, 409 on duplicate), and
  delete account (`DELETE /api/auth/me`) — all requiring re-authentication — plus
  the corresponding forms in Settings.
- Timed session mode: the trainer now auto-finishes when the configured duration
  elapses, with a live countdown; lessons are sized to the session goal so the
  clock (not the text) ends timed runs.
- Continuous integration (`.github/workflows/ci.yml`): backend `pytest` +
  `pip-audit`, frontend build + `npm audit`.
- Project `README.md`.

### Fixed
- Authentication state no longer goes stale after logout / account deletion: a
  401 from `/api/auth/me` is now treated as logged-out instead of retaining the
  previously cached user.

## [0.4.0] - 2026-07-04

### Added
- Global navigation hotkeys on the Dashboard and Settings pages: `t` → Trainer,
  `d` → Dashboard, `s` → Settings.
- Results panel: `d` jumps to the Dashboard (alongside `Enter` = Next Lesson and
  `Space` = Try Again).

### Notes
- Navigation hotkeys are intentionally inactive on the Trainer (those letters
  are lesson input) and are ignored while a form field is focused, so text entry
  such as the API-key name is never hijacked.

## [0.3.0] - 2026-07-04

### Added
- Results-panel keyboard shortcuts: `Enter` = Next Lesson, `Space` = Try Again,
  with a ~400 ms arming delay so the keystroke that finished the lesson can't
  immediately trigger an action. Buttons show `<kbd>` hints.

## [0.2.1] - 2026-07-04

### Fixed
- Typing caret no longer causes the text after the cursor to shift when a word
  is completed. The end-of-word caret is drawn as a zero-width absolutely
  positioned element instead of an injected space (verified 0 px drift).

## [0.2.0] - 2026-07-04

### Added
- Frontend MVP (React 18 + TypeScript + Vite):
  - Trainer with the custom typing engine (`useTypingEngine`): document-level
    key capture, timing on first keystroke, word-level backspace, live rolling
    WPM, net WPM, consistency, `Tab+Enter` restart, batched keystrokes.
  - Slide-up Results panel (WPM / accuracy / consistency / time, sparkline,
    weakest keys).
  - 36-key Ferris Sweep SVG heatmap with per-key heat and hover tooltips.
  - Dashboard: 30-day WPM/accuracy trend, heatmap, personal bests, recent
    sessions.
  - Settings: theme (dark/light/system), layout, session-mode defaults, and MCP
    API-key management.
  - Login/register pages over the httpOnly-cookie session flow.
  - Design-token system (Section 7 palette), self-hosted Inter + JetBrains Mono,
    `prefers-reduced-motion` honored.
- One-shot `frontend` Docker builder service that compiles the SPA into the
  `frontend/dist` bind mount served by Caddy.

## [0.1.0] - 2026-07-04

### Added
- Backend MVP (FastAPI, async SQLAlchemy + asyncpg, PostgreSQL 16, Redis 7):
  - Auth: Argon2id password hashing, RS256 JWT in httpOnly/SameSite=Strict
    cookies, refresh-token rotation, per-IP Redis rate limiting.
  - Data models + initial Alembic migration: users, sessions, keystrokes,
    key_stats, refresh_tokens, plus api_keys (MCP) and layouts (seed target).
  - Adaptive learning engine: weighted key-pool scoring and lesson generation;
    Ferris Sweep Colemak-DH and QWERTY layouts.
  - Routers: auth, sessions, keystrokes, stats, lessons, and MCP
    (`/summary`, `/recommendations`, API-key management).
  - RFC 7807 `application/problem+json` error handling.
  - Layout seed script and pytest suite (adaptive, auth, sessions).
- Infrastructure: Docker Compose (production + dev override), Caddy reverse
  proxy with security headers, least-privilege PostgreSQL role, JWT keygen
  script, and `.env.example`.

[Unreleased]: https://github.com/adi-infra/typeforge/compare/v0.9.0...HEAD
[0.9.0]: https://github.com/adi-infra/typeforge/compare/v0.8.0...v0.9.0
[0.8.0]: https://github.com/adi-infra/typeforge/compare/v0.7.0...v0.8.0
[0.7.0]: https://github.com/adi-infra/typeforge/compare/v0.6.0...v0.7.0
[0.6.0]: https://github.com/adi-infra/typeforge/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/adi-infra/typeforge/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/adi-infra/typeforge/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/adi-infra/typeforge/compare/v0.2.1...v0.3.0
[0.2.1]: https://github.com/adi-infra/typeforge/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/adi-infra/typeforge/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/adi-infra/typeforge/releases/tag/v0.1.0
