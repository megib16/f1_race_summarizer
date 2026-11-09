// @vitest-environment jsdom
import { act, cleanup, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useRaceDashboard } from "./use-race-dashboard";
import { Race } from "./race-types";

const { getJson, getPages } = vi.hoisted(() => ({ getJson: vi.fn(), getPages: vi.fn() }));
vi.mock("./api-client", async (original) => ({ ...await original<typeof import("./api-client")>(), getJson, getPages }));
const race = { race_id: 1, name: "GP1", date: "2026-01-01", round: 1 } as Race;
const other = { ...race, race_id: 2, name: "GP2", round: 2 };
const laps = [{ driver: "A", lap_number: 1, position: 1 }];

beforeEach(() => {
  getJson.mockReset();
  getPages.mockReset();
  getPages.mockImplementation(async (path: string) => path === "/races" ? [race] : laps);
  getJson.mockImplementation(async (path: string) => path.endsWith("/circuit")
    ? { status: "unavailable", reason: "no_data", map: null } : []);
});
afterEach(cleanup);

describe("dashboard loading", () => {
  it("keeps lap and pit data when results fail", async () => {
    getJson.mockImplementation(async (path: string) => {
      if (path.endsWith("/results")) throw new Error("unavailable");
      if (path.endsWith("/pits")) return [{ driver: "A", lap_number: 2 }];
      return path.endsWith("/circuit") ? { status: "unavailable", reason: "no_data" } : [];
    });
    const { result } = renderHook(() => useRaceDashboard());
    await waitFor(() => expect(result.current.raceErrors).toHaveLength(1));
    expect(result.current.lapData).toEqual(laps);
    expect(result.current.pitstops).toHaveLength(1);
    expect(result.current.loadingSections.results).toBe(false);
  });

  it("cancels old requests and ignores their late responses", async () => {
    let resolveOld: (value: unknown[]) => void = () => {};
    let oldSignal: AbortSignal | undefined;
    getJson.mockImplementation((path: string, signal: AbortSignal) => {
      if (path === "/races/1/results") {
        oldSignal = signal;
        return new Promise((resolve) => { resolveOld = resolve; });
      }
      if (path.endsWith("/results")) return Promise.resolve([{ position: 1, full_name: "New winner" }]);
      return Promise.resolve(path.endsWith("/circuit") ? { status: "unavailable", reason: "no_data" } : []);
    });
    const { result, unmount } = renderHook(() => useRaceDashboard());
    await waitFor(() => expect(result.current.race?.race_id).toBe(1));
    act(() => result.current.selectRace(other));
    await waitFor(() => expect(result.current.results[0]?.full_name).toBe("New winner"));
    expect(oldSignal?.aborted).toBe(true);
    await act(async () => { resolveOld([{ position: 1, full_name: "Old winner" }]); });
    expect(result.current.results[0].full_name).toBe("New winner");
    const latestSignal = getJson.mock.calls.find(([path]) => path === "/races/2/results")?.[1];
    unmount();
    expect(latestSignal.aborted).toBe(true);
  });
});
