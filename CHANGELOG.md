# Changelog

All notable changes to Velocitype are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
While the project is pre-1.0, minor versions may introduce features and patch
versions carry fixes; the public API/UX is not yet considered stable.

## [Unreleased]

## [0.31.2] - 2026-07-05

### Fixed
- AI coach drills now use your **latest** metrics: the next drill is prefetched
  **after** a session's results are saved (previously it was fetched at the start
  of the current session, so it lagged one session behind).

### Changed
- Coach drills (and adaptive lessons) are **more varied on small key sets**: when
  few real words fit the unlocked letters, the generator blends in varied
  pseudo-word clusters instead of repeating a couple of words (e.g. "not"/"into").
  Full-keyboard lessons stay word-based.

## [0.31.1] - 2026-07-05

### Fixed
- Progressive unlocking: the first lessons only practised some of the unlocked
  keys (e.g. the initial set showed only "into"/"not" — missing **e** and **a**),
  because the common-word pool for a small key set can't cover every letter. The
  lesson generator now guarantees **every unlocked letter is practised** (via
  keybr-style clusters for letters no real word covers).

## [0.31.0] - 2026-07-05

### Added
- **Progressive key unlocking (keybr-style).** You practice a small starting set
  of keys; the next key unlocks once every active key reaches a share of your
  target speed over a number of sessions. Both are configurable in Preferences —
  the **unlock threshold %** and the **mastery window (sessions)** — plus a
  **toggle** and a **Reset progression** button. Lessons **and AI drills only ever
  use unlocked keys** (the deterministic generator now produces clean pseudo-words
  from just the unlocked letters when the set is small). The Heatmaps page shows a
  progress indicator and locks not-yet-unlocked keys; Session Complete announces a
  newly unlocked key.
- New API: `GET /api/lessons/unlock`, `POST /api/lessons/unlock/reset`;
  `POST /api/sessions/{id}/complete` returns `unlocked_char`; three new settings
  synced across browsers. New table `user_layout_progress` + `key_stats.qualifying_streak`
  (migration `0007`).

### Changed
- **Existing accounts are grandfathered** to all keys unlocked (no regression);
  enable/reset progression from Preferences. New accounts start progressive.

## [0.30.0] - 2026-07-05

### Added
- **Settings sync across browsers.** UI/training preferences (theme, layout,
  session goal, duration, word count, target WPM) are now stored per user in the
  database (`user_settings`, migration `0006`) and synced across devices/browsers:
  they hydrate from the server on sign-in and save back on change. `localStorage`
  still provides an instant local value and offline fallback. New endpoints
  `GET`/`PUT /api/settings`. Preferences are kept when using "Delete all data"
  (they are settings, not metrics).

## [0.29.0] - 2026-07-05

### Added
- **Delete all data** under Profile → Account. Password-confirmed, it permanently
  removes all of the user's data — sessions, keystrokes, per-key and bigram stats,
  AI-provider config (including any stored Mistral API key) and prompt overrides —
  leaving a fresh profile with empty stats. The account, login and MCP keys are
  kept. Deletions are **real row deletes** (`POST /api/auth/me/reset`), not
  soft-deletes/flags.

## [0.28.2] - 2026-07-05

### Fixed
- Generating a drill from the Analysis tables failed with "One or more fields
  failed validation." whenever more than 12 keys/bigrams were selected (e.g.
  "Generate drill from 245 bigrams"). The `focus_keys`/`focus_bigrams` request
  lists were capped at 12 items; the bound is now generous (the service already
  focuses the drill on the top few of whatever is selected).

## [0.28.1] - 2026-07-05

### Changed
- Nav: **AI-Coach** now sits directly right of Trainer.
- Analysis: a sub-navigation at the top links to its two tables (**Per-key
  breakdown** and **Bigram breakdown**) — click to jump, and the active section is
  highlighted as you scroll.

## [0.28.0] - 2026-07-05

### Added
- **Bigram / rhythm surface in the UI.** The Analysis page now has a **Bigram
  breakdown** table (class, error %, WPM, rhythm consistency, hitch %, with
  same-finger bigrams highlighted) — sortable and searchable. Tick the bigrams
  you want and **Generate drill from N bigrams** starts a coach-drill session
  targeting exactly those letter pairs (the `focus_bigrams` path from 0.27.0).
