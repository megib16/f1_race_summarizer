# Minimal safe deployment checklist

This lists what to verify. It changes no infrastructure. Items marked (verify) are
assumptions I could not confirm from the repo alone.

## Database
- [ ] **Postgres in production, not SQLite.** `DATABASE_URL` must be set on the backend.
      Without it the app silently falls back to a local SQLite file.
- [ ] **Docker Compose (local only):** `./backend/f1_races.db` is bind-mounted as a single
      file. If it does not exist on the host, Docker creates a *directory* of that name and
      the app fails. Create/copy the DB file first (`touch` is not enough for a populated DB).
- [ ] **Back up before the first deploy with new code.** On startup the app runs
      `create_all`, which adds the new `race_meta` table. It does not alter existing tables,
      and nothing is dropped. (This already happened once on the local DB when running the
      summary dry-run.)
- [ ] **The ingest job must reach the same database as the API.** The scheduled workflow
      uses the `DATABASE_URL` secret. Render's `fromDatabase connectionString` is, as far as
      I know, the *internal* URL, which is not reachable from GitHub. Use the external URL
      for the secret (verify).
- [ ] Check the hosting plan's database retention/expiry limits (verify).

## Frontend API URL
- [ ] `NEXT_PUBLIC_API_URL` is **inlined at build time**. Changing it requires a rebuild.
      Set it as a build environment variable on the frontend host, or
      `docker compose build --build-arg`/`NEXT_PUBLIC_API_URL=... docker compose build frontend`.
- [ ] Use the public https URL of the API, no trailing path. The default is
      `http://localhost:8000`; a production build without the variable will call localhost
      from the visitor's browser and show the "Could not reach the race API" message.
- [ ] `render.yaml` defines only the backend. The frontend host is configured elsewhere
      (verify where).

## CORS
- [ ] `FRONTEND_URL` on the backend must equal the frontend's exact origin
      (scheme + host [+ port]), e.g. `https://my-app.vercel.app`. A trailing slash is now
      stripped, but `http` vs `https` or a preview-deployment hostname will still be blocked.
- [ ] `http://localhost:3000` is always allowed, including in production. Harmless for a
      public read-only API, but remove it if you tighten this later.
- [ ] Only one extra origin is supported. Multiple frontends (e.g. Vercel previews) need code.

## Secrets and jobs
- [ ] `ANTHROPIC_API_KEY` set on the ingest job and anywhere `backfill_summaries` runs.
      Without it summaries stay empty and are retried; ingestion still succeeds.
- [ ] Only one ingest job at a time (the workflow has a `concurrency` group; local manual
      runs against the production DB do not).
- [ ] The workflow exits non-zero when a race fails to ingest. Check the run status, since a
      missing sprint is only a warning.

## Smoke test after deploy
1. `GET <api>/races` returns races in date order.
2. `GET <api>/championship?season=<year>&through_round=1` returns a table.
3. Load the frontend, open the browser console: no CORS or network errors.
4. Pick an older race: the standings heading should read "after round N" for that round.
