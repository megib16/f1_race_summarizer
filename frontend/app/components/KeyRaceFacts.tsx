import { Race, DriverResult } from "../lib/race-types";
import { biggestPositionGain, formatTime, formatLapTime } from "../lib/race-utils";
import { TEAMCOLOURS } from "../lib/dashboard-style";

export default function KeyRaceFacts({ race, results }: { race: Race | null; results: DriverResult[] }) {
  const p1 = results.find((d) => d.position === 1);
  const p2 = results.find((d) => d.position === 2);
  const p3 = results.find((d) => d.position === 3);
  const gain = biggestPositionGain(results);
  const fl = race?.fastest_lap_driver;
  const flTime = race?.fastest_lap_time;
  const flLap = race?.fastest_lap_number;
  const flTeam = race?.fastest_lap_team;
  const flResult = results.find((d) => d.abbreviation === fl);

  const card = "bg-gray-800 rounded-lg p-4 sm:p-5 min-w-0";
  const cardLabel = "text-gray-400 text-sm sm:text-base uppercase tracking-wide";
  return (
    <section aria-label="Key race facts" style={{ fontFamily: "Playfair" }} className="mt-6 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      <div className={card}>
        <p className={cardLabel}>🏆 Winner</p>
        <p className="text-xl sm:text-2xl font-bold mt-1">{p1?.full_name ?? "-"}</p>
        <p style={{ color: TEAMCOLOURS[p1?.team ?? ""] }}>{p1?.team ?? ""}</p>
        <p className="text-[#F8ED07]">{p1 ? formatTime(p1.time, true) : ""}</p>
        {(p2 || p3) && (
          <p className="text-gray-400 text-sm mt-2">
            {p2 ? `2nd ${p2.full_name}` : ""}{p2 && p3 ? " · " : ""}{p3 ? `3rd ${p3.full_name}` : ""}
          </p>
        )}
      </div>
      <div className={card}>
        <p className={cardLabel}>⏱ Fastest lap</p>
        <p className="text-xl sm:text-2xl font-bold mt-1">{flResult?.full_name ?? fl ?? "-"}</p>
        <p style={{ color: TEAMCOLOURS[flTeam ?? ""] }}>{flResult?.team ?? flTeam ?? ""}</p>
        <p>{flTime ? formatLapTime(flTime) : "-"}{flLap != null ? ` · lap ${flLap}` : ""}</p>
      </div>
      <div className={card}>
        <p className={cardLabel}>▲ Biggest position gain</p>
        {gain ? (
          <>
            <p className="text-xl sm:text-2xl font-bold mt-1">{gain.driver.full_name}</p>
            <p style={{ color: TEAMCOLOURS[gain.driver.team] }}>{gain.driver.team}</p>
            <p className="text-green-400">+{gain.gained} places · P{gain.driver.grid_position} → P{gain.driver.position}</p>
          </>
        ) : (
          <p className="text-gray-400 mt-1">-</p>
        )}
        <p className="text-gray-500 text-xs mt-2">Starting slot vs finishing position only; not a count of overtakes.</p>
      </div>
      <div className={card}>
        <p className={cardLabel}>🌡 Conditions</p>
        {race && (race.air_temp != null || race.track_temp != null || race.rainfall) ? (
          <>
            <p className="mt-1">Air {race.air_temp ?? "-"}°C · Track {race.track_temp ?? "-"}°C</p>
            <p>{race.rainfall === "Yes" ? "🌧️ Rain recorded" : race.rainfall === "No" ? "☀️ No rain recorded" : ""}</p>
          </>
        ) : (
          <p className="text-gray-400 mt-1">-</p>
        )}
        <p className="text-gray-500 text-xs mt-2">Averages over the race session.</p>
      </div>
    </section>
  );
}