- The **AI-Coach** page ("What your coach sees") now shows your weak bigrams
  (with SFB flags) and a rhythm line (redirect % / SFB-chain % / worst redirect).

### Changed
- The Trainer's coach-drill banner shows the targeted letter pairs when a bigram
  drill is active.

## [0.27.0] - 2026-07-05

### Added
- **N-gram metric model (backend).** Bigram statistics are now captured from your
  keystrokes — same-finger bigrams (SFB), inward/outward rolls, alternation — plus
  **rhythm consistency** (inter-key-interval spread) and a **hitch** (hesitation)
  counter, stored in a new `ngram_stats` table (migration `0005`). Trigram
  rolls/redirects are derived on read. A pure engine module `engine/ngrams.py`
  does the classification and weakness scoring (SFBs get a score bonus).
- The **AI coach now sees bigrams and rhythm**: `analyze` calls out weak
  same-finger bigrams, rhythm hitches and awkward redirects (grounded in the data,
  no invented numbers), and `POST /api/coach/drill` accepts `focus_bigrams` to
  build drills around specific letter pairs (with coverage verification + the
  deterministic fallback).
- New API: `GET /api/stats/ngrams` (per-bigram table with class + consistency);
  `GET /api/coach/metrics` now includes `weak_bigrams` + `trigram_rollup`.
- One-off backfill `python -m app.db.backfill_ngrams` seeds existing users' bigram
  stats from their retained keystrokes.

## [0.26.1] - 2026-07-05

### Fixed
- Session Complete panel: the action buttons had too little horizontal padding —
  the highlighted "Next Lesson" label touched its edges. Restored comfortable
  button padding and widened the panel so the three equal-width buttons breathe.

## [0.26.0] - 2026-07-05

### Added
- **Targeted drills from the per-key Analysis.** Each row in the per-key table now
  has a checkbox (keys "needing work" are pre-selected); a **Generate drill from N
  keys** button sends exactly those keys to the active LLM (Ollama or Mistral),
  which builds a word list focused on them, and starts a coach-drill session. The
  Trainer banner shows which keys are being targeted.
- The drill prompt now includes per-key severity (error % and approx WPM) for the
  focus keys so the model can prioritise.

### Changed
- `POST /api/coach/drill` accepts an optional `focus_keys` list; without it the
  adaptive engine still picks the weakest keys automatically (unchanged default).

## [0.25.0] - 2026-07-05

### Added
- **Per-key breakdown on Analysis.** The Analysis page now shows a sortable,
  searchable table with one row per key — hand, finger, attempts, errors,
  error %, WPM (from latency), average latency, consistency %, and a status
  verdict (on-target / slow / error-prone / needs data). Sort by any column,
  search for a key, or filter to only the keys that need work.

### Changed
- The three key heatmaps (Accuracy / Speed / Consistency) moved to a dedicated
  **Heatmaps** menu item; Analysis is now the per-key table.

## [0.24.0] - 2026-07-05

### Added
- **Pluggable AI provider (per user).** Settings → AI Provider lets each account
  choose where coaching runs: the local **Ollama** model (default, fully private)
  or **Mistral** (EU cloud). Pick the model for either provider, and — for
  Ollama — **download new models** from Settings with a live progress indicator.
- Mistral integration calls `https://api.mistral.ai` **server-side**; the API key
  is entered in Settings, stored **encrypted at rest** (Fernet key derived from
  the JWT private key), and never returned to the browser. Analysis/drills use the
  selected provider; drills keep their deterministic fallback.
- New endpoints under `/api/coach`: `GET`/`PUT /config`, `GET /models`,
  `POST`/`GET /models/pull`; `GET /status` now reports the active provider. New
  `user_ai_config` table (migration `0004`).

### Changed
- The AI Coach page reflects the active provider/model and states the privacy
  trade-off when Mistral is selected (data leaves your machine). Ollama remains
  the private default.

## [0.23.0] - 2026-07-05

### Changed
- **Rebrand: TypeForge is now Velocitype.** All user-facing surfaces (app title,
  logo, auth screen, release notes) and documentation now use the Velocitype name
  and manifesto: *the world's fastest typing trainer doesn't run in the cloud, it
  runs on your localhost.* Not a single byte leaves your machine.
