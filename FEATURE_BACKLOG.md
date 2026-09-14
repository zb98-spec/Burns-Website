# Feature Backlog

Ideas and known gaps that are deliberately deferred — not urgent enough to
block current work, but worth tracking so they don't get lost. Pull items
into active work when they're ready to be tackled.

## Infrastructure

- **Connect a real Neon Postgres database.** The deployed Cloud Run service
  currently has no `DATABASE_URL` set, so every project falls back to a
  local SQLite file created fresh inside the container (see
  `app/__init__.py`'s auto `db.create_all()`). This works — the app no
  longer 500s — but data doesn't persist: it's wiped on every container
  restart/redeploy, and if Cloud Run ever scales beyond one instance,
  each instance gets its own separate, inconsistent copy of the data.
  Fine as a throwaway dev database for now; needs to be replaced before
  the wine cellar or grocery list data actually matters.
  - When ready: create a Neon project, get the connection string, store it
    in Google Secret Manager (preferred over a plain Cloud Run env var —
    keeps the password out of service configs/console), and run
    `flask --app wsgi init-db` once against it to create tables.
- Set a real `SECRET_KEY` on the live Cloud Run service (currently falls
  back to the insecure `dev-only-change-me` default). Low urgency until
  there's session data worth protecting.
- CI/CD via GitHub Actions — deploys are manual (`gcloud run deploy`) for
  now, per `DEVELOPMENT_PLAN.md`.
- Confirm a GCP billing budget alert exists on the `burns-website-prod`
  project.

## Product ideas (uncommitted, just capturing)

- Wine Cellar: a "Ready to drink" filter/tab in addition to the inline
  drink-window badges, once the list grows large enough that scanning for
  the badge alone gets tedious.
- Wine Cellar: CSV import for bringing in an existing spreadsheet of
  bottles (explicitly deferred when originally scoped — manual entry only
  for the first build).
- Grocery List / Recipe Tracker: no specific ideas yet — revisit once
  Recipe Tracker is built out.
