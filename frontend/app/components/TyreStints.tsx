"use client";

import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { DriverResult, LapEntry } from "../lib/race-types";
import { PitStop, buildStints } from "../lib/race-utils";
import { TYRECOLOURS, sectionTitle, sectionNote } from "../lib/dashboard-style";

interface StintBarProps {
  x?: number;
  y?: number;
  width?: number;
  height?: number;
  payload?: Record<string, string | number>;
}

interface Props {
  results: DriverResult[];
  lapData: LapEntry[];
  pitstops: PitStop[];
  totalLaps: number;
}

export default function TyreStints({ results, lapData, pitstops, totalLaps }: Props) {
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

  if (maxStints === 0) return null;
  return (
    <section aria-label="Tyre stints" style={{ fontFamily: "Playfair" }} className="mt-10 min-w-0">
      <h2 className={sectionTitle}>TYRE STINTS</h2>
      <p className={sectionNote}>
        Inferred from pit-lane exits and tyre compound changes in the lap data. Stop durations and the reason for a
        stop are not available.
      </p>
      <ResponsiveContainer width="100%" height={stintChartData.length * 32 + 40}>
        <BarChart data={stintChartData} layout="vertical" margin={{ left: 10 }}>
          <XAxis type="number" domain={[0, totalLaps]} stroke="#6b7280" />
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
  );
}