- Infrastructure identifiers were renamed to match: the Postgres database
  (`typeforge` → `velocitype`) and app role (`typeforge_app` → `velocitype_app`)
  were renamed in place (existing training data preserved), and the Docker Compose
  project, containers, network and volumes are now `velocitype`. The JWT issuer is
  now `velocitype`, so existing sessions refresh into new tokens on next request.

## [0.22.0] - 2026-07-05

### Added
- **Corne keyboard layout.** Two new selectable layouts — *Corne — Colemak-DH*
  and *Corne — QWERTY* — modelling the 3×6 + 3-thumb split. The heatmap now
  renders the Corne's extra outer columns and third thumb as greyed, non-trainable
  modifier keys (Tab/Ctrl/Shift, `'`/Bksp/Enter, and the thumb cluster), so the
  board is drawn truthfully while training stays on the 30 letter keys. Switch
  layouts under Settings → Training → Layout.

### Changed
- Heatmap geometry is now driven per-layout (variable column count, thumb count,
  and non-trainable "decoration" keys) instead of assuming a fixed 3×5 + 2-thumb
  board.

## [0.21.0] - 2026-07-05

### Added
- **Editable AI prompts.** Settings now has an "AI Settings" section where you can
  view and override the exact prompts sent to the local AI coach — a separate
  system prompt and instruction for both *Get analysis* and *Start coaching
  drills* (four fields). Fresh installs start from built-in defaults; edits are
  stored server-side per user. The instruction templates support `{{data}}`
  (trainee stats) and `{{focus}}` (weak keys) placeholders, which the app injects
  automatically. "Reset to defaults" clears your overrides.
- New endpoints `GET`/`PUT /api/coach/prompts` and a `user_prompts` table
  (migration `0003`).

### Changed
- The navigation entry "Coach" is renamed to **AI-Coach**.

## [0.20.3] - 2026-07-05

### Fixed
- Session Complete panel: the Next Lesson / Try Again / Dashboard buttons now
  always render on a single row (equal-width, no wrap) — "Dashboard" no longer
  wrapped to the next line. Keyboard hints hide on very narrow screens.

## [0.20.2] - 2026-07-05

### Fixed
- Ferris Sweep heatmap now renders the correct **2 thumb keys per hand** (it
  previously showed 3 on the left and 2 on the right).

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

[Unreleased]: https://github.com/adi-infra/typeforge/compare/v0.31.2...HEAD
[0.31.2]: https://github.com/adi-infra/typeforge/compare/v0.31.1...v0.31.2
[0.31.1]: https://github.com/adi-infra/typeforge/compare/v0.31.0...v0.31.1
[0.31.0]: https://github.com/adi-infra/typeforge/compare/v0.30.0...v0.31.0
[0.30.0]: https://github.com/adi-infra/typeforge/compare/v0.29.0...v0.30.0
[0.29.0]: https://github.com/adi-infra/typeforge/compare/v0.28.2...v0.29.0
[0.28.2]: https://github.com/adi-infra/typeforge/compare/v0.28.1...v0.28.2
[0.28.1]: https://github.com/adi-infra/typeforge/compare/v0.28.0...v0.28.1
[0.28.0]: https://github.com/adi-infra/typeforge/compare/v0.27.0...v0.28.0
[0.27.0]: https://github.com/adi-infra/typeforge/compare/v0.26.1...v0.27.0
[0.26.1]: https://github.com/adi-infra/typeforge/compare/v0.26.0...v0.26.1
[0.26.0]: https://github.com/adi-infra/typeforge/compare/v0.25.0...v0.26.0
[0.25.0]: https://github.com/adi-infra/typeforge/compare/v0.24.0...v0.25.0
[0.24.0]: https://github.com/adi-infra/typeforge/compare/v0.23.0...v0.24.0
[0.23.0]: https://github.com/adi-infra/typeforge/compare/v0.22.0...v0.23.0
[0.22.0]: https://github.com/adi-infra/typeforge/compare/v0.21.0...v0.22.0
[0.21.0]: https://github.com/adi-infra/typeforge/compare/v0.20.3...v0.21.0
[0.20.3]: https://github.com/adi-infra/typeforge/compare/v0.20.2...v0.20.3
[0.20.2]: https://github.com/adi-infra/typeforge/compare/v0.20.1...v0.20.2
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
