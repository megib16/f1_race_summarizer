"""Championship calculation without database or HTTP dependencies."""
from dataclasses import dataclass
from typing import Iterable

from data_utils import finite_number


class StandingsUnavailable(ValueError):
    """Source classifications cannot yet support a complete points total."""


@dataclass(frozen=True)
class Classification:
    date: str
    round: int
    is_race: bool
    full_name: str
    team: str
    position: int | None
    points: float | None
    status: str | None


def calculate_standings(classifications: Iterable[Classification]) -> list[dict]:
    totals: dict[str, dict] = {}
    countback: dict[str, list[int]] = {}
    events = sorted(classifications, key=lambda r: (r.date, r.round, r.is_race))
    for result in events:
        name, team = result.full_name, result.team
        disqualified = (result.status or "").strip().lower() in {"disqualified", "excluded", "dsq"}
        points = finite_number(result.points)
        if disqualified:
            points = 0
        elif points is None:
            raise StandingsUnavailable("Re-ingest this season to load source-awarded points")
        entry = totals.setdefault(name, {"full_name": name, "team": team, "points": 0})
        entry["team"] = team
        entry["points"] += points
        finishes = countback.setdefault(name, [0] * 100)
        if result.is_race and not disqualified and result.position and 1 <= result.position <= 100:
            finishes[result.position - 1] += 1
    return sorted(totals.values(), key=lambda entry: (
        -entry["points"], tuple(-n for n in countback[entry["full_name"]]), entry["full_name"]
    ))
