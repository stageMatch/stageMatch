# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

stageMatch is a full-stack Flask web app that matches student profiles with companies for internship opportunities. It authenticates entirely in-app via Google OAuth, stores data in SQLite via SQLAlchemy, delegates geocoding/routing to a separate internal proxy service, and scores student/job-offer matches with an in-process background engine that can optionally refine its deterministic score via an LLM (Anthropic or DeepSeek).

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

`SERVER_SECRET_KEY` is required (the app refuses to start without it). In Docker the app runs under Gunicorn with a **single worker** (the matching queue is in-memory, so more than one app process would each get their own queue).

Tests and lint (`requirements-dev.txt`): `python -m pytest` and `ruff check .` (only real errors — style is not enforced). CI runs both (`.github/workflows/ci.yml`). There is no build step. `tests/conftest.py` sets the env vars and provides a fresh SQLite `db` fixture; API tests log in by writing `session['user']`/`session_id`/`auth_type` directly (no Google needed).

Login (student or company) requires working Google OAuth credentials (`GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET`) even locally — there is no dev bypass.

The AI refinement step in `matching/ai_refiner.py` is optional: with `ANTHROPIC_MATCHING_ENABLED=False`, or no API key for the selected `MATCH_AI_PROVIDER` (`anthropic` or `deepseek`), matching still works end-to-end using only the deterministic score.

## Architecture

See `ARCHITECTURE.md` for a diagram. The key split:

