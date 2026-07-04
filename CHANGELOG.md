# Changelog

All notable changes to TypeForge are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
While the project is pre-1.0, minor versions may introduce features and patch
versions carry fixes; the public API/UX is not yet considered stable.

## [Unreleased]

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

[Unreleased]: https://github.com/adi-infra/typeforge/compare/v0.4.0...HEAD
[0.4.0]: https://github.com/adi-infra/typeforge/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/adi-infra/typeforge/compare/v0.2.1...v0.3.0
[0.2.1]: https://github.com/adi-infra/typeforge/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/adi-infra/typeforge/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/adi-infra/typeforge/releases/tag/v0.1.0
