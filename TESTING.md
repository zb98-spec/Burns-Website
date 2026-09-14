# Testing Notes

Status of test coverage as of 2026-09-13, covering everything built so far
(commits `c356eb3` scaffold, `0e36ff9` Wine Cellar Tracker, and `540397d`
Grocery List). Written as a reference for picking this back up later — what's
covered, what isn't, and how to run it.

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

**Wine Cellar Tracker** and **Grocery List** both have real behavior and
full test coverage. `core` is a static dashboard and `recipe_tracker` is
still a placeholder page with no logic, covered by a smoke test confirming
the placeholder renders; it doesn't need more until it's built out.

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
- **`tests/test_wine_cellar_integration.py`** (new) — full request/response
  cycles through the Flask test client and the real (in-memory) database:
  - Cross-blueprint navigation: dashboard lists all three projects; the
    live Grocery List page renders and recipe tracker renders its
    placeholder page.
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

## Running a subset

```bash
python -m pytest tests/test_wine_cellar_unit.py -v          # unit only
python -m pytest tests/test_wine_cellar_integration.py -v   # integration only
```

## Known gaps / not covered

- No tests for the `flask init-db` CLI command (`app/__init__.py`) — it's a
  thin wrapper around `db.create_all()`.
- No template-rendering assertions beyond substring checks on response
  bytes; nothing verifies HTML structure/accessibility.
- No concurrency/race-condition tests (e.g. two simultaneous `drink` posts
  against the same bottle) — the app has no auth or multi-user concept yet,
  so this hasn't been a priority.
- Recipe Tracker has no real tests because it has no real behavior yet.
  Revisit this file when it's built out — follow the same unit/integration
  split used for Wine Cellar.
- `tests/test_grocery_list.py` isn't split into unit/integration files the
  way Wine Cellar is; it's all route-level tests. Worth revisiting if its
  form-parsing logic (`_item_from_form`, `_group_by_category` in
  `app/blueprints/grocery_list/routes.py`) grows complex enough to warrant
  isolated unit tests.
