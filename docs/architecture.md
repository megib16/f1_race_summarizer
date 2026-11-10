# Code responsibilities

## Backend

- `fetcher.py` is the FastF1/MultiViewer adapter. Source naming and pandas data
  stay at this boundary.
- `ingest_data.py` validates source dictionaries into immutable race/sprint
  payloads. Invalid identities and field types fail before database writes.
- `pipeline.py` coordinates downloads, retry decisions and per-race transactions.
  `today` is supplied throughout schedule filtering, retries and refresh markers,
  so a backfill can be evaluated consistently without changing the system clock.
- `race_store.py` contains database writes. Its functions accept a SQLAlchemy
  session and validated payloads; they never download data, commit, or roll back.
  The caller's `SessionLocal.begin()` context owns that transaction.
- `standings.py` calculates points and countback from plain classifications. It
  has no dependency on FastAPI or ORM models. The API translates a domain error
  into an HTTP response.
- `api.py` handles request validation, queries, serialization and HTTP behavior.

Optional source failures are contained at their download boundaries. A failed
race is logged and returned to the job caller, which exits nonzero. Backfills
close read sessions before downloading and open a short write transaction after
that download. Tests verify no connections remain checked out during those calls.

## Schema history

`migrate.py` is the migration runner and compatibility check. Versioned modules
under `backend/migrations/` own frozen table definitions and upgrade operations.
They must never import `models.py` or use its metadata: changing an application
model must not change how an older migration runs.

For a new schema change, add a new numbered migration module and register its
upgrade function in `MIGRATIONS`. Do not edit an applied migration. Update the
application models separately, then test a fresh database and an upgrade from
the previous version. Moving migration 1 into its own module did not change its
schema or version; existing version-1 databases require no additional migration.

## Frontend

`app/page.tsx` composes dashboard sections and race selection. `useRaceDashboard`
owns requests, cancellation and loading/error state. Facts, finishing order,
position progression, tyre stints and standings each live in a component under
`app/components/`; table expansion belongs to the relevant table component.
Shared colours and section styles live in `app/lib/dashboard-style.ts`.

The extracted sections retain the dashboard's existing content and presentation.
Written summaries remain absent. Backend response shapes and URL paths are
unchanged.

## Tests

Reusable fake sessions and circuit payloads live in `backend/tests/fakes.py`;
test modules do not import each other for fixtures. Database and HTTP tests cover
transactions and season scope, while calculation tests can run without a database.
Frontend component tests cover expansion, loading/error states and stable row
identity when standings are reordered.
