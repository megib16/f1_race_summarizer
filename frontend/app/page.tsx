"use client";

import { useEffect, useState } from "react";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";

const API = "http://localhost:8000";

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
}

interface DriverResult {
  driver_id: number;
  position: number;
  full_name: string;
  team: string;
  time: string;
  fastest_lap: string;
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

const POINTS: Record<number, number> = {
  1: 25, 2: 18, 3: 15, 4: 12, 5: 10,
  6: 8, 7: 6, 8: 4, 9: 2, 10: 1
};

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


export default function Home() {
  const [race, setRace] = useState<Race | null>(null);
  const [results, setResults] = useState<DriverResult[]>([]);
  const [lapData, setLapData] = useState<{ driver: string, lap_number: number, position: number }[]>([]);
  const [showAllResults, setShowAllResults] = useState(false);
  const [showAllChampionship, setShowAllChampionship] = useState(false);

  useEffect(() => {
    fetch(`${API}/races`)
      .then((r) => r.json())
      .then((races: Race[]) => {
        if (races.length === 0) return;
        const latest = races[races.length - 1];
        setRace(latest);
        fetch(`${API}/races/${latest.race_id}/results`)
          .then((r) => r.json())
          .then((res: DriverResult[]) =>
            setResults(res.sort((a, b) => a.position - b.position))
          );
        fetch(`${API}/races/${latest.race_id}/laps`).then((r) => r.json()).then((laps) => setLapData(laps));
      });
  }, []);

  const p1 = results.find((d) => d.position === 1);
  const p2 = results.find((d) => d.position === 2);
  const p3 = results.find((d) => d.position === 3);
  const fl = race?.fastest_lap_driver;
  const flTime = race?.fastest_lap_time;
  const flLap = race?.fastest_lap_number;
  const flResult = results.find((d) => d.full_name.split(" ").pop()?.slice(0, 3).toUpperCase() === fl);


  const cpoints = [...results].sort((a, b) => (POINTS[b.position] ?? 0) - (POINTS[a.position] ?? 0));
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




  return (
    <div className="min-h-screen bg-[#212121] text-white p-8">

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
          <p className="text-gray-400 text-2xl">{p2?.team ?? ""}</p>
          <p className="text-gray-300 text-2xl mt-1">{p2 ? formatTime(p2.time, false) : ""}</p>
        </div>
        <div style={{ fontFamily: "Playfair" }} className="bg-[#DF2F3F] p-8 rounded-lg text-center w-80">
          <p className="text-yellow-300 text-5xl font-bold">🏆 RACE WINNER</p>
          <p className="text-4xl font-bold mt-1">{p1?.full_name ?? "-"}</p>
          <p style={{ color: TEAMCOLOURS[p1?.team ?? ""] }} className="text-2xl">{p1?.team ?? ""}</p>
          <p className="text-[#F8ED07] text-2xl mt-2">{p1 ? formatTime(p1.time, true) : ""}</p>
        </div>
        <div style={{ fontFamily: "Playfair" }} className="bg-gray-800 p-6 rounded-lg text-center w-60">
          <p className="text-[#c7c7c7] text-4xl">3rd Place</p>
          <p className="text-3xl font-bold mt-1">{p3?.full_name ?? "-"}</p>
          <p className="text-gray-400 text-2xl">{p3?.team ?? ""}</p>
          <p className="text-gray-300 text-2xl mt-1">{p3 ? formatTime(p3.time, false) : ""}</p>
        </div>
      </div>

      {/* Fastest lap */}
      <div style={{ fontFamily: "Playfair" }} className="flex items-center justify-between bg-[#255F98] rounded-lg px-8 py-4 mb-6">
        <p className="text-white text-2xl">Fastest lap:</p>
        <p className="text-xl font-bold">{flResult?.full_name ?? "-"}</p>
        <p className="text-gray-400 text-xl">{flResult?.team ?? ""}</p>
        <p className="text-white text-xl">{flTime ? formatLapTime(flTime) : ""}</p>
        <p className="text-white text-xl">Lap: {flLap}</p>
      </div>

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
                  <div className="bg-gray-900 border border-gray-700 rounded p-2 text-xs">
                    <p className="text-gray-400 mb-1">Lap {label}</p>
                    {sorted.map((entry) => (
                      <p key={String(entry.dataKey)} style={{ color: entry.color }}>
                        P{entry.value as number} — {String(entry.dataKey)}
                      </p>
                    ))}
                  </div>
                );
              }} />
              {drivers.map((d) => (
                <Line key={d} type="monotone" dataKey={d} dot={false} strokeWidth={2} stroke={teamForDriver[d] ?? "#ffffff"} />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Top right: Finishing order */}
        <div className="w-7/10 ml-auto" style={{ fontFamily: "Playfair" }}>
          <h2 className="text-3xl text-center text- font-bold text-red-500 mb-4">FINISHING ORDER</h2>
          <table className="text-left text-sm border-collapse text-xl">
            <thead>
              <tr className="text-gray-400 border-b border-gray-700">
                <th className="py-2 pr-3">POS</th>
                <th className="py-2 pr-3">DRIVER</th>
                <th className="py-2 pr-3">TEAM</th>
                <th className="py-2">TIME</th>
              </tr>
            </thead>
            <tbody>
              {(showAllResults ? results : results.slice(0, 10)).map((d) => (
                <tr key={d.driver_id} className="border-b border-gray-800 hover:bg-gray-900">
                  <td className="py-2 pr-3 font-bold text-red-500">{d.position}</td>
                  <td className="py-2 pr-3 font-semibold">{d.full_name}</td>
                  <td style={{ color: TEAMCOLOURS[d.team] }} className="py-2 pr-3">{d.team}</td>
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

        {/* Bottom left: Championship table */}
        <div style={{ fontFamily: "Playfair" }}>
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
              {(showAllChampionship ? cpoints : cpoints.slice(0, 10)).map((d) => (
                <tr key={d.driver_id} className="border-b border-gray-800 hover:bg-gray-900">
                  <td className="py-2 pr-3 font-bold">{d.full_name}</td>
                  <td style={{ color: TEAMCOLOURS[d.team] }} className="py-2 pr-3">{d.team}</td>
                  <td className="py-2 pr-3 text-gray-400">{POINTS[d.position] ?? 0}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {cpoints.length > 10 && (
            <button onClick={() => setShowAllChampionship(!showAllChampionship)} className="mt-2 text-gray-400 hover:text-white text-sm flex items-center gap-1">
              {showAllChampionship ? "▲ Show less" : "▼ Show all"}
            </button>
          )}
        </div>

        {/* Bottom right: Summary */}
        <div>
          <h2 className="text-3xl font-bold text-red-500 mb-4">RACE SUMMARY</h2>
          <div className="bg-gray-800 rounded-lg p-6 text-gray-300 text-xl" style={{ fontFamily: "Playfair" }}>
            {race?.summary ?? "Summary coming soon..."}
          </div>
        </div>

      </div>
    </div>
  );
}
