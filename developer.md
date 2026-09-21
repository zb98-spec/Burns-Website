# Developer Summary

A current-state snapshot of this project as of 2026-09-21 — what exists,
what's live, and what's next. For deeper detail, see the other docs
(pointers at the bottom); this file is the fast-orientation summary, not
the source of truth for any one topic.

## What this is

A personal dashboard site (Flask monolith) where each hobby/utility
project is a self-contained blueprint sharing one login system, one
permissions model, and one Neon Postgres database — except Investing,
which will be a separate service (see below).

**Live at:** https://zabu-kabu.com (custom domain, cert issued) and
https://burns-website-hihcmsb4ua-uc.a.run.app (Cloud Run default URL,
always works). Currently serving revision `burns-website-00011-4h5`,
built from `master` @ `f21e7a8`.

## Stack

Flask 3 (app factory + Blueprints) · Flask-SQLAlchemy · Flask-Migrate
(Alembic) · Flask-Login · Jinja2 templates, hand-written CSS, minimal
vanilla JS · Neon Postgres in prod, SQLite fallback for zero-config local
dev · gunicorn in a single Dockerfile · Google Cloud Run · GitHub Actions
CI (tests only — deploys are manual).

## Project status

| Project | Status | Notes |
|---|---|---|
| Wine Cellar Tracker | **Live** | Full CRUD, search, drink-window badges, Drink action + Tasting History |
| Grocery List | **Live** | Active list + catalog, category grouping |
| Recipe Tracker | **Live** | Structured ingredients, search/filter by cuisine + meal type |
| Honeymoon | Placeholder | Tile + access gate exist, no functionality |
| Investing | Placeholder | Tile + access gate exist, no functionality — see "Investing" below |

All five are access-gated: the whole site requires login, and each
project additionally requires an admin-granted per-project permission
(`UserProjectAccess`) beyond just being logged in.

## Auth & permissions

Added this session (PR #7, hardened in PR #8). Local accounts only, no
email:
- `User` (`auth_users`) + `UserProjectAccess` (`auth_user_project_access`,
  a grant join table). `User.has_access(key)` is the single source of
  truth; admins bypass all grants.
- Whole-site login gate (`app/__init__.py`) + a one-line
  `require_project_access(key)` `before_request` per project blueprint.
- Self-service signup (`/create-account`) starts with zero access; an
  admin grants projects and can promote other admins via `/admin`.
- Bootstrap the first admin with `flask --app wsgi create-admin` — already
  done in prod, you have admin access.
- Session cookies are hardened (HttpOnly, SameSite=Lax, Secure in prod);
  password resets invalidate existing sessions; the post-review pass (PR
  #8) closed an open-redirect bug and two race conditions. CSRF protection
  and login rate-limiting are explicitly deferred — see
  `FEATURE_BACKLOG.md`.

## Database migrations

Flask-Migrate/Alembic replaced the old manual `db.create_all()` step
(PR #6) after that caused two separate production 500s from
forgotten table creation. Workflow: change a model → `flask db migrate` →
review the generated script → commit it → after deploying, run
`gcloud run jobs execute burns-website-migrate`.

**Known gotcha (hit twice, documented in `FEATURE_BACKLOG.md`):** that
Cloud Run Job is pinned to a fixed image digest and does **not**
auto-track new deploys. Every deploy needs:
```bash
gcloud run jobs update burns-website-migrate --region us-central1 \
  --image "$(gcloud run services describe burns-website --region us-central1 --format='value(spec.template.spec.containers[0].image)')"
gcloud run jobs execute burns-website-migrate --region us-central1
```
right after `gcloud run deploy`, or the job silently runs stale code.

## Investing — different pattern than the others

Per `INVESTMENT_ENGINE_HANDOFF.md` (uncommitted planning doc, still in
this repo), Investing's actual functionality (direct indexing, DCA,
tax-loss harvesting) is planned as a **separate, independently-developed
API/service** — not a blueprint here — integrating over HTTP, likely at a
subdomain (`invest.zabu-kabu.com` or similar, not yet decided). This
site's `investing` blueprint is just the placeholder tile/entry point;
real scaffolding decisions (subdomain, GCP project, DB, auth model between
the two services) are still open, listed at the bottom of that doc.

## Deploying (manual)

```bash
gcloud run deploy burns-website --source . --region us-central1 \
  --project burns-website-prod --allow-unauthenticated
# then the migrate re-pin + execute commands above, every time
```
Verify after: check routes with `curl`, check
`gcloud run services logs read burns-website --region us-central1` for
errors. CI (GitHub Actions) runs the test suite on every push/PR; CD
(auto-deploy) isn't set up yet.

## Recent fix

PR #11 (just deployed): added `SQLALCHEMY_ENGINE_OPTIONS =
{"pool_pre_ping": True}` after an intermittent
`psycopg2.OperationalError: SSL connection has been closed unexpectedly`
showed up in prod logs — Neon can silently close idle connections;
pre-ping detects and transparently reconnects instead of 500ing.

## Loose ends

- Two throwaway test accounts exist in prod (`logintest-verify`,
  `browsercheck-2026`) from manual verification — harmless (zero access),
  no delete-user feature yet to remove them.
- `INVESTMENT_ENGINE_HANDOFF.md` is uncommitted; decide whether to commit
  it, move it, or fold it into a future investing-engine repo.
- See `FEATURE_BACKLOG.md` for the fuller list (CSRF, rate limiting, CD
  automation, a billing budget alert not yet confirmed, minor test-hygiene
  items).

## Where to look next

- **`DEVELOPMENT_PLAN.md`** — architecture decisions, how to build a new
  project blueprint, full data models for each built project.
- **`FEATURE_BACKLOG.md`** — deferred work and known gaps, with rationale.
- **`TESTING.md`** — what's covered, what isn't, how to run subsets.
- **`WORKFLOW.md`** — the branch → PR → merge → deploy → verify process
  used for every change in this repo.
- **`INVESTMENT_ENGINE_HANDOFF.md`** — scoping doc for the separate
  investing service.
