import { describe, expect, it } from "vitest";
import { buildStints, byDateAscending, formatLapTime, formatTime, type PitStop } from "./race-utils";

const pit = (driver: string, lap: number, from: string, to: string): PitStop => ({
  driver,
  lap_number: lap,
  old_compound: from,
  new_compound: to,
});

describe("buildStints", () => {
  // lap_number is the out-lap: the first lap on the new tyre.
  const pits = [pit("ALB", 13, "MEDIUM", "HARD"), pit("ALB", 34, "HARD", "SOFT")];

  it("ends each stint on the lap before the pit-out lap", () => {
    expect(buildStints("ALB", pits, 58)).toEqual([
      { compound: "MEDIUM", laps: 12 },
      { compound: "HARD", laps: 21 },
      { compound: "SOFT", laps: 25 },
    ]);
  });

  it("stint lengths add up to the laps run", () => {
    const total = buildStints("ALB", pits, 58).reduce((n, s) => n + s.laps, 0);
    expect(total).toBe(58);
  });

  it("does not give a retired driver laps they never ran", () => {
    expect(buildStints("ALB", pits, 20)).toEqual([
      { compound: "MEDIUM", laps: 12 },
      { compound: "HARD", laps: 8 },
    ]);
  });

  it("ignores pits recorded after the driver's last lap", () => {
    expect(buildStints("ALB", pits, 10)).toEqual([{ compound: "UNKNOWN", laps: 10 }]);
  });

  it("handles a driver with no stops", () => {
    expect(buildStints("VER", pits, 58)).toEqual([{ compound: "UNKNOWN", laps: 58 }]);
  });

  it("returns no stints for a driver with no recorded laps", () => {
    expect(buildStints("VER", [], 0)).toEqual([]);
  });

  it("only uses the requested driver's stops, in lap order", () => {
    const mixed = [pit("B", 30, "HARD", "SOFT"), pit("A", 10, "SOFT", "HARD"), pit("B", 15, "SOFT", "HARD")];
    expect(buildStints("B", mixed, 50)).toEqual([
      { compound: "SOFT", laps: 14 },
      { compound: "HARD", laps: 15 },
      { compound: "SOFT", laps: 21 },
    ]);
  });

  it("falls back to UNKNOWN for empty compounds and drops zero-length stints", () => {
    const odd = [pit("X", 1, "", ""), pit("X", 20, "", "HARD")];
    expect(buildStints("X", odd, 30)).toEqual([
      { compound: "UNKNOWN", laps: 19 },
      { compound: "HARD", laps: 11 },
    ]);
  });
});

describe("formatLapTime", () => {
  it("formats pandas timedelta strings", () => {
    expect(formatLapTime("0 days 00:01:22.091000")).toBe("1:22.091");
  });

  it("handles whole seconds with no fraction", () => {
    expect(formatLapTime("0 days 00:01:22")).toBe("1:22.000");
  });

  it("pads short fractions and truncates long ones", () => {
    expect(formatLapTime("0 days 00:01:22.5")).toBe("1:22.500");
    expect(formatLapTime("0 days 00:01:22.123456")).toBe("1:22.123");
  });

  it.each([null, undefined, "", "NaT", "None", "nan"])("shows a dash for missing value %s", (value) => {
    expect(formatLapTime(value)).toBe("-");
  });

  it("passes through strings it cannot parse", () => {
    expect(formatLapTime("1:22.091")).toBe("1:22.091");
  });
});

describe("formatTime", () => {
  it("formats the winner's total time with and without hours", () => {
    expect(formatTime("0 days 01:23:06.801000", true)).toBe("1:23:06.801");
    expect(formatTime("0 days 00:45:06.801000", true)).toBe("45:06.801");
  });

  it("formats gaps under a minute in seconds", () => {
    expect(formatTime("0 days 00:00:02.974000", false)).toBe("+2.974s");
  });

  it("formats gaps over a minute as m:ss.mmm", () => {
    expect(formatTime("0 days 00:01:05.250000", false)).toBe("+1:05.250");
  });

  it.each([null, undefined, "", "NaT", "None", "nan"])("never claims DNF for missing value %s", (value) => {
    expect(formatTime(value, false)).toBe("No time");
  });
});

describe("byDateAscending", () => {
  const race = (race_id: number, date: string | null, round: number | null) => ({ race_id, date, round });

  it("orders by date, not by id", () => {
    const sorted = byDateAscending([race(1, "2026-06-14", 7), race(2, "2026-06-07", 6)]);
    expect(sorted.map((r) => r.round)).toEqual([6, 7]);
  });

  it("breaks date ties by round then id and does not mutate the input", () => {
    const input = [race(3, "2026-01-01", 2), race(2, "2026-01-01", 1), race(1, "2026-01-01", 1)];
    expect(byDateAscending(input).map((r) => r.race_id)).toEqual([1, 2, 3]);
    expect(input.map((r) => r.race_id)).toEqual([3, 2, 1]);
  });

  it("sorts missing dates first instead of throwing", () => {
    expect(byDateAscending([race(1, "2026-01-01", 1), race(2, null, null)]).map((r) => r.race_id)).toEqual([2, 1]);
  });
});
