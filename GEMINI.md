# stageMatch Project Instructions

## Overview
**stageMatch** is a Flask-based web application for managing user access, profile data collection, and route visualization on a map. It integrates SSO authentication, interactive maps (Leaflet/OpenStreetMap), and geographic services (Photon/OpenRouteService).

## Architecture
The project consists of two primary services:
1. **Main Application (`app.py`)**: Handles views, user sessions, profile CRUD, and acts as a proxy to geographic APIs. Runs on port `5000` by default.
2. **Geo-Proxy Service (`server.py`)**: A support API for geocoding and routing, abstracting external services like Photon and OpenRouteService. Runs on port `5001`.

### Data Layer
- **ORM**: SQLAlchemy.
- **Database**: SQLite (default `users.db`).
- **Models**: Located in `database/models/`.

### Authentication
- **Middleware**: Custom SSO middleware in `auth/`.
- **Modes**: `dev` (simulated login) and `production` (JWT-based SSO).

## Development Workflow
1. **Environment**: Use a Python 3.10+ virtual environment.
2. **Configuration**: Copy `.env.example` to `.env` and configure `ORS_API_KEY`.
3. **Execution**:
   - Start the geo-proxy: `python server.py`
   - Start the main app: `python app.py`
4. **Login (Dev)**: Access `http://127.0.0.1:5000/dev/login` to simulate a session.

## Conventions
- **Language**: Code and comments are in English. Documentation (README, etc.) is in Italian.
- **Styling**: Vanilla CSS and JavaScript (Leaflet).
- **APIs**: RESTful endpoints using Flask. Maintain the current architecture (`app.py` and `server.py`).

## Verification
- **Method**: Manual verification is the standard.
- **Checklist**:
  - Start both services (`server.py` and `app.py`).
  - Verify login flows (Dev/SSO).
  - Test profile completion and data persistence.
  - Validate map routing and address suggestions.