- **`app.py`** — the main Flask app (port 5000). Serves all HTML views (Jinja templates in `resources/html/`), owns user/company sessions, and is the only service that talks to the database.
- **`validation.py`** — input validation/normalization for the JSON routes in `app.py`; raises `ValueError` with an Italian user-facing message, which routes turn into a 400 (never a 500). Use it for any new route that accepts user input.
- **`server.py`** — an internal Flask "geo-proxy" (port 5001), called only by `app.py` (never directly by the browser). Abstracts three external APIs: Nominatim (geocoding), Photon (address autocomplete), and OpenRouteService (routing). `app.py` proxies `/photon` and `/routejson` requests to it via `API_URL`.
- **`matching/`** — student/job-offer matching engine, run off the request thread:
  - `worker.py` is a single daemon thread draining an in-memory `queue.Queue`; `startWorker()` is idempotent (guarded by a lock) and `enqueue(job_fn, name=None)` queues a zero-arg callable (jobs with the same pending `name` are coalesced). Queue lives only in the current process — no cross-process/worker coordination; at startup `engine.recomputeMissingMatches` re-queues whatever was lost.
  - `scorer.py` computes the deterministic 0-100 score from skill/soft-skill match and commute duration; pure functions, no DB/network access.
  - `geo.py` resolves student↔company commute distance/duration, reusing the same `UserRoute` cache and geo-proxy (`server.py`) as the student dashboard's "Percorsi" section.
  - `ai_refiner.py` optionally refines the deterministic score via an LLM, sending only an anonymized payload (skills/soft skills/languages/experiences/distance, no identifying data). Provider is picked by `MATCH_AI_PROVIDER` (`anthropic` default, or `deepseek` — same `anthropic` SDK against DeepSeek's Anthropic-compatible endpoint, just a different `base_url`/key/model). Any failure, missing key, disabled flag, or low deterministic score short-circuits to the deterministic score (`ai_status`: `ok`/`fallback`/`disabled`/`skipped`). The AI score is validated (finite, 0-100) and clamped to ±15 of the deterministic score; user-written text is redacted and wrapped as untrusted data in the prompt.
  - `engine.py` orchestrates the above plus `database_helper`, and is what `worker.py` jobs actually call; result is upserted into the `matches` table (unique per `user_id`+`job_offer_id`).
- **`auth/`** — authentication layer (`loginRequired(role=...)` returns 403 if `session['auth_type']` doesn't match `role`; `app.before_request` rejects cross-site writes via `Origin`/`Sec-Fetch-Site`):
  - `auth/auth.py` wires up the session middleware and rate limiter from env vars, and exposes `getNameSurname(user)` (students only; companies take their name from the registration form): uses Google's `given_name`/`family_name` first (they handle composite names); a missing field is filled from the `surname.name.studente@domain` email format.
  - `auth/rate_limiter.py` implements `RateLimiter`: per-user and global concurrent-session caps, persisted in the `active_sessions` DB table (via `database_helper`) — survives restarts and multiple workers. Exceeding the per-user cap evicts that user's oldest session rather than rejecting the new login.
  - `auth/middleware/session_middleware.py` implements server-side session creation (`SessionMiddleware.createSession`) and the `loginRequired(role=...)` route decorator, which redirects to the matching login page (`/login/student` or `/login/company`) with a `?notice=` reason when the session is missing/expired.
  - `auth/auth_google/auth.py` wires up Authlib/Google OAuth — the single login mechanism for both students and companies.
- **`database/`** — SQLAlchemy layer:
  - `database/database_helper.py` is the single access point for all DB operations (no ORM session objects are passed around outside this module). It also has `modelToDict()`, a generic model-to-dict serializer that walks relationships recursively.
  - `database/models/` — one file per table (`User`, `Company`, `UserPreferences`, `Skill`, `SoftSkill`, `Language`, `Experience`, `JobOffer`, `JobOfferSkill`, `JobOfferSoftSkill`, `Application`, `Match`, `Notification`, `UserRoute`, `PrivacyConsent`, `ActiveSession`). `User` and `Company` are the two hubs (`User` cascades to preferences/skills/soft_skills/languages/experiences/routes/applications/matches/notifications; `Company` cascades to job offers/notifications). Primary keys are Google `sub` IDs (`googleId`) on `User`/`Company`, not autoincrement ints — `JobOffer`, `Application`, `Match`, `Notification` use autoincrement ints instead, since they aren't 1:1 with a Google account. `UserRoute` is a per-user capped list (max 25 entries, deduped by address+mode) and `ActiveSession` is keyed by session id. `CompanyAccessCode` holds one-time company registration codes generated by admins (`ADMIN_EMAILS`, page `/admin/codes`); `addCompany(..., access_code=...)` consumes the code atomically. SQLite runs with `foreign_keys=ON`, WAL and a busy timeout. `Match` is unique per (`user_id`, `job_offer_id`) and stores both `deterministic_score` and the optional `ai_score`/`explanation` from `matching/`.
- **`resources/`** — the frontend, served as both static files and Jinja templates from the same folder (`app.py` sets `static_folder`/`template_folder` to `./resources`). One HTML/CSS/JS triplet per page, no bundler or framework — vanilla JS and CSS only.

### Design

Any work on layouts, components, or colors in `resources/html`/`resources/css` must follow the `stagematch-design` skill (`.claude/skills/stagematch-design/`): Midnight Blue & Emerald Green palette, CSS variables from `assets/brand-variables.css`, vanilla CSS only (no external UI libraries). Reference: `references/design-system.md`.

### Request flow for a logged-in page

1. Browser hits an `@au.session_middleware.loginRequired(role=...)` route in `app.py`.
2. Decorator checks `session['user']`, validates the rate-limiter session is still live, and touches its `last_seen`.
3. Route handler calls into `database_helper` for data, converts models with `modelToDict()`, and renders a template from `resources/html/`.
4. Any map/routing calls from the frontend hit `/photon` or `/routejson` on `app.py`, which forwards to `server.py` (port 5001) with a `requests` call.
5. Routes that change a student's profile or a job offer's requirements call `matching/worker.py`'s `enqueue()` to recompute affected `Match` rows in the background thread, instead of blocking the response on `matching/engine.py` (which itself calls out to `server.py` for distance and, optionally, an LLM for score refinement).

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

Se una modifica incide su quanto descritto nel README (setup, comandi di avvio, dipendenze, architettura, ecc.), aggiorna anche il README nello stesso commit/PR.
