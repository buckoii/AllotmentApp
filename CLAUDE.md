# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## What this is

A self-hosted allotment planning/tracking tool for a UK (Isle of Man, mild maritime climate) plot:
a shared seed-sowing catalog, per-user tracking of what's been sown/transplanted/harvested with
progress bars and next-task alerts, succession-sowing reminders, bed-sharing suggestions, a harvest
log valued against supermarket reference prices, and an expenses ledger - so the app can answer
"has this thing paid for itself yet".

Flask JSON API (`backend/`) + React SPA (`frontend/`, Vite), same self-hosted LXC/Docker pattern as
this homelab's other custom apps (see `FitnessApp`, `booksapp`).

## Running locally

Backend:
```
cd backend
pip install -r requirements.txt
export FLASK_SECRET_KEY=dev-secret
export DB_PATH=./allotment.db
python app.py     # :5000, auto-creates schema + seeds the catalog via init_db()
```

Frontend (separate terminal):
```
cd frontend
npm install
npm run dev        # :5173, proxies /api to :5000 (see vite.config.js)
```

No test suite or linter configured. Node/npm were not available in the environment this was first
built in - the frontend has never been run through `npm install`/`vite build` locally; the first
real build happens via the Dockerfile's `node:20-alpine` stage. If anything fails to build, check
there first before assuming the backend is at fault.

## Running via Docker

```
docker compose up -d --build
```

Multi-stage `Dockerfile`: stage 1 (`node:20-alpine`) runs `npm install && npm run build`, stage 2
(`python:3.11-slim`) copies the built static files into `static_frontend/` alongside the Flask app
and serves both API and SPA from one gunicorn process on :5000. `docker-compose.yml` bind-mounts
`/opt/allotment/data` (host) to `/data` (container) for the SQLite file, same convention as `fitness`.

## Architecture

- **Two-tier schema** (`backend/schema.sql`): `plants` is shared reference data (one row per
  sowable veg/fruit/herb - germination, sow windows, days-to-harvest, yield, reference price,
  succession interval); everything else (`plots`, `plantings`, `harvests`, `expenses`, `users`) is
  per-user. Keep this split - it's what lets one curated catalog serve every user if this is ever
  opened up beyond a single household, and retrofitting `user_id` onto tables after real data
  exists is exactly the pain [[project-fitness-tracker]] hit once already.
- **`backend/growth.py`** holds all the sowing-calendar math (month-range checks with year-boundary
  wraparound for things like garlic, progress-bar percentage, next-due-task, succession-due, value
  score, bed-sharing candidates) deliberately separate from Flask/DB code so it's easy to reason
  about and extend without touching routes.
- **Progress bar vs overdue-task badge are two different signals, not one.** The progress bar is a
  calm red-to-green gradient purely for "how far through the seed-to-harvest window". Overdue
  *actions* (e.g. a missed transplant date) are a separate badge. Don't collapse these into the
  same color scale - that was a deliberate design decision to avoid a "everything red is bad, but
  which kind of bad?" muddle.
- **`maturity_from` matters.** Some crops' days-to-harvest is measured from the sow date (direct-sow
  veg like carrots), others from the transplant date (brassicas, tomatoes, etc., per how seed
  packets actually phrase it). `growth.total_lifecycle_days()` folds the indoor growing-on period
  into the total for transplant crops - don't compute progress/value scoring against
  `days_to_harvest` alone without checking `maturity_from` first.
- **Harvest value is snapshotted at insert time** (`harvests.value_gbp`), not recomputed live from
  the catalog's current `ref_price_gbp_per_kg`, so editing a reference price later doesn't rewrite
  history.
- **Auth**: cookie sessions, `werkzeug.security` password hashing, self-service `/api/auth/register`.
  Every per-user table access filters by `session["user_id"]` - there's no other authorization layer.

## Known gaps (deliberately deferred, not oversights)

- **Perennial fruit** (strawberries, raspberries, rhubarb) don't fit the one-shot sow-to-harvest
  lifecycle this schema models - a planting here can't yet represent "crops again every year after
  the first season". `seed_data.py`'s strawberry entry is a placeholder, flagged in its own notes.
- **Overwintering crops sown the previous summer** (e.g. spring cabbage) aren't in the seed catalog
  yet for the same reason - the UI's "sowable this month" logic assumes a single-year window.
- **Bed-sharing suggestions are timing-only** - they don't know about companion-planting
  compatibility (e.g. keeping alliums away from legumes), just whether a fast crop's lifecycle fits
  in the remaining time before a slower one needs its space back.
- **Catalog data (`backend/seed_data.py`) is a first-pass curation**, not verified against RHS or
  actual seed packets - sanity-check sow windows/days-to-harvest before relying on it for anything
  time-critical.
