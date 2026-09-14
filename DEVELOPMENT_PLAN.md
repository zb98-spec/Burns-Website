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

- Landing page with 4 tiles (Wine Cellar Tracker, Grocery List, Recipe
  Tracker, Honeymoon)
- **Wine Cellar Tracker is built out**: add/edit/delete bottles, a searchable
  table view, drink-window badges, a "Drink" action that decrements quantity
  and logs to a separate Tasting History page. See its own section below.
- **Grocery List is built out**: a running household list grouped by fixed
  category, with a separate catalog view of past items to re-add.
- **Recipe Tracker is built out**: add/edit/delete recipes with structured
  ingredients (quantity/unit/name rows), fixed cuisine/meal-type categories,
  search across title and ingredients, and filter by cuisine/meal type. See
  its own section below.
- Flask-SQLAlchemy is wired up, defaulting to a local SQLite file
  (`instance/dev.db`) until `DATABASE_URL` (Neon) is set
- No authentication

## Project structure

```
Burns-Website/
├── app/
│   ├── __init__.py              # create_app() factory, registers all blueprints, `flask init-db` CLI command
│   ├── extensions.py            # shared `db = SQLAlchemy()` instance
│   ├── templates/
│   │   ├── base.html            # shared layout (header, flash messages, CSS link)
│   │   └── placeholder.html     # shared "not built yet" page
│   ├── static/css/style.css     # single stylesheet, no build step
│   └── blueprints/
│       ├── core/                             # landing page + tile list
│       │   ├── routes.py
│       │   └── templates/core/index.html
│       ├── wine_cellar/                       # built out — see "Wine Cellar Tracker" below
│       │   ├── routes.py
│       │   ├── models.py                      # Bottle, TastingHistory
│       │   └── templates/wine_cellar/         # index, form, drink, history
│       ├── grocery_list/                      # built out — item list + catalog
│       │   ├── routes.py
│       │   ├── models.py                      # GroceryItem
│       │   └── templates/grocery_list/        # index, catalog, form
│       └── recipe_tracker/                    # built out — see "Recipe Tracker" below
│           ├── routes.py
│           ├── models.py                      # Recipe, RecipeIngredient
│           └── templates/recipe_tracker/      # index, form, detail
├── config.py                    # env-based config (SECRET_KEY, DATABASE_URL, SQLALCHEMY_*)
├── wsgi.py                      # entrypoint for gunicorn / `python wsgi.py`
├── tests/                       # pytest suite (currently covers wine_cellar)
├── requirements.txt
├── requirements-dev.txt         # requirements.txt + pytest
├── Dockerfile
├── .dockerignore
├── .gitignore
├── .env.example
└── DEVELOPMENT_PLAN.md          # this file
```

**Template naming gotcha:** Flask blueprint template loaders are not scoped
to the current blueprint — if two blueprints each register a template with
the same filename (e.g. two `index.html`), whichever blueprint was
registered first in `create_app()` silently wins for *both* routes. Every
blueprint here uses `template_folder="templates"` and renders templates as
`"<blueprint_name>/<template>.html"` (e.g. `"wine_cellar/index.html"`) to
namespace them — keep following that pattern for new projects.

## How to build out a project independently

Each project lives entirely inside its own `app/blueprints/<project>/`
folder. Using the Wine Cellar Tracker as the template to copy:

1. Add a `models.py` in that folder with `db.Model` classes from
   `app.extensions`. Prefix table names with the project name
   (`wine_bottles`, not `bottles`) rather than using a Postgres schema — it
   keeps the same models working against local SQLite and Neon Postgres
   with no code changes (see "Database" below).
2. Add routes to `app/blueprints/<project>/routes.py`, importing that
   blueprint's own `db` session via `from app.extensions import db`.
3. Add templates under `app/blueprints/<project>/templates/<project>/`,
   and register the blueprint with `template_folder="templates"` — render
   with the `"<project>/<template>.html"` path (see the template naming
   gotcha above).
4. If the blueprint defines new models, import them inside the `init_db`
   CLI command in `app/__init__.py` so `flask init-db` creates their tables
   too (see how `wine_cellar.models` is imported there).
