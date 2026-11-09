import { afterEach, describe, expect, it, vi } from "vitest";
import { PHASE_DEVELOPMENT_SERVER, PHASE_PRODUCTION_BUILD } from "next/constants";
import configure from "./next.config";

afterEach(() => vi.unstubAllEnvs());

describe("deployment configuration", () => {
  it("requires an explicit API origin for production builds", () => {
    vi.stubEnv("NEXT_PUBLIC_API_URL", undefined);
    expect(() => configure(PHASE_PRODUCTION_BUILD)).toThrow("Set NEXT_PUBLIC_API_URL");
    expect(configure(PHASE_DEVELOPMENT_SERVER).output).toBe("standalone");
    vi.stubEnv("NEXT_PUBLIC_API_URL", "https://api.example.com");
    expect(configure(PHASE_PRODUCTION_BUILD).output).toBe("standalone");
  });

  it("rejects credentials, paths and non-HTTP API URLs", () => {
    for (const url of ["file:///tmp/api", "https://user:pass@api.example.com", "https://api.example.com/races"]) {
      vi.stubEnv("NEXT_PUBLIC_API_URL", url);
      expect(() => configure(PHASE_PRODUCTION_BUILD)).toThrow();
    }
  });
});
