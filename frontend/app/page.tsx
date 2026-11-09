"use client";

import { useState } from "react";
import { useRaceDashboard } from "./lib/use-race-dashboard";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceDot, BarChart, Bar } from "recharts";
import { biggestPositionGain, buildStints, formatLapTime, formatTime } from "./lib/race-utils";
import CircuitMap from "./components/CircuitMap";

function renderGridDelta(grid: number | null, finish: number) {
  if (grid == null || grid < 1) return "-"; // missing, or not a normal grid slot
  const delta = grid - finish;
  if (delta === 0) return <span className="text-gray-400">–</span>;
  if (delta > 0) return <span className="text-green-400">▲{delta}</span>;
  return <span className="text-red-400">▼{Math.abs(delta)}</span>;
}

interface StintBarProps {
  x?: number;
  y?: number;
  width?: number;
  height?: number;
  payload?: Record<string, string | number>;
}

const TEAMCOLOURS: Record<string, string> = {
  "Mercedes": "#00D2BE",
  "Ferrari": "#E8002D",
  "Red Bull Racing": "#3671C6",
  "McLaren": "#FF8000",
  "Aston Martin": "#229971",
  "Alpine": "#FF87BC",
  "Williams": "#64C4FF",
  "Racing Bulls": "#6692FF",
  "Haas F1 Team": "#B6BABD",
  "Cadillac": "#C92D4B",
  "Audi": "#D6D6D6",
};

const TYRECOLOURS: Record<string, string> = {
  "SOFT": "#E8002D",
  "MEDIUM": "#F8F02B",
  "HARD": "#FFFFFF",
  "INTERMEDIATE": "#1AFF00",
  "WET": "#0B7FEF"
}


