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
| Auth | Local accounts (username + password, Flask-Login), whole site behind login, per-project access grants managed by admins — see "Authentication & Access Control" below |
| Structure | One Flask app, one Blueprint per project, one Cloud Run service |
| Database | One Neon Postgres project; tables are name-prefixed per app (`wine_*`, `grocery_*`, `recipe_*`) in the default schema — see "Database (Neon)" below |
| Schema changes | Flask-Migrate/Alembic — versioned migration scripts, not ad hoc `create_all()` — see "Database migrations" below |
| Container | Single Dockerfile, gunicorn as the WSGI server |
| Hosting | Google Cloud Run (scales to zero, no cluster to manage) |
| Deploys | Manual (`gcloud run deploy`) for now; CI (tests via GitHub Actions) exists, CD (auto-deploy) doesn't yet |
| Repo | New GitHub repo, created as part of setup |
| Domain | Default `*.run.app` URL for now; custom domain can be mapped later |

## Current status

- Landing page with 5 tiles (Wine Cellar Tracker, Grocery List, Recipe
  Tracker, Honeymoon, Investing)
- **Wine Cellar Tracker is built out**, as two pages: a Cellar (add/edit/
  delete bottles, searchable table, drink-window badges, a "Drink" action
  that decrements quantity and logs a tasting) and a Wine Tasting page (a
  card grid of every tasting — cellar-linked or logged standalone — each
  with an optional photo and a multi-person average score you can hover to
  break down). See its own section below.
- **Grocery List is built out**: a running household list grouped by fixed
  category, with a separate catalog view of past items to re-add.
- **Recipe Tracker is built out**: add/edit/delete recipes with structured
  ingredients (quantity/unit/name rows), fixed cuisine/meal-type categories,
  search across title and ingredients, and filter by cuisine/meal type. See
  its own section below.
- **Honeymoon** is a placeholder tile — no functionality yet.
- **Investing** is a placeholder tile — no functionality yet, and won't
  become a blueprint here. Per `INVESTMENT_ENGINE_HANDOFF.md`, its actual
  functionality (direct indexing, DCA, tax-loss harvesting) is planned as
  a separate, independently-developed API/service integrating over HTTP,
  not a blueprint in this repo. This tile is just the dashboard entry
  point for it.
- Flask-SQLAlchemy is wired up, defaulting to a local SQLite file
  (`instance/dev.db`) until `DATABASE_URL` (Neon) is set
- **The whole site requires login.** Accounts are local (username +
  password, no email), self-service signup starts with zero project
  access, and admins grant per-project access + can promote other admins.
  See "Authentication & Access Control" below.

## Project structure

