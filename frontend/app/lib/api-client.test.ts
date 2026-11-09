import { afterEach, describe, expect, it, vi } from "vitest";
import { getJson, getPages } from "./api-client";

afterEach(() => vi.unstubAllGlobals());

describe("API transport", () => {
  it("collects every bounded page", async () => {
    const fetch = vi.fn()
      .mockResolvedValueOnce({ ok: true, json: async () => [1, 2] })
      .mockResolvedValueOnce({ ok: true, json: async () => [3] });
    vi.stubGlobal("fetch", fetch);
    expect(await getPages<number>("/races", 2)).toEqual([1, 2, 3]);
    expect(fetch.mock.calls[1][0]).toContain("limit=2&offset=2");
  });

  it("rejects failed responses and invalid collection payloads", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 503 }));
    await expect(getJson("/races")).rejects.toThrow("503");
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => ({}) }));
    await expect(getPages("/races", 2)).rejects.toThrow("Expected a list");
  });

  it("propagates cancellation to fetch", async () => {
    const controller = new AbortController();
    const fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => [] });
    vi.stubGlobal("fetch", fetch);
    await getJson("/races", controller.signal);
    const signal = fetch.mock.calls[0][1].signal as AbortSignal;
    controller.abort();
    expect(signal.aborted).toBe(true);
  });
});
