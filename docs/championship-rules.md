# Championship calculation: implemented rules and known gaps

Source: `get_championship` in `backend/api.py`. Covered by `backend/tests/test_api.py`.

**Accuracy status:** the implementation follows the points scheme below and is unit
tested against hand-computed cases. It has **not** been compared with official FIA
standings, so do not describe the table as official. To validate, compare
`/championship?season=2026` to the FIA's published table after each round and record
any differences here.

## Implemented

| Rule | Behaviour |
|---|---|
| Race points | P1-P10 score 25, 18, 15, 12, 10, 8, 6, 4, 2, 1. Everyone else scores 0. |
| Sprint points | P1-P8 score 8, 7, 6, 5, 4, 3, 2, 1. |
| Fastest lap | **No bonus point.** Removed from the 2026 rules, so it is deliberately not counted. |
| Season scope | `?season=YYYY` filters race **and** sprint results by the race `date` prefix. Default is the latest season in the DB. |
| "After round N" | `?through_round=N` includes rounds <= N only (race and sprint alike). The dashboard uses this for the selected race. |
| Driver identity | Grouped by `full_name`. |
| Team shown | The team from the driver's most recent result (a mid-season move shows the new team; earlier points stay with the driver). |
| Ordering | Points descending, then name ascending (deterministic, **not** an official tie-break). |
| Missing data | Races with no date never count. A missing/NaN finishing position is not stored, so that driver scores 0 for the race. |

## Not supported (results can be wrong in these cases)

- **Disqualifications and penalties after the race.** No race status is stored, so a
  driver classified in the top 10 and later disqualified would still score.
- **Shortened races / half points.** Not modelled; full points are always awarded.
- **Tie-breaks.** Official countback (most wins, then second places, ...) is not
  implemented; ties are ordered alphabetically.
- **Constructors' championship.** Not computed.
- **Name changes / duplicate names.** A driver whose `full_name` differs between sessions
  would be split into two rows.
- **Rule changes between seasons.** One points table is used for every season. Querying
  a season other than 2026 applies 2026 rules, which is wrong for seasons with different
  rules (e.g. the old fastest-lap point).
- **Races missing from the DB** (e.g. not yet ingested, or a sprint that was never
  loaded) silently reduce totals. See the sprint retry policy in `backend/pipeline.py`.