```
Burns-Website/
├── app/
│   ├── __init__.py              # create_app() factory, registers all blueprints
│   ├── extensions.py            # shared `db = SQLAlchemy()` and `migrate = Migrate()` instances
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
│       ├── recipe_tracker/                    # built out — see "Recipe Tracker" below
│       │   ├── routes.py
│       │   ├── models.py                      # Recipe, RecipeIngredient
│       │   └── templates/recipe_tracker/      # index, form, detail
│       ├── honeymoon/                         # placeholder — no functionality yet
│       │   └── routes.py
│       ├── investing/                         # placeholder — see "Current status" above; real
│       │   └── routes.py                      # functionality planned as a separate service, not here
│       ├── auth/                              # login, logout, create-account — see "Authentication" below
│       │   ├── routes.py
│       │   ├── models.py                      # User, UserProjectAccess
│       │   ├── access.py                      # require_project_access(), safe_redirect_target()
│       │   └── templates/auth/                # login, create_account
│       └── admin/                             # admin-only user/permission management
│           ├── routes.py
│           └── templates/admin/               # users
├── migrations/                  # Flask-Migrate/Alembic — versioned schema changes, see
│                                 # "Database migrations" below. Committed, not gitignored.
├── config.py                    # env-based config (SECRET_KEY, DATABASE_URL, SQLALCHEMY_*)
├── wsgi.py                      # entrypoint for gunicorn / `python wsgi.py`
├── tests/                       # pytest suite — 104 tests: wine_cellar, grocery_list,
│                                 # recipe_tracker, auth, admin (see TESTING.md)
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
4. If the blueprint defines new models (or you change an existing one),
   generate a migration: `flask db migrate -m "add <project> tables"`, then
   review the generated script under `migrations/versions/` before
   committing it. See "Database migrations" below for the full workflow —
   models alone don't create tables anymore; the migration does.
5. Add an access-control gate: a `"key"` entry in its `PROJECTS` dict (used
   by `UserProjectAccess`, independent of routing), and a one-line
   `@<project>_bp.before_request` calling
   `require_project_access("<key>")` (from `app.blueprints.auth.access`) —
   copy the pattern from any existing project blueprint. Without this, the
   project would be reachable by any logged-in user regardless of what an
   admin granted them.
6. Flip its `status` from `"coming soon"` to `"live"` in
   `app/blueprints/core/routes.py` (`PROJECTS` list) once the index route
   is ready.
7. No other blueprint needs to change. The app factory in `app/__init__.py`
   already registers all blueprints, so routing "just works" as soon as a
   project's `index()` view exists.

This keeps projects decoupled while still shipping as one small container
and one Cloud Run service — no need to stand up new infra per project.

## Wine Cellar Tracker

The first built-out project. Reference implementation for future projects.
Two pages: the Cellar (`/wine-cellar/`, inventory) and Wine Tasting
(`/wine-cellar/history`, a log of tastings — from the cellar or not).

- **Data model** (`app/blueprints/wine_cellar/models.py`):
  - `Bottle` (table `wine_bottles`) — one row per distinct wine, not per
    physical bottle, with a `quantity` count. Fields: name, producer,
    vintage, varietal, region, quantity, location, purchase price/date/
    source, drink window (start/end year).
  - `TastingHistory` (table `wine_tasting_history`) — one row per tasting.
    Stores a snapshot of the wine's name/producer/vintage at tasting time
    (plus a nullable `bottle_id` FK) so history stays meaningful even if
    the original bottle entry is later edited or deleted — and so a
    tasting can exist with no cellar entry at all. Holds `consumed_date`,
    free-text `notes`, and an optional `image`/`image_mimetype` (raw bytes
    stored directly in Postgres — see "Tasting photos" below).
  - `TastingScore` (table `wine_tasting_scores`) — one row per taster's
    score (0–100) for a tasting, `tasting_id` FK with `ondelete="CASCADE"`.
    Replaces an earlier single `rating` int column: a tasting can have
    several people's scores, not just one. `TastingHistory.average_score`
    (a Python property, not a stored column) averages them; `None` if
    nobody's scored it yet.
- **Behavior:**
  - The bottle list (`/wine-cellar/`) only shows bottles with `quantity > 0`,
    sorted by name, with a text search across name/producer/varietal/region.
  - A "Drink" action (`/wine-cellar/<id>/drink`) decrements `quantity` by 1
    and creates one `TastingHistory` row. The bottle drops off the main
    list once quantity hits 0, but the row itself isn't deleted — history
    keeps referencing it.
  - "Add a Tasting" (`/wine-cellar/tastings/add`) logs a tasting with no
    cellar bottle involved at all — free-text wine name/producer/vintage
    instead of picking a `Bottle`, `bottle_id` stays `None`, no quantity
    change. Same scores/photo/notes fields as the cellar-linked drink form.
  - Both tasting forms share one partial
    (`templates/wine_cellar/_tasting_fields.html`) for the repeatable
    taster-name/score rows and the photo input, so the two flows can't
    drift apart. Score rows use the same "clone a `<template>`" vanilla-JS
    pattern as Recipe Tracker's ingredient rows (`_scores_from_form` in
    `routes.py` parses them back with `request.form.getlist(...)`).
  - Drink-window badges ("Cellar" / "Drink now" / "Past window") are computed
    from the current year vs. `drink_window_start`/`drink_window_end` —
    no separate filter view, just inline in the table.
  - Deleting a bottle (`/wine-cellar/<id>/delete`) nulls out `bottle_id` on
    any related history rows rather than cascading the delete, so tasting
    history is never destroyed by cleaning up the cellar list.
  - The tasting page (`/wine-cellar/history`) renders as a card grid, not a
    table: each card shows the average-score badge, and hovering (or
    focusing, for keyboard use) reveals a popover with every taster's
    individual score — CSS `:hover`/`:focus-within`, no JS needed for that
    part.
- **Tasting photos:** uploaded as `multipart/form-data`, validated to be an
  `image/*` mimetype, and stored as raw bytes on the `TastingHistory` row
  itself rather than on disk. This is deliberate: the app runs on Cloud Run,
  which wipes local container disk on every scale-to-zero/restart, and no
  object storage (e.g. a GCS bucket) is wired up for this project — Neon
  Postgres is the only durable storage that already exists. Served back via
  `/wine-cellar/tastings/<id>/image`, which sets `Content-Type` from the
  stored mimetype. Fine at personal-cellar scale; would need to move to
  object storage if photo volume ever got large.
- **Forms:** plain HTML + manual server-side validation (required fields,
  numeric ranges, drink-window ordering, score range, image mimetype) with
  flash messages — no Flask-WTF, to stay dependency-light.
- **Tests:** `tests/test_wine_cellar_unit.py` (pure functions: form parsing,
  `_scores_from_form`, `_image_from_files`, `average_score`),
  `tests/test_wine_cellar.py` (feature-level: add/edit/delete, both tasting
  flows, scores, image upload/serve round-trip), `tests/test_wine_cellar_
  integration.py` (cross-page flows: nav links, card rendering, full
  bottle lifecycle).

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
  `app/blueprints/core/routes.py` (`PROJECTS` list). Its tables
  (`recipe_recipes`, `recipe_ingredients`) are part of the baseline
  migration in `migrations/versions/` — see "Database migrations" below.

## Authentication & Access Control

The whole site sits behind a login. There's no email anywhere in this
system — accounts are just a username and password.

- **Data model** (`app/blueprints/auth/models.py`):
  - `User` (table `auth_users`, `UserMixin` for Flask-Login) — username
    (unique, stored/compared lowercase), password_hash (werkzeug's
    `generate_password_hash`/`check_password_hash`, no extra hashing
    dependency), `is_admin`, created_at.
  - `UserProjectAccess` (table `auth_user_project_access`) — join table:
    `(user_id, project_key)`, unique together. A row's presence is the
    grant; there's no "denied" state to represent. `ondelete="CASCADE"` so
    deleting a user (no admin UI for that yet, see `FEATURE_BACKLOG.md`)
    would clean up its grants automatically.
  - `User.has_access(project_key)` is the single source of truth for "can
    this user see/use this project" — it returns `True` unconditionally
    for admins (they bypass all per-project grants) before checking
    `UserProjectAccess`. Both the dashboard's tile filtering and each
    project blueprint's access gate call this same method.
- **Two-layer access control:**
  1. **Global "must be logged in"** — one `@app.before_request` hook in
     `create_app()`, exempting only `auth.login`, `auth.create_account`,
     and `static`. Redirects anonymous visitors to `/login?next=<path>`.
  2. **Per-project "must have this project"** — `require_project_access(key)`
     (`app/blueprints/auth/access.py`), called from a one-line
     `before_request` in each project blueprint (`wine_cellar`,
     `grocery_list`, `recipe_tracker`, `honeymoon`). 403s if the user
     lacks that project's grant. New projects need this too — see step 5
     in "How to build out a project independently" above.
  - The dashboard (`core.index()`) filters `PROJECTS` down to what the
    current user can see before rendering — a tile without access doesn't
    appear at all, rather than showing disabled.
- **`next`-param redirect is validated** (`safe_redirect_target()` in
  `access.py`) — only same-site relative paths are honored, to close an
  open-redirect hole a crafted `?next=` could otherwise open.
- **Session cookies are hardened** in `config.py`:
  `SESSION_COOKIE_HTTPONLY`, `SESSION_COOKIE_SAMESITE="Lax"`, and
  `SESSION_COOKIE_SECURE` conditional on `DATABASE_URL` being set (i.e.
  prod) — hardcoding `Secure` would silently break login over plain-HTTP
  local dev.
- **CSRF (Flask-WTF) is explicitly deferred** — see `FEATURE_BACKLOG.md`.
  `SameSite=Lax` above is a partial mitigation, not a replacement.
- **Self-service signup**: `/create-account` — new accounts start with
  `is_admin=False` and zero `UserProjectAccess` rows. An admin has to
  grant access to anything before the account is useful.
- **Admin panel** (`app/blueprints/admin/`, `/admin`, gated by
  `current_user.is_admin`): lists every user with a checkbox per project
  key, an "is admin" toggle (an admin can't demote themselves, to avoid
  accidentally locking everyone out), and a "set new password" action —
  the only account-recovery path that exists, since there's no email to
  send a reset link to.
- **Bootstrapping the first admin**: `flask create-admin` (prompts for
  username/password if not passed as `--username`/`--password`) — needed
  once per fresh database (local, or Neon after first deploy — see
  "Deploying" below), since a brand-new database has no admin at all.
- **Login errors are generic** ("Invalid username or password" for both
  unknown-username and wrong-password) to avoid trivial username
  enumeration via the login form.
- **Tests**: `tests/test_auth.py` (signup, login/logout, the `next`
  round-trip, the open-redirect rejection, per-project 403 vs 200,
  dashboard filtering, the `create-admin` CLI) and `tests/test_admin.py`
  (admin-only 403, granting/revoking access, promote/demote, the
  self-demote guard, password reset). `tests/conftest.py`'s `client`
  fixture logs in a non-admin user with access to every project, so all
  the pre-existing feature tests keep exercising the same routes as
  before auth existed, unmodified.

## Local development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt   # includes requirements.txt + pytest
cp .env.example .env   # fill in SECRET_KEY / DATABASE_URL as needed
flask --app wsgi create-admin   # first time only — prompts for username/password
python wsgi.py          # http://localhost:8080
```

No extra setup step needed for local SQLite — tables are auto-created at
startup (see "Database migrations" below for why this is SQLite-only, not
how Neon is handled). If you point `DATABASE_URL` at a real Postgres
database (including Neon) for local testing, run `flask db upgrade` first
to create its tables — the auto-create-on-startup only applies to the
local SQLite fallback.

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
- `DATABASE_URL` (from `.env` locally, from Cloud Run Secret Manager in
  production — see "Deploying" below) is the single connection string
  shared by all blueprints. If unset, `config.py` falls back to a local
  SQLite file at `instance/dev.db`.
- The live service's `DATABASE_URL` is stored in Secret Manager as the
  `database-url` secret and injected via `--set-secrets` — never a plain
  Cloud Run env var, so the password isn't visible in service config or
  the console.
- `SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}` (`config.py`) —
  Neon can silently close idle connections server-side; pre-ping tests a
  pooled connection with a cheap query before handing it out and
  transparently reconnects if it's dead, instead of the request 500ing
  with `psycopg2.OperationalError: SSL connection has been closed
  unexpectedly` (observed in production before this was added).

## Database migrations

Schema changes (new tables, new/changed columns) go through **Flask-Migrate**
(Alembic), not `db.create_all()`. This replaced an earlier manual
`flask init-db` CLI command that only knew how to create missing tables —
it silently did nothing for column changes to a table that already
existed, and it was easy to forget to run at all after a deploy (this
happened twice: once for Wine Cellar/Grocery List, once for Recipe
Tracker, both showing up as a live 500 until someone remembered to run it).

**The one thing that's still automatic:** when no `DATABASE_URL` is set,
`app/__init__.py` still auto-runs `db.create_all()` against the local
SQLite fallback at startup — that's a throwaway dev database with no
history worth tracking, so migrations don't apply to it. Any real database
(Neon, or a local Postgres you point `DATABASE_URL` at) is always managed
through migrations, never auto-created.

**Workflow for a schema change:**
1. Change (or add) a model in `app/blueprints/<project>/models.py`.
2. Generate a migration script:
   ```bash
   flask --app wsgi db migrate -m "describe the change"
   ```
   This connects to whatever `SQLALCHEMY_DATABASE_URI` currently resolves
   to (local SQLite by default) and diffs it against your models. **Always
   read the generated script under `migrations/versions/`** — Alembic's
   autogenerate is good but not perfect (e.g. it won't detect a plain
   column rename as a rename; it'll see it as a drop + add and lose data
   unless you edit the script to use `op.alter_column`).
3. Test it locally: `flask --app wsgi db upgrade`, confirm the app still
   works, then commit the migration script alongside the model change in
   the same PR.
4. After deploying (see "Deploying" below), apply the migration to Neon:
   ```bash
   gcloud run jobs execute burns-website-migrate --region us-central1
   ```
   This runs `flask db upgrade` inside a one-off Cloud Run Job using the
   same image and `DATABASE_URL` secret as the live service — safe to run
   after every deploy whether or not there's anything pending (`db upgrade`
   is a no-op if already up to date).

**SQLite portability:** `render_as_batch=True` is set on the `Migrate()`
instance in `app/extensions.py` — SQLite can't do most `ALTER TABLE`
variants directly, so Alembic rebuilds the table (batch mode) instead.
This only changes how migrations run against SQLite; Postgres is
unaffected.

**Bootstrapping note:** the baseline migration
(`migrations/versions/dbb3bcfbf3fe_baseline_*.py`) captures the schema as
it existed right before migrations were introduced — Wine Cellar, Grocery
List, and Recipe Tracker's tables all already existed on Neon by then
(created ad hoc via the old `init-db` command and, for Recipe Tracker, a
one-off Cloud Run Job). Rather than re-running `db upgrade` against
already-existing tables, Neon was **stamped** at the baseline revision
(`flask db stamp head`) — this records "the database is already at this
point" without re-running the `CREATE TABLE`s. You won't need to do this
again; it's a one-time step for adopting migrations on an existing
database. A genuinely fresh database (e.g. a new Neon project, or CI)
just runs `flask db upgrade` normally and gets everything from scratch.

## Docker

```bash
docker build -t burns-dashboard .
docker run -p 8080:8080 --env-file .env burns-dashboard
# if .env points DATABASE_URL at a real Postgres database, apply migrations first:
docker exec <container_name> flask --app wsgi db upgrade
```

(With no `DATABASE_URL` set, the local SQLite fallback auto-creates its own
tables at startup — no `docker exec` step needed in that case.)

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

`DATABASE_URL` is stored in Secret Manager (`database-url` secret) and
referenced with `--set-secrets DATABASE_URL=database-url:latest` rather
than passed as a plain `--set-env-vars` value — keeps the Neon password out
of service configs/console.

**After every deploy that includes a new migration**, apply it to Neon:
```bash
gcloud run jobs execute burns-website-migrate --region us-central1
```
Cloud Run doesn't run this automatically — see "Database migrations" above
for the full workflow and why `db upgrade` (not the old `init-db`) is what
this job runs.

**After the first deploy that includes the auth tables**, Neon has zero
admins until you run this once (from a machine with `DATABASE_URL` pointed
at Neon — see "Authentication & Access Control" above):
```bash
DATABASE_URL=<neon-connection-string> flask --app wsgi create-admin
```
Without this, `/admin` is unreachable on the live site — nobody can grant
themselves or anyone else access to anything.

## Future: CD (auto-deploy) via GitHub Actions

CI already exists — `.github/workflows/ci.yml` runs the pytest suite on
every push and PR. CD (automatic deploy on merge) doesn't yet; deploys are
still a manual `gcloud run deploy`, and applying migrations is a separate
manual `gcloud run jobs execute burns-website-migrate` after that. When
ready to automate:
1. Add a `Workload Identity Federation` binding (or a service-account key,
   less preferred) so GitHub Actions can auth to GCP without long-lived keys.
2. Add a deploy workflow that on push to `master`:
   - builds the Docker image
   - pushes to Artifact Registry
   - runs `gcloud run deploy` with the new image
   - runs `gcloud run jobs execute burns-website-migrate` to apply any
     pending migration
3. Manual `gcloud run deploy` (and the migrate job) stay available as a
   fallback.

## Open items for later (not needed for the current placeholder stage)

- Whether a custom domain gets mapped to the Cloud Run service.
- Whether any project ends up needing background jobs / scheduled tasks
  (e.g. a grocery list reminder) — Cloud Run + Cloud Scheduler would be the
  natural fit, added only when a project actually needs it.
