# Changelog

All notable changes to TypeForge are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
While the project is pre-1.0, minor versions may introduce features and patch
versions carry fixes; the public API/UX is not yet considered stable.

## [Unreleased]

## [0.20.1] - 2026-07-05

### Changed
- On session save, the Trainer explicitly invalidates the `stats` and `sessions`
  queries so the Dashboard and Analysis views refetch fresh data (previously they
  relied only on refetch-on-navigation). The stats invalidation also moved from
  the typing component to after the save actually succeeds.

## [0.20.0] - 2026-07-05

### Added
- Coach drill sessions are recorded with a dedicated `coach_drill` mode, and the
  Dashboard's Recent Sessions table shows an "AI Drill" tag for them.

## [0.19.1] - 2026-07-05

### Changed
- Moved the version badge next to the TypeForge logo (top-left) instead of beside
  the user menu.

## [0.19.0] - 2026-07-05

### Added
- WPM threshold slider on the Analysis page that drives the Speed heatmap: drag
  to see which keys reach a chosen WPM (green) vs fall short (red), with a live
  "reached / measured" count. Starts at your configured target speed.

## [0.18.0] - 2026-07-05

### Added
- Coach drill mode: while active, every Trainer session generates a fresh
  LLM drill targeting the current weak keys (next drill prefetched during
  typing), until switched back to adaptive. A banner offers "Switch to adaptive".
- `GET /api/coach/metrics` and a Coach-page card showing the exact metrics the
  coach uses (weak keys, avg WPM, accuracy, best WPM) — transparency.

### Changed
- Generated drills are verified to over-represent the focus keys
  (`_covers_focus`); on failure the coach retries once, then falls back to the
  deterministic generator (which guarantees weak-key coverage).

## [0.17.0] - 2026-07-05

### Added
- A thin session progress line on the Trainer: a depleting countdown in timed
  mode (turns warm near the end) and a filling lesson-progress bar in word-count
  mode.

## [0.16.0] - 2026-07-05

### Added
- Live pace indicator on the Trainer: a diverging meter centred on the session
  average WPM, with a dot showing the rolling 10-second pace and a signed delta
  (faster = green, slower = amber). The engine now also exposes `liveAvgWpm`.

## [0.15.0] - 2026-07-05

### Changed
- Settings returned to the main navigation (Trainer / Dashboard / Analysis /
  Coach / Settings); the top-right user menu now holds Profile and Log out.

## [0.14.0] - 2026-07-05

### Changed
- The username in the top-right is now a dropdown menu containing Profile,
  Settings, and Log out. Profile and Settings were removed from the main
  navigation, which is now Trainer / Dashboard / Analysis / Coach. Their
  keyboard shortcuts (`p`, `s`) still work.

## [0.13.0] - 2026-07-05

### Added
- New **Profile** page (`/profile`, nav item + hotkey `p`) for account actions:
  change password, change email, delete account.

### Changed
- Account actions moved out of Settings into the dedicated Profile page; Settings
  now covers appearance, training defaults, and MCP API keys.

## [0.12.0] - 2026-07-05

### Added
- New **Analysis** page (`/analysis`, nav item + hotkey `a`) housing the three
  per-key heatmaps (accuracy, speed, consistency).

### Changed
- The Dashboard now focuses on the progress overview (trend, personal bests,
  recent sessions); the per-key heatmaps moved to the Analysis page.

## [0.11.0] - 2026-07-05

### Added
- `GET /api/version` and a `version` field in `GET /api/health`.
- Documented versioning policy in the README (declared public surface, MAJOR/
  MINOR/PATCH rules, pre-1.0 caveat, 1.0.0 criterion, release process).
- CI check enforcing that `backend/app/version.py` and `frontend/package.json`
  versions match.

### Fixed
- The API self-reported version was hardcoded to `1.0.0` in the OpenAPI docs; it
  now reflects the real release version from a single source (`app/version.py`).

## [0.10.0] - 2026-07-05

### Added
- Third key heatmap on the Dashboard: **consistency** — per-key timing steadiness
  (`1 − stddev/mean` of a key's latencies; green = steady, red = erratic).
- `key_stats` now tracks per-key latency spread (`latency_n`, `latency_sq_sum`,
  migration `0002`); `/api/stats/keys` returns a `consistency` field per key.

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

[Unreleased]: https://github.com/adi-infra/typeforge/compare/v0.20.1...HEAD
[0.20.1]: https://github.com/adi-infra/typeforge/compare/v0.20.0...v0.20.1
[0.20.0]: https://github.com/adi-infra/typeforge/compare/v0.19.1...v0.20.0
[0.19.1]: https://github.com/adi-infra/typeforge/compare/v0.19.0...v0.19.1
[0.19.0]: https://github.com/adi-infra/typeforge/compare/v0.18.0...v0.19.0
[0.18.0]: https://github.com/adi-infra/typeforge/compare/v0.17.0...v0.18.0
[0.17.0]: https://github.com/adi-infra/typeforge/compare/v0.16.0...v0.17.0
[0.16.0]: https://github.com/adi-infra/typeforge/compare/v0.15.0...v0.16.0
[0.15.0]: https://github.com/adi-infra/typeforge/compare/v0.14.0...v0.15.0
[0.14.0]: https://github.com/adi-infra/typeforge/compare/v0.13.0...v0.14.0
[0.13.0]: https://github.com/adi-infra/typeforge/compare/v0.12.0...v0.13.0
[0.12.0]: https://github.com/adi-infra/typeforge/compare/v0.11.0...v0.12.0
[0.11.0]: https://github.com/adi-infra/typeforge/compare/v0.10.0...v0.11.0
[0.10.0]: https://github.com/adi-infra/typeforge/compare/v0.9.0...v0.10.0
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
