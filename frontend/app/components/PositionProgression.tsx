"use client";

import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceDot } from "recharts";
import { DriverResult, LapEntry } from "../lib/race-types";
import { PitStop } from "../lib/race-utils";
import { TEAMCOLOURS, TYRECOLOURS, sectionTitle, sectionNote } from "../lib/dashboard-style";

interface Props {
  results: DriverResult[];
  lapData: LapEntry[];
  pitstops: PitStop[];
  loading: boolean;
}

export default function PositionProgression({ results, lapData, pitstops, loading }: Props) {
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

  return (
    <section aria-label="Position progression" style={{ fontFamily: "Playfair" }} className="mt-10 min-w-0">
      <h2 className={sectionTitle}>POSITION PROGRESSION</h2>
      {loading && <p role="status">Loading lap positions…</p>}
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
  );
}
