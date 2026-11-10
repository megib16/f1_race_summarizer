"use client";

import { useState } from "react";
import { DriverResult } from "../lib/race-types";
import { formatTime } from "../lib/race-utils";
import { TEAMCOLOURS, sectionTitle, sectionNote } from "../lib/dashboard-style";

function renderGridDelta(grid: number | null, finish: number) {
  if (grid == null || grid < 1) return "-"; // missing, or not a normal grid slot
  const delta = grid - finish;
  if (delta === 0) return <span className="text-gray-400">–</span>;
  if (delta > 0) return <span className="text-green-400">▲{delta}</span>;
  return <span className="text-red-400">▼{Math.abs(delta)}</span>;
}

export default function FinishingOrder({ results, loading }: { results: DriverResult[]; loading: boolean }) {
  const [showAllResults, setShowAllResults] = useState(false);
  return (
    <section aria-label="Finishing order" style={{ fontFamily: "Playfair" }} className="mt-10 min-w-0">
      <h2 className={sectionTitle}>FINISHING ORDER</h2>
      {loading && <p role="status">Loading results…</p>}
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
  );
}
