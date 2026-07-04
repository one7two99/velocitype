I am building TypeForge, a self-hosted touch typing trainer. I have a complete MVP Briefing Pack that defines the full architecture, data models, API, adaptive learning engine, security requirements, and file structure. Your job is to implement the backend first.

Please read the briefing pack carefully before writing any code:

[PASTE FULL CONTENTS OF TypeForge_MVP_BriefingPack.md HERE]

---

Implementation instructions:

1. Scaffold the full project directory structure exactly as defined in Section 10.
2. Implement the backend in this order:
   a. docker-compose.yml + docker-compose.override.yml + .env.example + secrets/keygen.sh
   b. FastAPI app skeleton: main.py, config.py (pydantic-settings), DB session, Redis client
   c. SQLAlchemy ORM models (all 5 tables from Section 3)
   d. Alembic migrations — one initial migration covering all tables
   e. Auth router: register, login, logout, refresh, /me — with Argon2id, RS256 JWT in httpOnly cookies, Redis rate limiting
   f. Layout definitions module (layouts.py) — Ferris Sweep Colemak-DH + QWERTY from Section 5
   g. Adaptive engine (adaptive.py) — key scoring algorithm + lesson generation from Section 5
   h. Sessions router: start, complete, detail, history
   h. Keystrokes router: bulk save on session complete
   i. Stats router: overview, per-key data, progress time-series
   j. Lessons router: next adaptive lesson, available layouts
   k. MCP router: /summary endpoint with API key auth
   l. DB seed script for layout definitions
   m. pytest test stubs for adaptive.py, auth, and sessions

3. Security requirements from Section 2 are non-negotiable. Do not cut corners here.

4. Use async SQLAlchemy with asyncpg throughout — no sync database calls.

5. All API inputs must be validated by Pydantic v2 models in schemas/.

6. When done, confirm that running these three commands from the project root brings up a working API with all endpoints responding:
   cp .env.example .env && ./secrets/keygen.sh && docker compose up --build

Do not start the frontend. Backend only for now.
