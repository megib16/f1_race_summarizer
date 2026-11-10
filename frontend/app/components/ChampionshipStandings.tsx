"use client";

import { useState } from "react";
import { Race, ChampionshipEntry } from "../lib/race-types";
import { TEAMCOLOURS, sectionTitle, sectionNote } from "../lib/dashboard-style";

interface Props {
  race: Pick<Race, "name" | "date" | "round"> | null;
  championship: ChampionshipEntry[];
  loading: boolean;
  championshipError: string | null;
}

export default function ChampionshipStandings({ race, championship, loading, championshipError }: Props) {
  const [showAllChampionship, setShowAllChampionship] = useState(false);
  const season = race?.date?.slice(0, 4);
  return (
    <section aria-label="Championship standings" style={{ fontFamily: "Playfair" }} className="mt-10 min-w-0">
      <h2 className={sectionTitle}>DRIVERS&apos; CHAMPIONSHIP</h2>
      {race && (
        <p className={sectionNote}>
          {season} season, standings after round {race.round} ({race.name}). Race and sprint points; ties use race finishing-position countback.
        </p>
      )}
      {loading && <p role="status">Loading standings…</p>}
      {championshipError && <p role="alert" className="text-red-400 mb-2">{championshipError}</p>}
      {!championshipError && !loading && race && championship.length === 0 && <p className="text-gray-400 mb-2">No standings available.</p>}
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
            {(showAllChampionship ? championship : championship.slice(0, 10)).map((d) => (
              <tr key={d.full_name} className="border-b border-gray-800 hover:bg-gray-900">
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
  );
}
