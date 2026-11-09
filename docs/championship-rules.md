# Championship scoring

`backend/api.py:get_championship` totals the `Points` supplied by FastF1 for each
race and sprint classification. It preserves fractional awards and doesn't
reconstruct points from positions. Classification statuses `Disqualified`,
`Excluded` and `DSQ` score zero even if an upstream row still contains points.

- `season` defaults to the latest dated season in the database.
- `through_round` includes races and sprints through that round.
- Equal totals are ordered by the number of race wins, then seconds, thirds,
  and so on. Sprint finishing positions are excluded from this countback.
- Names provide deterministic ordering if all stored finish counts are equal.
- Drivers are grouped by full name; their latest team is displayed.
- A classification without source-awarded points returns HTTP 409. Refresh that
  season using `python backend/pipeline.py --year YYYY`; old databases are not
  silently scored using a newer season's rules.

Totals depend on completeness and freshness of the stored source data. Missing
races/sprints reduce totals; a penalty is only reflected once the source updates
and ingestion refreshes it. This is not an independently verified official table.
Constructor standings, championship-only points deductions not represented in
session awards, and stable driver IDs across name changes are not implemented.
