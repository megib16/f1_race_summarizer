# Deployment checklist

- Back up the database and run `python backend/migrate.py` before starting new
  application code. Duplicate identities must be reviewed before migration.
- Set `APP_ENV=production` and `DATABASE_URL`. Both the API and ingest job must
  target the same database. Imports don't perform schema updates.
- Render's free service uses `dockerCommand` to run the explicit migration before
  uvicorn. Paid services can use a dedicated release/pre-deploy migration instead.
- The ingest workflow uses an ephemeral GitHub-hosted runner. Its `DATABASE_URL`
  secret must be reachable from that runner; an internal-only host URL won't work.
- Refresh stored seasons once to populate source-awarded points. Until then,
  championship requests involving legacy classifications return HTTP 409.
- `NEXT_PUBLIC_API_URL` must be the public API origin at frontend **build time**.
  Production builds reject missing or malformed origins. Rebuild when it changes. Set the backend's `FRONTEND_URL` to the exact frontend
  origin; localhost:3000 is also allowed for local development.
- Use Node 24 LTS and Python 3.11. Images run as non-root users and exclude local
  `.env` files, databases and credential directories.
- Docker Compose uses a fresh named database volume. It does not automatically
  copy the host's existing SQLite database. Stop the service before a restore.
- Set edge-level limits for a multi-worker deployment. The application IP limiter
  is per process and defaults to 120 GET requests per minute. Configure trusted
  proxy addresses so unrelated visitors don't all share the proxy's IP quota.
- Verify `/health`, `/races`, and `/championship?season=YYYY`; check unknown race
  IDs return 404, the frontend loads all sections and errors are visible per section.
- Keep a database backup and monitor ingestion logs. Missing sprint data is a
  warning with retry backoff; failed race ingestion exits nonzero.
- No model API key is required by the scheduled pipeline or the web service.
  Written summaries remain absent from the dashboard.
