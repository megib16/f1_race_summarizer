# Circuit maps

**Source:** MultiViewer circuit data (the service FastF1's `get_circuit_info` wraps), read
through FastF1's own request helper at ingest time and stored in the `circuit_maps` table.
The web app never calls it at request time.

**Why not FastF1's public API or telemetry:** `get_circuit_info()` discards the track
outline and needs telemetry for corner distances. Telemetry (`pos_data`) was not obtainable
when this was built (live-timing returned 401 for car and position data), so a
telemetry-derived outline could not be verified.

## What is shown (and what is deliberately not)
| Element | Basis |
|---|---|
| Outline | Source outline (a reference lap's path), rotated for display, loop closed. |
| Corner numbers | Source corners, kept only if within 3% of the track size of the outline. |
| Start / finish marker | **Approximate.** First point of the outline, kept only if corners then follow in increasing order, beginning in the first quarter. |
| Sectors | **Not shown.** The source only has ~16 marshal sectors, not the 3 timing sectors. |

## Limits
- Unofficial, "not highly accurate" data (FastF1's wording); fine for orientation, not for measurement.
- Layouts change between years (Barcelona: 16 corners to 2022, 14 from 2023), so maps are fetched for the race's own season and stored per race.
- No data for some venues (the 2026 Madrid GP at the time of writing): the page shows an explicit fallback.
- `get_circuit` returns nothing for any non-200 response, so "no data" and a server error look alike. Errors that raise are not stored and retry next run; "no data" is stored as `unavailable`.
- Uses `fastf1.mvapi.api` (an internal module). `fastf1` is pinned in `requirements.txt`; recheck on upgrade.

## Commands
    python backend/backfill_circuits.py                      # races with no stored lookup
    python backend/backfill_circuits.py --retry-unavailable  # also retry "no data" answers

The daily ingest also backfills missing maps, best-effort (it never fails the run).
Verified against the real payloads: 13 of the 14 stored 2026 races had maps.
