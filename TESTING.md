# Testing Notes

Status of test coverage as of 2026-09-21, covering everything built so far:
Wine Cellar Tracker, Grocery List, Recipe Tracker, and the auth/permissions
system (accounts, login, per-project access, admin panel). Written as a
reference for picking this back up later — what's covered, what isn't, and
how to run it.

## Setup

No virtualenv is committed (it's gitignored). To run the suite from scratch:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
python -m pytest tests/ -v
```

Tests run against an in-memory SQLite database (`tests/conftest.py`), so they
never touch the Neon/Postgres database configured for dev or prod.

## Scope

**Wine Cellar Tracker**, **Grocery List**, **Recipe Tracker**, and the
**auth/admin system** all have real behavior and full test coverage. `core`
is a static dashboard, covered indirectly by the cross-blueprint navigation
test in `test_wine_cellar_integration.py`. `honeymoon` and `investing` are
still placeholder pages with no logic — no dedicated tests for their
placeholder content, but their access-control gate (403 without a grant,
200 with one) is covered by the parametrized tests in `test_auth.py` along
with every other project's gate.

## Test files

- **`tests/test_wine_cellar.py`** — pre-existing, one test per route, kept
  as-is.
- **`tests/test_wine_cellar_unit.py`** (new) — pure logic, no HTTP, no
  database session:
  - `Bottle.drink_status()` — the cellar/ready/past/None classification
    based on the current year vs. the drink window, including both boundary
    years.
  - `_parse_int`, `_parse_decimal`, `_parse_date` — the form-field coercion
    helpers in `app/blueprints/wine_cellar/routes.py`.
  - `_bottle_from_form` — every validation branch (missing name, negative/
    non-numeric quantity, non-numeric vintage, inverted drink window,
    non-numeric price, invalid date), and that blank optional fields become
    `None` while whitespace gets stripped.
- **`tests/test_grocery_list.py`** — pre-existing (added alongside the
  Grocery List build-out), covers adding/editing/deleting items, the
  active-list vs. catalog toggle, category grouping, and bulk clear.
- **`tests/test_recipe_tracker.py`** — added alongside
  the Recipe Tracker build-out (`Recipe` + `RecipeIngredient` models, fixed
  `CUISINES`/`MEAL_TYPES` lists — see `app/blueprints/recipe_tracker/models.py`).
  Route-level tests, all against the real in-memory database:
  - Add a recipe with multiple ingredients and confirm it appears in the
    list.
  - Validation: title is required, and at least one ingredient is required
    (a submit with only blank ingredient rows is rejected).
  - Detail page shows ingredients (in `sort_order`) and instructions.
  - Edit replaces both the recipe fields and its full ingredient set —
    confirms the old `RecipeIngredient` rows are gone and only the newly
    submitted ones remain (exercises the `cascade="all, delete-orphan"`
    relationship in the model).
  - Delete removes the recipe and its ingredients (cascade via
    `ondelete="CASCADE"` on the FK).
  - Search matches on both recipe title and ingredient name.
  - Filtering by `cuisine` and `meal_type` independently.
- **`tests/test_wine_cellar_integration.py`** (new) — full request/response
  cycles through the Flask test client and the real (in-memory) database:
  - Cross-blueprint navigation: dashboard lists all projects; Grocery List
    and Recipe Tracker both render their live pages (updated from an earlier
    version of this test that asserted Recipe Tracker's placeholder — now
    stale since it's built out).
  - Full bottle lifecycle in one test: add → edit → drink twice → delete,
    checking the list view, the drink-window badge, and that tasting
    history survives bottle deletion with `bottle_id` set to `NULL` (see
    `ondelete="SET NULL"` in `models.py`).
  - **Documented surprising behavior**: `edit` rebuilds the row from
    whatever fields are posted, so omitting an optional field on a resubmit
    (e.g. a form that doesn't include `producer`) writes it back as `None`
    rather than leaving the stored value alone. `test_edit_with_partial_form_clears_unset_fields`
    pins this down so a future change to make edits merge-only is a
    deliberate decision, not an accidental behavior change.
  - Validation round-trips: invalid `add`/`drink` submissions re-render the
    form with the user's entered values intact, and don't write to the
    database.
  - Drink edge cases: blocked at zero quantity, rejected out-of-range
    rating leaves quantity/history untouched, omitting rating/notes stores
    `NULL`s.
  - 404s for edit/drink/delete on an unknown bottle id.
  - Search: case-insensitivity across name/producer/varietal/region, and the
    "no matches" message.
  - Tasting history ordering (most recent first).
- **`tests/test_auth.py`** — accounts, login, and the site-wide + per-project
  access gates:
  - Signup: succeeds with zero project access, rejects a duplicate
    username, rejects a too-short password, rejects mismatched
    password/confirm.
  - Login: succeeds with correct credentials, fails (generic error, no
    username enumeration) on wrong password or unknown username.
  - `logout` requires POST (405 on GET); an anonymous visitor hitting any
    page gets redirected to `/login`.
  - The `next` redirect round-trips correctly after login, and a crafted
    open-redirect `next` value (`https://evil.com`, `//evil.com`) is
    rejected and falls back to the dashboard.
  - **Parametrized across all five project routes** (wine-cellar,
    grocery-list, recipe-tracker, honeymoon, investing) — added
    specifically to close a gap where only wine-cellar's gate was tested:
    `test_user_without_project_access_gets_403` and
    `test_user_with_project_access_gets_200`.
  - Dashboard tile filtering: hidden entirely without access, all shown
    with full access.
  - The `flask create-admin` CLI: creates an admin, rejects a duplicate
    username.
- **`tests/test_admin.py`** — the `/admin` panel, all gated by `is_admin`:
  - Rejected for a non-admin (403) and for an anonymous visitor (redirected
    to login by the global gate before the admin check even runs).
  - Lists all users.
  - Granting and revoking per-project access via the toggle endpoint,
    confirmed both in the database and by the target route flipping
    between 403/200.
  - Rejects toggling a project key that doesn't exist (404).
  - Promoting/demoting another user's admin status.
  - An admin can't demote themselves (self-demote guard) — and separately,
    `toggle_admin`'s guard is written against the actual "at least one
    admin must exist" invariant (a count check), not just self-demotion,
    so it also covers any future path that could zero out admins.
  - Admin-initiated password reset: works (the user can log in with the
    new password), and rejects a too-short one.

## Running a subset

```bash
python -m pytest tests/test_wine_cellar_unit.py -v          # unit only
python -m pytest tests/test_wine_cellar_integration.py -v   # integration only
```

As of this writing, the full suite is **104 tests**, all passing (`python -m
pytest tests/ -v`).

## End-to-end verification (production, manual)

The above are all pytest, running against an in-memory SQLite database —
they never touch the real deployment. Separately, after the fix for the
"missing database table" 500 error (`app/__init__.py`'s auto `db.create_all()`
for the SQLite fallback, plus wiring the Neon database via Secret Manager),
the live Cloud Run service was checked directly, by hand rather than as an
automated test:

- **All five routes checked against the live URL** (`curl -o /dev/null -w
  "%{http_code}"` against `/`, `/wine-cellar/`, `/grocery-list/`,
  `/recipe-tracker/`, `/honeymoon/`) — all returned 200 after the redeploy.
  Before the fix, `/wine-cellar/` and `/grocery-list/` both 500'd.
- **Confirmed the service is actually talking to Neon, not the local SQLite
  fallback**, two ways: (1) `gcloud run services describe` shows
  `DATABASE_URL` sourced from the `database-url` Secret Manager secret, and
  (2) `gcloud run services logs read` showed a genuine
  `psycopg2.errors.UndefinedTable` error in the window before `flask
  init-db` was run against Neon — that error only comes from real Postgres;
  SQLite raises `sqlite3.OperationalError: no such table` instead, so its
  presence is direct proof of a live Postgres connection.
- **Full user flow confirmed via production logs**, not just page loads:
  add a bottle (`POST /wine-cellar/add` → 302), use the Drink action
  (`POST /wine-cellar/1/drink` → 302), and check Tasting History (`GET
  /wine-cellar/history` → 200) — all captured in the Cloud Run request log
  with real timestamps.
- **Persistence re-confirmed on a later, separate request**: fetched
  `/wine-cellar/` again afterward and the bottle added during that manual
  test (a Chianti Classico) was still there — proof it's durable Postgres
  storage, not something that would vanish on container restart the way the
  SQLite fallback does.

This isn't scripted or repeatable as-is — it was ad hoc verification after a
specific deploy. See "Known gaps" below for turning this into something
that runs automatically.

**More recent manual verification (2026-09-21, after the auth/permissions
and Investing-tile deploys):** signup → auto-login → logout → manual login
walked through in a real browser against the live site, confirming the
whole auth flow works end-to-end in production, not just in pytest. Also
confirmed live: the new `investing` route 302s to login when logged out
(access gate active), and after the `pool_pre_ping` fix, no further
`SSL connection has been closed unexpectedly` errors in the logs.

## Known gaps / not covered

- No automated check that `flask db migrate` produces an empty diff (i.e.
  that models and the latest migration are in sync) — see "Database
  migrations" in `DEVELOPMENT_PLAN.md`. Would be a good CI addition once
  schema changes are more frequent: run `flask db migrate` against a fresh
  DB and fail if it generates a non-empty script.
- No template-rendering assertions beyond substring checks on response
  bytes; nothing verifies HTML structure/accessibility.
- No concurrency/race-condition tests for the feature routes (e.g. two
  simultaneous `drink` posts against the same bottle). Two such races
  *were* found and fixed on the auth/admin side (concurrent signup,
  concurrent access-toggle — both now catch `IntegrityError` gracefully,
  see `app/blueprints/auth/routes.py` and `app/blueprints/admin/routes.py`)
  but neither has an automated test proving the fix, since reliably
  triggering a DB-level race from a single-threaded test client isn't
  straightforward — verified manually instead at the time.
- `tests/test_recipe_tracker.py` isn't split into unit/integration files the
  way Wine Cellar is — it's all route-level tests, same gap as Grocery List
  below. No unit coverage yet for the form-parsing helpers in
  `app/blueprints/recipe_tracker/routes.py` (`_ingredients_from_form`,
  `_recipe_from_form`, `_parse_optional_int`).
- The end-to-end production verification above is **manual and ad hoc**, not
  an automated test — it was run by hand after a specific deploy, using
  `curl` and `gcloud run services logs read`. There's no scripted smoke test
  that hits the live URL as part of the deploy process, so a regression on
  the live site wouldn't be caught automatically the way a broken pytest
  would. Worth adding as a lightweight script (hit each route, check for
  200) if deploys become more frequent than they are now.
- `tests/test_grocery_list.py` isn't split into unit/integration files the
  way Wine Cellar is; it's all route-level tests. Worth revisiting if its
  form-parsing logic (`_item_from_form`, `_group_by_category` in
  `app/blueprints/grocery_list/routes.py`) grows complex enough to warrant
  isolated unit tests.