5. Flip its `status` from `"coming soon"` to `"live"` in
   `app/blueprints/core/routes.py` (`PROJECTS` list) once the index route
   is ready.
6. No other blueprint needs to change. The app factory in `app/__init__.py`
   already registers all four blueprints, so routing "just works" as soon
   as a project's `index()` view exists.

This keeps projects decoupled while still shipping as one small container
and one Cloud Run service — no need to stand up new infra per project.

## Wine Cellar Tracker

The first built-out project. Reference implementation for future projects.

- **Data model** (`app/blueprints/wine_cellar/models.py`):
  - `Bottle` (table `wine_bottles`) — one row per distinct wine, not per
    physical bottle, with a `quantity` count. Fields: name, producer,
    vintage, varietal, region, quantity, location, purchase price/date/
    source, drink window (start/end year).
  - `TastingHistory` (table `wine_tasting_history`) — one row per bottle
    actually drunk. Stores a snapshot of the wine's name/producer/vintage
    at drink time (plus a nullable `bottle_id` FK) so history stays
    meaningful even if the original bottle entry is later edited or
    deleted. Holds `consumed_date`, `rating` (0–100), and free-text `notes`.
- **Behavior:**
  - The bottle list (`/wine-cellar/`) only shows bottles with `quantity > 0`,
    sorted by name, with a text search across name/producer/varietal/region.
  - A "Drink" action (`/wine-cellar/<id>/drink`) decrements `quantity` by 1
    and creates one `TastingHistory` row (optional rating/notes, date
    defaults to today). The bottle drops off the main list once quantity
    hits 0, but the row itself isn't deleted — history keeps referencing it.
  - Drink-window badges ("Cellar" / "Drink now" / "Past window") are computed
    from the current year vs. `drink_window_start`/`drink_window_end` —
    no separate filter view, just inline in the table.
  - Deleting a bottle (`/wine-cellar/<id>/delete`) nulls out `bottle_id` on
    any related history rows rather than cascading the delete, so tasting
    history is never destroyed by cleaning up the cellar list.
- **Forms:** plain HTML + manual server-side validation (required fields,
  numeric ranges, drink-window ordering) with flash messages — no
  Flask-WTF, to stay dependency-light.
- **Tests:** `tests/test_wine_cellar.py` covers add/edit/delete, the drink
  → history flow, the quantity-reaches-zero list behavior, and search.

## Recipe Tracker

A personal recipe box: store recipes with structured ingredients, search
and filter by title/ingredient/category. No meal planning, no cook-history
log, no photo upload in this first pass (see rationale below).

