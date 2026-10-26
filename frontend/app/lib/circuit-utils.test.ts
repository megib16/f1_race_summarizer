import { describe, expect, it } from "vitest";
import { cornerLabel, mapScale, outlinePath, unavailableMessage } from "./circuit-utils";
import { biggestPositionGain, type GainResult } from "./race-utils";

describe("mapScale", () => {
  it("pads the viewBox on every side and scales strokes with the map size", () => {
    const s = mapScale({ width: 1000, height: 500 });
    expect(s.viewBox).toBe("-60 -60 1120 620");
    expect(s.stroke).toBeCloseTo(11);
    expect(mapScale({ width: 2000, height: 500 }).stroke).toBeCloseTo(22);
  });

  it("does not divide by or collapse on an empty map", () => {
    expect(mapScale({ width: 0, height: 0 }).stroke).toBeGreaterThan(0);
  });
});

describe("outlinePath", () => {
  it("builds a closed SVG path", () => {
    expect(outlinePath([[0, 0], [10, 0], [10, 10]])).toBe("M0,0 L10,0 L10,10 Z");
  });
});

describe("cornerLabel", () => {
  it("joins number and optional letter", () => {
    expect(cornerLabel({ number: 1, letter: "" })).toBe("1");
    expect(cornerLabel({ number: 2, letter: "A" })).toBe("2A");
  });
});

describe("unavailableMessage", () => {
  it("explains known reasons and falls back for unknown or missing ones", () => {
    expect(unavailableMessage("no_data")).toMatch(/No circuit geometry/);
    expect(unavailableMessage("not_fetched")).toMatch(/not been loaded/);
    expect(unavailableMessage("something_new")).toBe("No circuit map is available for this race.");
    expect(unavailableMessage(null)).toBe("No circuit map is available for this race.");
  });
});

describe("biggestPositionGain", () => {
  const d = (abbreviation: string, grid: number | null, position: number): GainResult => ({
    full_name: abbreviation, abbreviation, team: "T", position, grid_position: grid,
  });

  it("picks the largest grid-minus-finish gain", () => {
    const best = biggestPositionGain([d("A", 1, 1), d("B", 10, 3), d("C", 5, 4)]);
    expect(best?.driver.abbreviation).toBe("B");
    expect(best?.gained).toBe(7);
  });

  it("breaks ties in favour of the higher finisher", () => {
    const best = biggestPositionGain([d("A", 8, 5), d("B", 6, 3)]);
    expect(best?.driver.abbreviation).toBe("B");
  });

  it("ignores missing and non-standard grid slots", () => {
    expect(biggestPositionGain([d("A", null, 1), d("B", 0, 1)])).toBeNull();
  });

  it("returns null when nobody gained places or there are no results", () => {
    expect(biggestPositionGain([d("A", 1, 1), d("B", 2, 5)])).toBeNull();
    expect(biggestPositionGain([])).toBeNull();
  });
});
