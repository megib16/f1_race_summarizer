"use client";

import { useEffect, useState } from "react";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceDot, BarChart, Bar } from "recharts";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface Race {
  race_id: number;
  name: string;
  location: string;
  date: string;
  round: number;
  total_laps: number;
  summary: string;
  fastest_lap_driver: string;
  fastest_lap_time: string;
  fastest_lap_number: number;
  fastest_lap_team: string;
  air_temp: number;
  track_temp: number;
  rainfall: string;

}

interface DriverResult {
  driver_id: number;
  position: number;
  grid_position: number | null;
  full_name: string;
  abbreviation: string;
  team: string;
  time: string;
  fastest_lap: string;
}

interface PitStop {
  driver: string;
  lap_number: number;
  old_compound: string;
  new_compound: string;
}

interface ChampionshipEntry {
  full_name: string;
  team: string;
  points: number;
}

function formatLapTime(time: string): string {
  if (!time || time === "NaT" || time === "None" || time === "nan") return "-";
  const match = time.match(/(\d+) days (\d+):(\d+):(\d+)\.(\d+)/);
  if (!match) return time;
  const [, , , minutes, seconds, ms] = match;
  return `${parseInt(minutes)}:${seconds.padStart(2, "0")}.${ms.slice(0, 3)}`;
}

function formatTime(time: string, isWinner: boolean): string {
  if (!time || time === "NaT" || time === "None" || time === "nan") return "DNF";
  const match = time.match(/(\d+) days (\d+):(\d+):(\d+)\.(\d+)/);
  if (!match) return time;
  const [, , hours, minutes, seconds, ms] = match;
  const h = parseInt(hours);
  const m = parseInt(minutes);
  const s = parseInt(seconds);
  const msPart = ms.slice(0, 3);
  if (isWinner) {
    if (h > 0) return `${h}:${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}.${msPart}`;
    return `${m}:${s.toString().padStart(2, "0")}.${msPart}`;
  }
  const totalSec = h * 3600 + m * 60 + s + parseInt(ms) / 1000000;
  if (totalSec < 60) return `+${totalSec.toFixed(3)}s`;
  return `+${m}:${s.toString().padStart(2, "0")}.${msPart}`;
}


function renderGridDelta(grid: number | null, finish: number) {
  if (grid == null) return "-";
  const delta = grid - finish;
  if (delta === 0) return <span className="text-gray-400">–</span>;
  if (delta > 0) return <span className="text-green-400">▲{delta}</span>;
  return <span className="text-red-400">▼{Math.abs(delta)}</span>;
}

interface Stint {
  compound: string;
  laps: number;
}

interface StintBarProps {
  x?: number;
  y?: number;
  width?: number;
  height?: number;
  payload?: Record<string, string | number>;
}

