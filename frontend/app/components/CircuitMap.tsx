import { CircuitMapData, cornerLabel, mapScale, outlinePath, unavailableMessage } from "../lib/circuit-utils";

export type CircuitState =
  | { kind: "loading" }
  | { kind: "error" }
  | { kind: "unavailable"; reason: string | null }
  | { kind: "available"; map: CircuitMapData };

function Placeholder({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-center min-h-[220px] rounded-lg border border-dashed border-gray-700 bg-[#1a1a1a] px-6 text-center text-gray-400">
      {children}
    </div>
  );
}

export default function CircuitMap({ state, season }: { state: CircuitState; season?: string }) {
  if (state.kind === "loading") return <Placeholder>Loading circuit map…</Placeholder>;
  if (state.kind === "error") return <Placeholder>Could not load the circuit map.</Placeholder>;
  if (state.kind === "unavailable") return <Placeholder>{unavailableMessage(state.reason)}</Placeholder>;

  const { map } = state;
  const s = mapScale(map);
  const [startX, startY] = [map.start?.x ?? 0, map.start?.y ?? 0];

  return (
    <figure className="m-0">
      <svg
        viewBox={s.viewBox}
        role="img"
        aria-label={`Circuit map${map.circuit_name ? ` of ${map.circuit_name}` : ""}, ${map.corners.length} numbered corners`}
        className="w-full h-auto max-h-[60vh] block"
      >
        <path d={outlinePath(map.outline)} fill="none" stroke="#0e0e0e" strokeWidth={s.underlay} strokeLinejoin="round" strokeLinecap="round" />
        <path d={outlinePath(map.outline)} fill="none" stroke="#E10600" strokeWidth={s.stroke} strokeLinejoin="round" strokeLinecap="round" />

        {map.corners.map((c) => (
          <g key={`${c.number}${c.letter}-${c.x}-${c.y}`}>
            <line x1={c.x} y1={c.y} x2={c.label_x} y2={c.label_y} stroke="#6b7280" strokeWidth={s.cornerDot * 0.5} />
            <circle cx={c.x} cy={c.y} r={s.cornerDot} fill="#ffffff" />
            <text
              x={c.label_x}
              y={c.label_y}
              fontSize={s.font}
              fill="#e5e7eb"
              textAnchor="middle"
              dominantBaseline="central"
              paintOrder="stroke"
              stroke="#212121"
              strokeWidth={s.font * 0.25}
            >
              {cornerLabel(c)}
            </text>
          </g>
        ))}

        {map.start && (
          <g>
            <line x1={startX} y1={startY} x2={map.start.ahead_x} y2={map.start.ahead_y} stroke="#ffffff" strokeWidth={s.stroke * 0.6} strokeLinecap="round" />
            <rect x={startX - s.marker} y={startY - s.marker} width={s.marker * 2} height={s.marker * 2} fill="#ffffff" stroke="#212121" strokeWidth={s.stroke * 0.3} />
          </g>
        )}
      </svg>
      <figcaption className="mt-2 text-center text-xs sm:text-sm text-gray-500">
        {map.start && <span className="text-gray-300">■ Start / finish (approximate) · </span>}
        Layout as of {map.year ?? season ?? "this season"}. Outline and corner positions are approximate third-party
        circuit data (MultiViewer), not telemetry from this race. Sector boundaries are not shown.
      </figcaption>
    </figure>
  );
}
