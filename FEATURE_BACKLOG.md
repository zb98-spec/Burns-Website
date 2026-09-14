# Feature Backlog

Ideas and known gaps that are deliberately deferred — not urgent enough to
block current work, but worth tracking so they don't get lost. Pull items
into active work when they're ready to be tackled.

## Infrastructure

- Set a real `SECRET_KEY` on the live Cloud Run service (currently falls
  back to the insecure `dev-only-change-me` default). Low urgency until
  there's session data worth protecting.
- **CD (auto-deploy) via GitHub Actions.** CI already exists
  (`.github/workflows/ci.yml` — runs pytest on every push/PR) but deploys
  are still manual (`gcloud run deploy`), and applying pending migrations
  after a deploy is a separate manual step
  (`gcloud run jobs execute burns-website-migrate`) — see "Database
  migrations" in `DEVELOPMENT_PLAN.md`. Worth automating both once deploys
  become frequent enough that forgetting the migrate step is a real risk.
- Confirm a GCP billing budget alert exists on the `burns-website-prod`
  project.

## Product ideas (uncommitted, just capturing)

- Wine Cellar: a "Ready to drink" filter/tab in addition to the inline
  drink-window badges, once the list grows large enough that scanning for
  the badge alone gets tedious.
- Wine Cellar: CSV import for bringing in an existing spreadsheet of
  bottles (explicitly deferred when originally scoped — manual entry only
  for the first build).
- Recipe Tracker: photo upload — deferred until real object storage (e.g.
  a GCS bucket) exists, since Cloud Run's filesystem doesn't persist
  (same root cause as the SQLite-doesn't-persist issue above).
- Recipe Tracker: a cook-history/ratings log (did I make this, when, how
  did it turn out) — could mirror the wine cellar's `TastingHistory`
  pattern later if wanted; explicitly out of scope for the first build.
- Recipe Tracker → Grocery List: "send ingredients to grocery list" once
  Grocery List itself is built. The Recipe Tracker ingredient data model
  is being built as a structured list (quantity/unit/name rows) rather
  than free text specifically so this stays possible without a rewrite.
- Grocery List: no specific ideas yet — not yet scoped.