- **Data model** (`app/blueprints/recipe_tracker/models.py`):
  - `Recipe` (table `recipe_recipes`) — one row per recipe. Fields: title
    (required), instructions (required, free-text steps), servings
    (free-text string, e.g. `"4"` or `"4-6"` — not a strict integer, since
    yields aren't always a single number), prep_time_minutes,
    cook_time_minutes, cuisine, meal_type, source_url, source_name,
    created_at.
  - `RecipeIngredient` (table `recipe_ingredients`) — one row per
    ingredient line. Fields: recipe_id (FK, `ondelete="CASCADE"`),
    quantity (free-text string, e.g. `"1 1/2"`, to allow fractions),
    unit, name (required), sort_order (preserves the ingredient list's
    order, since SQL row order isn't guaranteed). Unlike the wine cellar's
    `TastingHistory`, ingredients have no meaning outside their recipe, so
    deleting a recipe cascades to delete its ingredients (no soft-orphan
    pattern needed here).
  - `cuisine` and `meal_type` are plain string columns validated against a
    **fixed list defined in code** (not a database-backed tag table) —
    rendered as `<select>` dropdowns in the form. Starting lists (easy to
    extend later by editing the constant, no migration needed since it's
    not its own table):
    - Cuisine: American, Italian, Mexican, Chinese, Indian, French,
      Mediterranean, Thai, Japanese, Other
    - Meal type: Breakfast, Lunch, Dinner, Dessert, Snack, Appetizer,
      Side, Drink
- **Behavior:**
  - `/recipe-tracker/` — index: searchable (title + ingredient name) and
    filterable (cuisine, meal type) list view, similar in spirit to the
    wine cellar's search box.
  - `/recipe-tracker/<id>` — detail view: full ingredient list + instructions.
  - `/recipe-tracker/new` and `/recipe-tracker/<id>/edit` — add/edit form.
    Ingredient rows are added/removed client-side with plain vanilla JS
    (matching the "minimal vanilla JS" stack decision) and posted as
    same-named repeated form fields (`ingredient_quantity`,
    `ingredient_unit`, `ingredient_name`), parsed server-side by
    position — this is the one place more custom parsing logic is needed
    than the wine cellar form required, since wine cellar has no
    repeating sub-rows. At least one ingredient with a name is required.
  - `/recipe-tracker/<id>/delete` — deletes the recipe; ingredients
    cascade-delete with it.
  - Forms use the same plain HTML + manual server-side validation pattern
    as wine cellar (required fields, no Flask-WTF).
- **Ingredient data shape is deliberately structured** (not a single free
  text block) specifically so a *future* "send ingredients to Grocery
  List" feature can consume it without a data-model rewrite — that
  integration itself is out of scope for this build; Grocery List and
  Recipe Tracker stay independently decoupled for now, per the existing
  "keep projects decoupled" approach.
- **Explicitly deferred to `FEATURE_BACKLOG.md`:** photo upload (blocked
  on real object storage — Cloud Run's filesystem doesn't persist, same
  issue as the SQLite fallback noted there) and a cook-history/ratings
  log (could mirror `TastingHistory` later if wanted).
- **Tests:** `tests/test_recipe_tracker.py`, mirroring
  `tests/test_wine_cellar.py` — add/edit/delete a recipe with multiple
  ingredients, cascade-delete of ingredients, search, and cuisine/meal-type
  filtering.
- **Rollout:** Recipe Tracker's `status` is `"live"` in
  `app/blueprints/core/routes.py` (`PROJECTS` list), and
  `recipe_tracker.models` is imported in the `init-db` CLI command in
  `app/__init__.py` so `flask init-db` creates its tables.

## Local development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt   # includes requirements.txt + pytest
cp .env.example .env   # fill in SECRET_KEY / DATABASE_URL as needed
flask --app wsgi init-db   # creates tables in instance/dev.db (SQLite) or Neon if DATABASE_URL is set
python wsgi.py              # http://localhost:8080
```

Run tests with `pytest` (uses an in-memory SQLite DB, no setup needed).

## Database (Neon)

- One Neon project for the whole site.
- Rather than a Postgres schema per app, tables are **name-prefixed** per
  project (`wine_bottles`, `wine_tasting_history`, and future
  `grocery_*` / `recipes_*` tables) inside the one default schema. This was
  changed from the original schema-per-app plan because Postgres schemas
  don't translate to SQLite, and prefixed table names let the exact same
  SQLAlchemy models run locally (SQLite) and in production (Neon Postgres)
  with zero code changes.
- `DATABASE_URL` (from `.env` locally, from Cloud Run env vars / Secret
  Manager in production) is the single connection string shared by all
  blueprints. If unset, `config.py` falls back to a local SQLite file at
  `instance/dev.db`.
- **Tables are not created automatically.** Run `flask --app wsgi init-db`
  once against a fresh database (local SQLite or a new Neon database) to
  create all registered models' tables. There's no Alembic/migrations yet
  (see "Wine Cellar Tracker" note above) — schema changes after the first
  deploy will need a manual `ALTER TABLE` or a full re-run of `init-db`
  against a fresh database until migrations are added.

## Docker

```bash
docker build -t burns-dashboard .
docker run -p 8080:8080 --env-file .env burns-dashboard
# first run only (or after adding new models): create tables inside the container
docker exec <container_name> flask --app wsgi init-db
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

**After the first deploy against a fresh Neon database**, run `flask
--app wsgi init-db` once with `DATABASE_URL` pointed at Neon (e.g. from your
own machine with the Neon connection string in your env) to create the
tables — Cloud Run doesn't run this automatically.

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
