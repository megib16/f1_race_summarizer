"use client";

import { useEffect, useState } from "react";

const API = "http://localhost:8000";

interface Race {
  race_id: number;
  name: string;
  location: string;
  date: string;
  round: number;
  total_laps: number;
  summary: string;
}

interface DriverResult {
  driver_id: number;
  position: number;
  full_name: string;
  team: string;
  time: string;
  fastest_lap: string;
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

export default function Home() {
  const [race, setRace] = useState<Race | null>(null);
  const [results, setResults] = useState<DriverResult[]>([]);

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
      });
  }, []);

  const p1 = results.find((d) => d.position === 1);
  const p2 = results.find((d) => d.position === 2);
  const p3 = results.find((d) => d.position === 3);


  return (
    <div className="min-h-screen bg-gray-950 text-white p-8">

      {/* Header */}
      <div className="mb-8 text-center">
        <h1 className="text-5xl font-bold text-red-600">
          {race ? race.name.toUpperCase() : "Loading..."}
        </h1>
        <p className="text-xl text-gray-400 mt-2">
          {race ? `${race.location} · ${race.date} · ${race.total_laps} Laps` : ""}
        </p>
      </div>

      {/* Podium */}
      <div className="flex justify-center items-end gap-4 mb-6">
        <div className="bg-gray-800 p-6 rounded-lg text-center w-48">
          <p className="text-gray-400 text-sm">2nd Place</p>
          <p className="text-xl font-bold mt-1">{p2?.full_name ?? "-"}</p>
          <p className="text-gray-400 text-sm">{p2?.team ?? ""}</p>
          <p className="text-gray-300 text-sm mt-1">{p2 ? formatTime(p2.time, false) : ""}</p>
        </div>
        <div className="bg-red-900 p-8 rounded-lg text-center w-56">
          <p className="text-yellow-400 text-sm font-bold">RACE WINNER</p>
          <p className="text-2xl font-bold mt-1">{p1?.full_name ?? "-"}</p>
          <p className="text-gray-300 text-sm">{p1?.team ?? ""}</p>
          <p className="text-yellow-400 text-sm mt-2">{p1 ? formatTime(p1.time, true) : ""}</p>
        </div>
        <div className="bg-gray-800 p-6 rounded-lg text-center w-48">
          <p className="text-gray-400 text-sm">3rd Place</p>
          <p className="text-xl font-bold mt-1">{p3?.full_name ?? "-"}</p>
          <p className="text-gray-400 text-sm">{p3?.team ?? ""}</p>
          <p className="text-gray-300 text-sm mt-1">{p3 ? formatTime(p3.time, false) : ""}</p>
        </div>
      </div>

      {/* Main two-column layout */}
      <div className="flex gap-8 mt-6">

        {/* Left: Chart */}
        {/* Left: Chart placeholder - to be built */}
        <div className="flex-1">
          <h2 className="text-2xl font-bold text-red-500 mb-4">RACE TIMELINE</h2>
          <div className="bg-gray-800 rounded-lg h-96 flex items-center justify-center text-gray-500">
            Chart coming soon
          </div>
        </div>

        {/* Right: Results table */}
        <div className="w-96">
          <h2 className="text-2xl font-bold text-red-500 mb-4">FINISHING ORDER</h2>
          <table className="w-full text-left text-sm border-collapse">
            <thead>
              <tr className="text-gray-400 border-b border-gray-700">
                <th className="py-2 pr-3">POS</th>
                <th className="py-2 pr-3">DRIVER</th>
                <th className="py-2 pr-3">TEAM</th>
                <th className="py-2">TIME</th>
              </tr>
            </thead>
            <tbody>
              {results.map((d) => (
                <tr key={d.driver_id} className="border-b border-gray-800 hover:bg-gray-900">
                  <td className="py-2 pr-3 font-bold text-red-500">{d.position}</td>
                  <td className="py-2 pr-3 font-semibold">{d.full_name}</td>
                  <td className="py-2 pr-3 text-gray-400 text-xs">{d.team}</td>
                  <td className="py-2 text-gray-300 text-xs">{formatTime(d.time, d.position === 1)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

      </div>
    </div>
  );
}
