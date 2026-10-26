export interface CircuitCorner {
  number: number;
  letter: string;
  x: number;
  y: number;
  label_x: number;
  label_y: number;
}

export interface CircuitMapData {
  circuit_name: string | null;
  year: number | null;
  width: number;
  height: number;
  outline: [number, number][];
  corners: CircuitCorner[];
  start: { x: number; y: number; ahead_x: number; ahead_y: number } | null;
}

export type CircuitResponse =
  | { status: "available"; reason: null; map: CircuitMapData }
  | { status: "unavailable"; reason: string | null; map: null };

const REASONS: Record<string, string> = {
  not_fetched: "The circuit map has not been loaded for this race yet.",
  no_data: "No circuit geometry is available for this venue, so no map is shown.",
  no_circuit_key: "This race could not be matched to a circuit, so no map is shown.",
  invalid_outline: "The circuit data for this venue was incomplete, so no map is shown.",
  corrupt_data: "The stored circuit data could not be read, so no map is shown.",
};

export function unavailableMessage(reason: string | null | undefined): string {
  return (reason && REASONS[reason]) || "No circuit map is available for this race.";
}

/** SVG sizing derived from the map's own size, so strokes and labels scale with the viewBox. */
export function mapScale(map: Pick<CircuitMapData, "width" | "height">) {
  const size = Math.max(map.width, map.height, 1);
  const pad = size * 0.06;
  return {
    viewBox: `${-pad} ${-pad} ${map.width + 2 * pad} ${map.height + 2 * pad}`,
    stroke: size * 0.011,
    underlay: size * 0.024,
    font: size * 0.03,
    marker: size * 0.014,
    cornerDot: size * 0.006,
  };
}

export function outlinePath(outline: [number, number][]): string {
  return outline.map(([x, y], i) => `${i === 0 ? "M" : "L"}${x},${y}`).join(" ") + " Z";
}

export function cornerLabel(corner: Pick<CircuitCorner, "number" | "letter">): string {
  return `${corner.number}${corner.letter ?? ""}`;
}
