# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

stageMatch is a full-stack Flask web app that matches student profiles with companies for internship opportunities. It authenticates entirely in-app via Google OAuth, stores data in SQLite via SQLAlchemy, and delegates geocoding/routing to a separate internal proxy service.

## Running the app

Two Flask processes make up the system and both need `.env` (copy from `.env.example`):

```bash
pip install -r requirements.txt

python app.py       # main app — port 5000 (HOST/PORT from .env)
python server.py    # geo-proxy service — port 5001 (PORT_API from .env)
```

Or via Docker Compose, which wires the two services together (`web` calls `api` at `http://api:5001`):

```bash
docker compose up --build
```

There is no test suite, linter, or build step configured in this repo.

Login (student or company) requires working Google OAuth credentials (`GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET`) even locally — there is no dev bypass.

## Architecture

See `ARCHITECTURE.md` for a diagram. The key split:

- **`app.py`** — the main Flask app (port 5000). Serves all HTML views (Jinja templates in `resources/html/`), owns user/company sessions, and is the only service that talks to the database.
- **`server.py`** — an internal Flask "geo-proxy" (port 5001), called only by `app.py` (never directly by the browser). Abstracts three external APIs: Nominatim (geocoding), Photon (address autocomplete), and OpenRouteService (routing). `app.py` proxies `/photon` and `/routejson` requests to it via `API_URL`.
- **`auth/`** — authentication layer:
  - `auth/auth.py` wires up the session middleware and rate limiter from env vars, and exposes email-parsing helpers (`getName`/`getSurname` prefer `surname.name@domain` email format, falling back to splitting the Google-provided full name for accounts that don't follow it).
  - `auth/rate_limiter.py` implements `RateLimiter`: per-user and global concurrent-session caps, persisted in the `active_sessions` DB table (via `database_helper`) — survives restarts and multiple workers. Exceeding the per-user cap evicts that user's oldest session rather than rejecting the new login.
  - `auth/middleware/session_middleware.py` implements server-side session creation (`SessionMiddleware.createSession`) and the `loginRequired(role=...)` route decorator, which redirects to the matching login page (`/login/student` or `/login/company`) with a `?notice=` reason when the session is missing/expired.
  - `auth/auth_google/auth.py` wires up Authlib/Google OAuth — the single login mechanism for both students and companies.
- **`database/`** — SQLAlchemy layer:
  - `database/database_helper.py` is the single access point for all DB operations (no ORM session objects are passed around outside this module). It also has `modelToDict()`, a generic model-to-dict serializer that walks relationships recursively.
  - `database/models/` — one file per table (`User`, `Company`, `UserPreferences`, `Skill`, `SoftSkill`, `UserRoute`, `PrivacyConsent`, `ActiveSession`). `User` is the hub, with cascading relationships to preferences/skills/soft_skills/routes. Primary keys are Google `sub` IDs (`googleId`), not autoincrement ints (except `UserRoute`, which is a per-user capped list — max 25 entries, deduped by address+mode — and `ActiveSession`, keyed by session id).
- **`resources/`** — the frontend, served as both static files and Jinja templates from the same folder (`app.py` sets `static_folder`/`template_folder` to `./resources`). One HTML/CSS/JS triplet per page, no bundler or framework — vanilla JS and CSS only.

### Design

Any work on layouts, components, or colors in `resources/html`/`resources/css` must follow the `stagematch-design` skill (`.claude/skills/stagematch-design/`): Midnight Blue & Emerald Green palette, CSS variables from `assets/brand-variables.css`, vanilla CSS only (no external UI libraries). Reference: `references/design-system.md`.

### Request flow for a logged-in page

1. Browser hits an `@au.session_middleware.loginRequired(role=...)` route in `app.py`.
2. Decorator checks `session['user']`, validates the rate-limiter session is still live, and touches its `last_seen`.
3. Route handler calls into `database_helper` for data, converts models with `modelToDict()`, and renders a template from `resources/html/`.
4. Any map/routing calls from the frontend hit `/photon` or `/routejson` on `app.py`, which forwards to `server.py` (port 5001) with a `requests` call.

### Auth flow

Both students and companies log in the same way — Google OAuth — converging on `_completeLogin()` in `app.py`:
- **Student**: `/auth/login` → sets `session['auth_type'] = "user"` → `/auth/google/login` → `/auth/google/callback` → `getGoogleUserInfo()` → session created.
- **Company**: `/auth/company/login` → sets `session['auth_type'] = "company"` (and stages registration data in `session['pending_company_data']` on POST) → `/auth/google/login` → `/auth/google/callback` → session created.

`session['auth_type']` distinguishes which onboarding path `/logged/complete` takes. `loginRequired`'s `role` param (or, when omitted, `session['auth_type']`) decides which login page a missing/expired session bounces back to.

## Conventions

- Route handlers and helper functions use camelCase (`getUserById`, `authLogin`), matching the JS side — this is intentional across the Python codebase, not an accident.
- Some user-facing strings, error messages, and comments are in Italian; keep new user-facing text consistent with the language already used on that page.
- Composite address fields are stored as a single `String` joined with the delimiter `` ££ `` (see `indirizzo`/`address` in `app.py` and `database_helper`) — split/join with that exact delimiter when reading or writing them.

## Contribution workflow

Full rules in `CONTRIBUTING.md`. Summary: anyone contributing branches from `main` using their own name capitalized (`git switch -c Cognome`), and every commit message must start with `NOME: ` (all caps) followed by a short description — avoid generic messages like "update files".