function buildStints(driverAbbr: string, pits: PitStop[], totalLaps: number): Stint[] {
  const driverPits = pits.filter((p) => p.driver === driverAbbr).sort((a, b) => a.lap_number - b.lap_number);
  if (driverPits.length === 0) return [{ compound: "UNKNOWN", laps: totalLaps }];

  const stints: Stint[] = [];
  let start = 1;
  let currentCompound = driverPits[0].old_compound || "UNKNOWN";
  for (const pit of driverPits) {
    stints.push({ compound: currentCompound, laps: pit.lap_number - start + 1 });
    start = pit.lap_number + 1;
    currentCompound = pit.new_compound;
  }
  if (start <= totalLaps) {
    stints.push({ compound: currentCompound, laps: totalLaps - start + 1 });
  }
  return stints;
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
  const [race, setRace] = useState<Race | null>(null);
  const [results, setResults] = useState<DriverResult[]>([]);
  const [lapData, setLapData] = useState<{ driver: string, lap_number: number, position: number }[]>([]);
  const [showAllResults, setShowAllResults] = useState(false);
  const [showAllChampionship, setShowAllChampionship] = useState(false);
  const [pitstops, setPitStops] = useState<PitStop[]>([]);
  const [allRaces, setAllRaces] = useState<Race[]>([]);
  const [championship, setChampionship] = useState<ChampionshipEntry[]>([]);

  function loadRaceData(raceId: number) {
    fetch(`${API}/races/${raceId}/results`)
      .then(r => r.json())
      .then((res: DriverResult[]) => setResults(res.sort((a, b) => a.position - b.position)));
    fetch(`${API}/races/${raceId}/laps`).then(r => r.json()).then(setLapData);
    fetch(`${API}/races/${raceId}/pits`).then(r => r.json()).then(setPitStops);
  }



  useEffect(() => {
    fetch(`${API}/races`)
      .then((r) => r.json())
      .then((races: Race[]) => {
        if (races.length === 0) return;
        setAllRaces(races);
        fetch(`${API}/championship`).then(r => r.json()).then(data => { if (Array.isArray(data)) setChampionship(data); });
        const latest = races[races.length - 1];
        setRace(latest);
        loadRaceData(latest.race_id);
      });

  }, []);

  const p1 = results.find((d) => d.position === 1);
  const p2 = results.find((d) => d.position === 2);
  const p3 = results.find((d) => d.position === 3);
  const fl = race?.fastest_lap_driver;
  const flTime = race?.fastest_lap_time;
  const flLap = race?.fastest_lap_number;
  const flTeam = race?.fastest_lap_team;
  const flResult = results.find((d) => d.full_name.split(" ").pop()?.slice(0, 3).toUpperCase() === fl);



  const lapMap: Record<number, Record<string, number>> = {};
  for (const entry of lapData) {
    if (!lapMap[entry.lap_number]) lapMap[entry.lap_number] = {};
    lapMap[entry.lap_number][entry.driver] = entry.position;
  }
  const chartData = Object.entries(lapMap).map(([lap, positions]) => ({
    lap: parseInt(lap),
    ...positions,
  }));

  const drivers = [...new Set(lapData.map((d) => d.driver))];
  const teamForDriver: Record<string, string> = {
  };
  for (const r of results) {
    const abbr = r.full_name.split(" ").pop()?.slice(0, 3).toUpperCase() ?? ""

    teamForDriver[abbr] = TEAMCOLOURS[r.team] ?? "#ffffff"
  }

  const stintsByDriver = results.map((r) => ({
    result: r,
    stints: buildStints(r.abbreviation, pitstops, race?.total_laps ?? 0),
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


  return (
    <div className="min-h-screen bg-[#212121] text-white p-8">

      <div style={{ fontFamily: "Playfair" }} className="flex gap-2 justify-center mb-8 flex-wrap text-xl p-6">
        {allRaces.slice(-3).map(r => (
          <button
            key={r.race_id}
            onClick={() => { setRace(r); loadRaceData(r.race_id); }}
            className={`px-6 py-3 rounded text-xl ${race?.race_id === r.race_id ? "bg-red-600 text-white" : "bg-gray-700 text-gray-300 hover:bg-gray-600"}`}
          >
            {r.name}
          </button>
        ))}
      </div>


      {/* Header */}
      <div className="mb-8 text-center">
        <h1 style={{ fontFamily: "BitcountSingle_Cursive-SemiBold" }} className="text-8xl font-bold text-red-600">
          {race ? race.name.toUpperCase() : "Loading..."}
        </h1>
        <p style={{ fontFamily: "Playfair" }} className="text-5xl text-white mt-2">
          {race ? `${race.location} · ${race.date} · ${race.total_laps} Laps` : ""}
        </p>
      </div>

      {/* Podium */}
      <div className="flex justify-center items-end gap-6 mb-8">
        <div style={{ fontFamily: "Playfair" }} className="bg-gray-800 p-6 rounded-lg text-center w-60">
          <p className="text-[#C7C7C7] text-4xl">2nd Place</p>
          <p className="text-3xl font-bold mt-1">{p2?.full_name ?? "-"}</p>
          <p style={{ color: TEAMCOLOURS[p2?.team ?? ""] }} className="text-gray-400 text-2xl">{p2?.team ?? ""}</p>
          <p className="text-gray-300 text-2xl mt-1">{p2 ? formatTime(p2.time, false) : ""}</p>
        </div>
        <div style={{ fontFamily: "Playfair" }} className="bg-[#DF2F3F] p-8 rounded-lg text-center w-80">
          <p className="text-white text-5xl font-bold">🏆 RACE WINNER</p>
          <p className="text-4xl font-bold mt-1">{p1?.full_name ?? "-"}</p>
          <p style={{ color: TEAMCOLOURS[p1?.team ?? ""] }} className="text-2xl">{p1?.team ?? ""}</p>
          <p className="text-[#F8ED07] text-2xl mt-2">{p1 ? formatTime(p1.time, true) : ""}</p>
        </div>
        <div style={{ fontFamily: "Playfair" }} className="bg-gray-800 p-6 rounded-lg text-center w-60">
          <p className="text-[#c7c7c7] text-4xl">3rd Place</p>
          <p className="text-3xl font-bold mt-1">{p3?.full_name ?? "-"}</p>
          <p style={{ color: TEAMCOLOURS[p3?.team ?? ""] }} className="text-gray-400 text-2xl">{p3?.team ?? ""}</p>
          <p className="text-gray-300 text-2xl mt-1">{p3 ? formatTime(p3.time, false) : ""}</p>
        </div>
      </div>

      {/* Fastest lap */}
      <div style={{ fontFamily: "Playfair" }} className="flex items-center justify-between bg-[#255F98] rounded-lg px-8 py-4 mb-6">
        <p className="text-white text-2xl">Fastest lap:</p>
        <p className="text-xl font-bold">{flResult?.full_name ?? "-"}</p>
        <p style={{ color: TEAMCOLOURS[flTeam ?? ""] }} className="text-xl font-bold ">{flResult?.team ?? ""}</p>
        <p className="text-white text-xl">{flTime ? formatLapTime(flTime) : ""}</p>
        <p className="text-white text-xl">Lap: {flLap}</p>
      </div>

      {/* Weather */}
      {race && (
        <div style={{ fontFamily: "Playfair" }} className="flex items-center justify-around bg-gray-800 rounded-lg px-8 py-3 mb-6 text-xl">
          <p>🌡️ Air: {race.air_temp}°C</p>
          <p>🏎️ Track: {race.track_temp}°C</p>
          <p>{race.rainfall === "Yes" ? "🌧️ Rain" : "☀️ Dry"}</p>
        </div>
      )}

      {/* 2x2 grid layout */}
      <div className="grid grid-cols-2 gap-8 mt-6">

        {/* Top left: Chart */}
        <div>
          <ResponsiveContainer width="120%" >
            <LineChart data={chartData}>
              <XAxis dataKey="lap" stroke="#6b7280" />
              <YAxis reversed domain={[1, 20]} stroke="#6b7280" width={40} />

              <Tooltip content={({ active, payload, label }) => {
                if (!active || !payload) return null;
                const sorted = [...payload].sort((a, b) => (a.value as number) - (b.value as number));
                return (
                  <div style={{ fontFamily: "Playfair" }} className="bg-gray-900 border border-gray-700 rounded p-2 text-s">
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
                          🔧 {pit.driver}: {pit.old_compound[0]}→{pit.new_compound[0]}
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
        </div>

        {/* Top right: Finishing order */}
        <div className="w-7/10 ml-auto" style={{ fontFamily: "Playfair" }}>
          <h2 className="text-3xl font-bold text-red-500 mb-4">FINISHING ORDER</h2>
          <table className="text-left text-sm border-collapse text-xl">
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
          {results.length > 10 && (
            <button onClick={() => setShowAllResults(!showAllResults)} className="mt-2 text-gray-400 hover:text-white text-sm flex items-center gap-1">
              {showAllResults ? "▲ Show less" : "▼ Show all"}
            </button>
          )}
        </div>



        {/* Bottom right: Summary */}
        <div style={{ width: "120%" }}>
          <h2 style={{ fontFamily: "Playfair" }} className="text-3xl font-bold text-red-500 mb-4">RACE SUMMARY</h2>
          <div className="bg-gray-800 rounded-lg p-6 text-gray-300 text-xl whitespace-pre-wrap " style={{ fontFamily: "Playfair" }}>
            {race?.summary ?? "Summary coming soon..."}
          </div>
        </div>


        {/* Bottom left: Championship table */}
        <div className="w-7/10 ml-auto" style={{ fontFamily: "Playfair" }}>
          <h2 className="text-3xl font-bold text-red-500 mb-4">CHAMPIONSHIP TABLE</h2>
          <table className="w-full text-left text-sm border-collapse text-xl">
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
          {championship.length > 10 && (
            <button onClick={() => setShowAllChampionship(!showAllChampionship)} className="mt-2 text-gray-400 hover:text-white text-sm flex items-center gap-1">
              {showAllChampionship ? "▲ Show less" : "▼ Show all"}
            </button>
          )}
        </div>

      </div>

      {/* Tire strategy */}
      {maxStints > 0 && (
        <div className="mt-10">
          <h2 style={{ fontFamily: "Playfair" }} className="text-3xl font-bold text-red-500 mb-4">TIRE STRATEGY</h2>
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
        </div>
      )}
    </div>
  );
}
