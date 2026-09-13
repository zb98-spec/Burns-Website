# Burns Dashboard — Development Plan

A personal website with a landing dashboard of project tiles. Each project
is built out independently as a Flask Blueprint, so new projects can be
added (or left unbuilt) without touching the others.

## Decisions locked in

| Area | Decision |
|---|---|
| Backend | Flask (app factory + Blueprints) |
| Rendering | Server-rendered Jinja2 templates, minimal vanilla JS |
| Styling | Plain hand-written CSS, no framework/build step |
| Auth | None for MVP — reconsider once a project stores anything sensitive |
| Structure | One Flask app, one Blueprint per project, one Cloud Run service |
| Database | One Neon Postgres project; each app gets its own schema (`wine.*`, `grocery.*`, `recipes.*`) when it needs one |
| Container | Single Dockerfile, gunicorn as the WSGI server |
| Hosting | Google Cloud Run (scales to zero, no cluster to manage) |
| Deploys | Manual (`gcloud run deploy`) for now; GitHub Actions CI/CD added later |
| Repo | New GitHub repo, created as part of setup |
| Domain | Default `*.run.app` URL for now; custom domain can be mapped later |

## Current status

The repo currently contains the **shell app only**:
- Landing page with 3 tiles (Wine Cellar Tracker, Grocery List, Recipe Tracker)
- Each tile links to a placeholder page ("this project hasn't been built yet")
- No database connection is wired up yet — `DATABASE_URL` is read from config but unused
- No authentication

## Project structure

```
Burns-Website/
├── app/
│   ├── __init__.py              # create_app() factory, registers all blueprints
│   ├── templates/
│   │   ├── base.html            # shared layout (header, CSS link)
│   │   └── placeholder.html     # shared "not built yet" page
│   ├── static/css/style.css     # single stylesheet, no build step
│   └── blueprints/
│       ├── core/                # landing page + tile list
│       │   ├── routes.py
│       │   └── templates/core/index.html
│       ├── wine_cellar/         # placeholder — build out independently
│       │   └── routes.py
│       ├── grocery_list/        # placeholder — build out independently
│       │   └── routes.py
│       └── recipe_tracker/      # placeholder — build out independently
│           └── routes.py
├── config.py                    # env-based config (SECRET_KEY, DATABASE_URL)
├── wsgi.py                      # entrypoint for gunicorn / `python wsgi.py`
├── requirements.txt
├── Dockerfile
├── .dockerignore
├── .gitignore
├── .env.example
└── DEVELOPMENT_PLAN.md          # this file
```

## How to build out a project independently

Each project lives entirely inside its own `app/blueprints/<project>/`
folder. To build one out (e.g. Wine Cellar Tracker):

1. Add routes to `app/blueprints/wine_cellar/routes.py`.
2. Add templates under `app/blueprints/wine_cellar/templates/wine_cellar/`.
3. If it needs data, add a `models.py` in that folder using SQLAlchemy (or
   raw `psycopg2`) against the `wine` schema in the shared Neon database.
4. Flip its `status` from `"coming soon"` to `"live"` in
   `app/blueprints/core/routes.py` (`PROJECTS` list) once the index route
   is ready.
5. No other blueprint needs to change. The app factory in `app/__init__.py`
   already registers all four blueprints, so routing "just works" as soon
   as a project's `index()` view exists.

This keeps projects decoupled while still shipping as one small container
and one Cloud Run service — no need to stand up new infra per project.

## Local development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in SECRET_KEY / DATABASE_URL as needed
python wsgi.py          # http://localhost:8080
```

## Database (Neon)

- One Neon project for the whole site.
- Each app that needs persistence gets its own Postgres **schema**
  (`CREATE SCHEMA wine;`, `CREATE SCHEMA grocery;`, `CREATE SCHEMA recipes;`)
  inside that one database, rather than separate databases or separate
  Neon projects.
- `DATABASE_URL` (from `.env` locally, from Cloud Run env vars / Secret
  Manager in production) is the single connection string shared by all
  blueprints.
- No ORM is wired up yet. When the first project needs data, add
  Flask-SQLAlchemy (or keep it to raw `psycopg2`) at that point — avoid
  adding it before it's needed.

## Docker

```bash
docker build -t burns-dashboard .
docker run -p 8080:8080 --env-file .env burns-dashboard
```

## Deploying to Google Cloud Run (manual, for now)

```bash
gcloud auth login
gcloud config set project <YOUR_GCP_PROJECT_ID>

gcloud run deploy burns-dashboard \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars SECRET_KEY=<value> \
  --set-env-vars DATABASE_URL=<neon-connection-string>
```

`--source .` builds the container from the Dockerfile via Cloud Build, so a
local Docker install isn't strictly required to deploy — only to test
locally.

Prefer secrets over `--set-env-vars` for `DATABASE_URL` once this moves
past personal-project scale: `gcloud secrets create`, then
`--set-secrets DATABASE_URL=projects/.../secrets/database-url:latest`.

## Future: CI/CD via GitHub Actions

Not set up yet. When ready, the plan is:
1. Add a `Workload Identity Federation` binding (or a service-account key,
   less preferred) so GitHub Actions can auth to GCP without long-lived keys.
2. Add `.github/workflows/deploy.yml` that on push to `main`:
   - builds the Docker image
   - pushes to Artifact Registry
   - runs `gcloud run deploy` with the new image
3. Manual `gcloud run deploy` stays available as a fallback.

## Open items for later (not needed for the current placeholder stage)

- Whether the three projects eventually need per-project auth even though
  the dashboard itself doesn't.
- Whether a custom domain gets mapped to the Cloud Run service.
- Whether any project ends up needing background jobs / scheduled tasks
  (e.g. a grocery list reminder) — Cloud Run + Cloud Scheduler would be the
  natural fit, added only when a project actually needs it.
