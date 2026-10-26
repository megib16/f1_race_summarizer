export interface PitStop {
  driver: string;
  lap_number: number;
  old_compound: string;
  new_compound: string;
}

export interface Stint {
  compound: string;
  laps: number;
}

const MISSING = new Set(["", "NaT", "None", "nan"]);

// pandas Timedelta strings look like "0 days 00:01:22.091000"; the fraction is absent for whole seconds.
const TIMEDELTA = /(\d+) days (\d+):(\d+):(\d+)(?:\.(\d+))?/;

export function formatLapTime(time: string | null | undefined): string {
  if (!time || MISSING.has(time)) return "-";
  const match = time.match(TIMEDELTA);
  if (!match) return time;
  const [, , , minutes, seconds, ms = "0"] = match;
  return `${parseInt(minutes)}:${seconds.padStart(2, "0")}.${ms.padEnd(3, "0").slice(0, 3)}`;
}

// No time means the driver did not finish on the lead lap (or did not finish at all).
// Status is not stored, so we cannot say "DNF" vs "lapped".
export function formatTime(time: string | null | undefined, isWinner: boolean): string {
  if (!time || MISSING.has(time)) return "No time";
  const match = time.match(TIMEDELTA);
  if (!match) return time;
  const [, , hours, minutes, seconds, ms = "0"] = match;
  const h = parseInt(hours);
  const m = parseInt(minutes);
  const s = parseInt(seconds);
  const msPart = ms.padEnd(3, "0").slice(0, 3);
  if (isWinner) {
    if (h > 0) return `${h}:${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}.${msPart}`;
    return `${m}:${s.toString().padStart(2, "0")}.${msPart}`;
  }
  const totalSec = h * 3600 + m * 60 + s + parseInt(msPart) / 1000;
  if (totalSec < 60) return `+${totalSec.toFixed(3)}s`;
  return `+${m}:${s.toString().padStart(2, "0")}.${msPart}`;
}

/**
 * Tyre stints from inferred pit-lane exits.
 * `lap_number` of a pit stop is the out-lap (first lap on the new tyre), so the
 * previous stint ends on `lap_number - 1`. `lastLap` is the driver's last
 * recorded lap, so retired drivers don't get laps they never ran.
 */
export function buildStints(driverAbbr: string, pits: PitStop[], lastLap: number): Stint[] {
  const driverPits = pits.filter((p) => p.driver === driverAbbr && p.lap_number <= lastLap).sort((a, b) => a.lap_number - b.lap_number);
  if (driverPits.length === 0) return lastLap > 0 ? [{ compound: "UNKNOWN", laps: lastLap }] : [];

  const stints: Stint[] = [];
  let start = 1;
  let currentCompound = driverPits[0].old_compound || "UNKNOWN";
  for (const pit of driverPits) {
    const laps = pit.lap_number - start;
    if (laps > 0) stints.push({ compound: currentCompound, laps });
    start = pit.lap_number;
    currentCompound = pit.new_compound || "UNKNOWN";
  }
  if (start <= lastLap) {
    stints.push({ compound: currentCompound, laps: lastLap - start + 1 });
  }
  return stints;
}

export function byDateAscending<T extends { date: string | null; round: number | null; race_id: number }>(races: T[]): T[] {
  return [...races].sort(
    (a, b) =>
      (a.date ?? "").localeCompare(b.date ?? "") || (a.round ?? 0) - (b.round ?? 0) || a.race_id - b.race_id,
  );
}

export interface GainResult {
  full_name: string;
  abbreviation: string;
  team: string;
  position: number;
  grid_position: number | null;
}

export interface PositionGain {
  driver: GainResult;
  gained: number;
}

/**
 * Largest number of places gained from starting slot to finishing position.
 * This is `grid - finish` only: it says nothing about overtakes, and drivers with a
 * missing or non-standard grid slot (< 1) are ignored. Returns null if nobody gained places.
 * Ties go to the driver who finished higher.
 */
export function biggestPositionGain(results: GainResult[]): PositionGain | null {
  let best: PositionGain | null = null;
  for (const driver of results) {
    if (driver.grid_position == null || driver.grid_position < 1 || !Number.isFinite(driver.position)) continue;
    const gained = driver.grid_position - driver.position;
    if (gained <= 0) continue;
    if (best === null || gained > best.gained || (gained === best.gained && driver.position < best.driver.position)) {
      best = { driver, gained };
    }
  }
  return best;
}
