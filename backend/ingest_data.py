"""Normalize FastF1 dictionaries before any write transaction is opened."""
from dataclasses import dataclass
from pydantic import BaseModel, ConfigDict

from data_utils import finite_number, optional_int


class IngestRow(BaseModel):
    model_config = ConfigDict(frozen=True, allow_inf_nan=False)


class ResultRow(IngestRow):
    position: int
    grid_position: int | None
    full_name: str
    abbreviation: str
    team: str
    time: str
    fastest_lap: str
    points: float | None
    status: str | None


class SprintRow(IngestRow):
    position: int
    full_name: str
    team: str
    points: float | None
    status: str | None


class LapRow(IngestRow):
    driver: str
    lap_number: int
    position: int


class PitRow(IngestRow):
    driver: str
    lap_number: int
    old_compound: str
    new_compound: str


class RaceFields(IngestRow):
    name: str
    location: str
    date: str
    round: int
    total_laps: int
    fastest_lap_driver: str | None
    fastest_lap_time: str | None
    fastest_lap_number: int | None
    fastest_lap_team: str | None
    air_temp: float | None
    track_temp: float | None
    rainfall: str | None


@dataclass(frozen=True)
class RacePayload:
    fields: RaceFields
    results: tuple[ResultRow, ...]
    laps: tuple[LapRow, ...]
    pits: tuple[PitRow, ...]
    complete: bool


@dataclass(frozen=True)
class SprintPayload:
    results: tuple[SprintRow, ...]
    complete: bool


def _positive_position(row):
    value = optional_int(row.get("Position"))
    return value if value is not None and value > 0 else None


def normalize_sprint(rows: list[dict]) -> SprintPayload:
    results = []
    for row in rows:
        position = _positive_position(row)
        if position is not None:
            results.append(SprintRow(
                position=position, full_name=row["FullName"], team=row["TeamName"],
                points=finite_number(row.get("Points")), status=row.get("Status"),
            ))
    return SprintPayload(tuple(results), len(results) == len(rows))


def normalize_race(*, info: dict, rows: list[dict], lap_data: list[dict],
                   pits: list[dict], fastest: dict, weather: dict) -> RacePayload:
    if not rows or not any(_positive_position(row) == 1 for row in rows):
        raise ValueError("Race has no usable classification or winner; retry later")
    results = []
    for row in rows:
        position = _positive_position(row)
        if position is not None:
            results.append(ResultRow(
                position=position, grid_position=optional_int(row.get("GridPosition")),
                full_name=row["FullName"], abbreviation=str(row.get("Abbreviation", "")),
                team=row["TeamName"], time=str(row["Time"]),
                fastest_lap=str(row.get("FastestLapTime", "")),
                points=finite_number(row.get("Points")), status=row.get("Status"),
            ))
    laps = []
    for row in lap_data:
        position = _positive_position(row)
        if position is not None:
            laps.append(LapRow(driver=str(row["Driver"]), lap_number=int(row["LapNumber"]), position=position))
    pit_rows = [PitRow(
        driver=row["Driver"], lap_number=int(row["LapNumber"]),
        old_compound=row["OldCompound"], new_compound=row["NewCompound"],
    ) for row in pits]
    fields = RaceFields(
        name=info["name"], location=info["location"], date=info["date"],
        round=info["round"], total_laps=info["total_laps"],
        fastest_lap_driver=fastest.get("driver"), fastest_lap_time=fastest.get("lap_time"),
        fastest_lap_number=optional_int(fastest.get("lap_number")), fastest_lap_team=fastest.get("team"),
        air_temp=finite_number(weather["air_temp"]), track_temp=finite_number(weather["track_temp"]),
        rainfall=None if weather["rainfall"] is None else ("Yes" if weather["rainfall"] else "No"),
    )
    complete = (len(results) == len(rows) and bool(laps)
                and len(results) >= len({row["Driver"] for row in lap_data}))
    return RacePayload(fields, tuple(results), tuple(laps), tuple(pit_rows), complete)