export default function Home() {
  const { race, results, lapData, pitstops, allRaces, championship, loadState,
    championshipError, raceErrors, circuit, loadingSections, selectRace } = useRaceDashboard();
  const [showAllResults, setShowAllResults] = useState(false);
  const [showAllChampionship, setShowAllChampionship] = useState(false);

  const p1 = results.find((d) => d.position === 1);
  const p2 = results.find((d) => d.position === 2);
  const p3 = results.find((d) => d.position === 3);
  const gain = biggestPositionGain(results);
  const season = race?.date?.slice(0, 4);
  const circuitName = circuit.kind === "available" ? circuit.map.circuit_name : null;
  const fl = race?.fastest_lap_driver;
  const flTime = race?.fastest_lap_time;
  const flLap = race?.fastest_lap_number;
  const flTeam = race?.fastest_lap_team;
  const flResult = results.find((d) => d.abbreviation === fl);



  const lapMap: Record<number, Record<string, number>> = {};
  for (const entry of lapData) {
    if (!lapMap[entry.lap_number]) lapMap[entry.lap_number] = {};
    lapMap[entry.lap_number][entry.driver] = entry.position;
  }
  const chartData = Object.entries(lapMap).map(([lap, positions]) => ({
    lap: parseInt(lap),
    ...positions,
  }));

  // Grids can exceed 20 cars (22 in 2026), so size the axis from the data.
  const maxPosition = Math.max(20, ...lapData.map((d) => d.position));
  const drivers = [...new Set(lapData.map((d) => d.driver))];
  const teamForDriver: Record<string, string> = {
  };
  for (const r of results) {
    teamForDriver[r.abbreviation] = TEAMCOLOURS[r.team] ?? "#ffffff"
  }

  const lastLapByDriver: Record<string, number> = {};
  for (const entry of lapData) {
    lastLapByDriver[entry.driver] = Math.max(lastLapByDriver[entry.driver] ?? 0, entry.lap_number);
  }
  const stintsByDriver = results.map((r) => ({
    result: r,
    stints: buildStints(r.abbreviation, pitstops, lastLapByDriver[r.abbreviation] ?? 0),
  }));
  const maxStints = Math.max(0, ...stintsByDriver.map((s) => s.stints.length));
  const stintChartData = stintsByDriver.map(({ result, stints }) => {
    const row: Record<string, string | number> = {
      driver: result.abbreviation,
      fullName: result.full_name,
    };
    stints.forEach((stint, i) => {
      row[`stint_${i}`] = stint.laps;
      row[`stint_${i}_compound`] = stint.compound;
    });
    return row;
  });


  const sectionTitle = "text-2xl sm:text-3xl font-bold text-red-500";
  const sectionNote = "text-gray-400 text-sm sm:text-base mb-4 mt-1";
  const card = "bg-gray-800 rounded-lg p-4 sm:p-5 min-w-0";
  const cardLabel = "text-gray-400 text-sm sm:text-base uppercase tracking-wide";

  return (
    <main className="min-h-screen bg-[#212121] text-white px-4 sm:px-8 py-4 sm:py-8 overflow-x-hidden">
      <div className="mx-auto max-w-6xl">

        {/* 1. Race selector, event name, date and circuit metadata */}
        <header className="text-center">
          {allRaces.length > 0 && (
            <select
              aria-label="Choose a race"
              value={race?.race_id ?? ""}
              onChange={(e) => {
                const picked = allRaces.find((r) => r.race_id === Number(e.target.value));
                if (picked) selectRace(picked);
              }}
              style={{ fontFamily: "Playfair" }}
              className="w-full sm:w-auto max-w-full px-3 py-2 sm:px-4 sm:py-3 rounded text-base sm:text-xl bg-gray-700 text-gray-300"
            >
              {[...allRaces].reverse().map((r) => (
                <option key={r.race_id} value={r.race_id}>
                  R{r.round} · {r.name}
                </option>
              ))}
            </select>
          )}

          {loadState === "error" && (
            <p role="alert" className="mt-6 text-xl text-red-400">
              Could not reach the race API. Check that the backend is running and try again.
            </p>
          )}
          {loadState === "empty" && <p className="mt-6 text-xl text-gray-400">No races have been loaded yet.</p>}
          {raceErrors.map((error) => <p key={error} role="alert" className="mt-6 text-xl text-red-400">{error}</p>)}

          <h1 style={{ fontFamily: "BitcountSingle_Cursive-SemiBold" }} className="mt-6 text-4xl sm:text-6xl lg:text-7xl font-bold text-red-600 break-words">
            {race ? race.name.toUpperCase() : loadState === "loading" ? "Loading..." : "F1 RACES"}
          </h1>
          {race && (
            <p style={{ fontFamily: "Playfair" }} className="mt-2 text-lg sm:text-2xl text-white">
              Round {race.round} · {race.date} · {race.location}
              {circuitName ? ` · ${circuitName}` : ""} · {race.total_laps} laps
            </p>
          )}
        </header>

        {/* 2. Circuit map (visual anchor) */}
        <section aria-label="Circuit map" className="mt-6 sm:mt-8 rounded-lg bg-[#1a1a1a] p-3 sm:p-6">
          <CircuitMap state={circuit} season={season} />
        </section>

        {/* 3. Key race facts (each is stored data or a direct calculation; see notes) */}
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

        {/* 4a. Finishing order */}
        <section aria-label="Finishing order" style={{ fontFamily: "Playfair" }} className="mt-10 min-w-0">
          <h2 className={sectionTitle}>FINISHING ORDER</h2>
          {loadingSections.results && <p role="status">Loading results…</p>}
          <p className={sectionNote}>
            Grid is the starting slot. +/- compares it with the finishing position. A missing time means no time was
            recorded; the reason (retirement or being lapped) is not stored.
          </p>
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-sm sm:text-xl">
              <thead>
                <tr className="text-gray-400 border-b border-gray-700">
                  <th className="py-2 pr-3">POS</th>
                  <th className="py-2 pr-3">DRIVER</th>
                  <th className="py-2 pr-3">TEAM</th>
                  <th className="py-2 pr-3">GRID</th>
                  <th className="py-2 pr-3">+/-</th>
                  <th className="py-2">TIME</th>
                </tr>
              </thead>
              <tbody>
                {(showAllResults ? results : results.slice(0, 10)).map((d) => (
                  <tr key={d.driver_id} className="border-b border-gray-800 hover:bg-gray-900">
                    <td className="py-2 pr-3 font-bold text-red-500">{d.position}</td>
                    <td className="py-2 pr-3 font-semibold">{d.full_name}</td>
                    <td style={{ color: TEAMCOLOURS[d.team] }} className="py-2 pr-3">{d.team}</td>
                    <td className="py-2 pr-3 text-gray-300">{d.grid_position ?? "-"}</td>
                    <td className="py-2 pr-3">{renderGridDelta(d.grid_position, d.position)}</td>
                    <td className="py-2 text-gray-300">{formatTime(d.time, d.position === 1)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {results.length > 10 && (
            <button onClick={() => setShowAllResults(!showAllResults)} className="mt-2 text-gray-400 hover:text-white text-sm flex items-center gap-1">
              {showAllResults ? "▲ Show less" : "▼ Show all"}
            </button>
          )}
        </section>

        {/* 4b. Position progression */}
        <section aria-label="Position progression" style={{ fontFamily: "Playfair" }} className="mt-10 min-w-0">
          <h2 className={sectionTitle}>POSITION PROGRESSION</h2>
          {loadingSections.laps && <p role="status">Loading lap positions…</p>}
          <p className={sectionNote}>
            Race position at the end of each lap. Dots mark inferred pit-lane exits (the lap shown is the first lap on the new tyres).
          </p>
          <ResponsiveContainer width="100%" height={420}>
            <LineChart data={chartData}>
              <XAxis dataKey="lap" stroke="#6b7280" />
              <YAxis reversed domain={[1, maxPosition]} allowDecimals={false} stroke="#6b7280" width={40} />

              <Tooltip content={({ active, payload, label }) => {
                if (!active || !payload) return null;
                const sorted = [...payload].sort((a, b) => (a.value as number) - (b.value as number));
                return (
                  <div style={{ fontFamily: "Playfair" }} className="bg-gray-900 border border-gray-700 rounded p-2 text-sm">
                    <p className="text-gray-400 mb-1">Lap {label}</p>
                    {sorted.map((entry) => (
                      <p key={String(entry.dataKey)} style={{ color: entry.color }}>
                        P{entry.value as number} — {String(entry.dataKey)}
                      </p>
                    ))}

                    {pitstops
                      .filter(pit => pit.lap_number === label)
                      .map((pit, i) => (
                        <p key={i} style={{ color: TYRECOLOURS[pit.new_compound] ?? "#ffffff" }}>
                          🔧 {pit.driver}: {pit.old_compound?.[0] ?? "?"}→{pit.new_compound?.[0] ?? "?"}
                        </p>
                      ))
                    }
                  </div>
                );
              }} />
              {drivers.map((d) => (
                <Line key={d} style={{ fontFamily: "Playfair" }} type="monotone" dataKey={d} dot={false} strokeWidth={2} stroke={teamForDriver[d] ?? "#ffffff"} />
              ))}
              {pitstops.map((pit, i) => (
                <ReferenceDot
                  key={i}
                  x={pit.lap_number}
                  y={lapMap[pit.lap_number]?.[pit.driver]}
                  r={5}
                  fill={TYRECOLOURS[pit.new_compound] ?? "#ffffff"}
                  stroke="none"
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </section>

        {/* 4c. Tyre stints */}
        {maxStints > 0 && (
          <section aria-label="Tyre stints" style={{ fontFamily: "Playfair" }} className="mt-10 min-w-0">
            <h2 className={sectionTitle}>TYRE STINTS</h2>
            <p className={sectionNote}>
              Inferred from pit-lane exits and tyre compound changes in the lap data. Stop durations and the reason for a
              stop are not available.
            </p>
            <ResponsiveContainer width="100%" height={stintChartData.length * 32 + 40}>
              <BarChart data={stintChartData} layout="vertical" margin={{ left: 10 }}>
                <XAxis type="number" domain={[0, race?.total_laps ?? 0]} stroke="#6b7280" />
                <YAxis type="category" dataKey="driver" stroke="#6b7280" width={50} />
                <Tooltip content={({ active, payload }) => {
                  if (!active || !payload || !payload[0]) return null;
                  const row = payload[0].payload as Record<string, string | number>;
                  return (
                    <div style={{ fontFamily: "Playfair" }} className="bg-gray-900 border border-gray-700 rounded p-2 text-sm">
                      <p className="text-gray-300 mb-1">{row.fullName}</p>
                      {Array.from({ length: maxStints }).map((_, i) => (
                        row[`stint_${i}`] ? (
                          <p key={i} style={{ color: TYRECOLOURS[row[`stint_${i}_compound`] as string] ?? "#fff" }}>
                            {row[`stint_${i}_compound`]}: {row[`stint_${i}`]} laps
                          </p>
                        ) : null
                      ))}
                    </div>
                  );
                }} />
                {Array.from({ length: maxStints }).map((_, i) => (
                  <Bar
                    key={i}
                    dataKey={`stint_${i}`}
                    stackId="stack"
                    shape={(props: StintBarProps) => {
                      const { x = 0, y = 0, width = 0, height = 0, payload } = props;
                      const compound = payload?.[`stint_${i}_compound`] as string | undefined;
                      return <rect x={x} y={y} width={width} height={height} fill={TYRECOLOURS[compound ?? ""] ?? "#555"} stroke="#212121" strokeWidth={1} />;
                    }}
                  />
                ))}
              </BarChart>
            </ResponsiveContainer>
          </section>
        )}

        {/* 5. Championship standings, labelled by season and round */}
        <section aria-label="Championship standings" style={{ fontFamily: "Playfair" }} className="mt-10 min-w-0">
          <h2 className={sectionTitle}>DRIVERS&apos; CHAMPIONSHIP</h2>
          {race && (
            <p className={sectionNote}>
              {season} season, standings after round {race.round} ({race.name}). Race and sprint points; ties use race finishing-position countback.
            </p>
          )}
          {loadingSections.championship && <p role="status">Loading standings…</p>}
          {championshipError && <p role="alert" className="text-red-400 mb-2">{championshipError}</p>}
          {!championshipError && !loadingSections.championship && race && championship.length === 0 && <p className="text-gray-400 mb-2">No standings available.</p>}
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-sm sm:text-xl">
              <thead>
                <tr className="text-gray-400 border-b border-gray-700">
                  <th className="py-2 pr-3">DRIVER</th>
                  <th className="py-2 pr-3">TEAM</th>
                  <th className="py-2 pr-3">POINTS</th>
                </tr>
              </thead>
              <tbody>
                {(showAllChampionship ? championship : championship.slice(0, 10)).map((d, i) => (
                  <tr key={i} className="border-b border-gray-800 hover:bg-gray-900">
                    <td className="py-2 pr-3 font-bold">{d.full_name}</td>
                    <td style={{ color: TEAMCOLOURS[d.team] }} className="py-2 pr-3">{d.team}</td>
                    <td className="py-2 pr-3 text-gray-400">{d.points}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {championship.length > 10 && (
            <button onClick={() => setShowAllChampionship(!showAllChampionship)} className="mt-2 text-gray-400 hover:text-white text-sm flex items-center gap-1">
              {showAllChampionship ? "▲ Show less" : "▼ Show all"}
            </button>
          )}
        </section>

      </div>
    </main>
  );
}
