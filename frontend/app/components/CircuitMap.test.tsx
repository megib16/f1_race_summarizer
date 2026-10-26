import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import CircuitMap from "./CircuitMap";
import type { CircuitMapData } from "../lib/circuit-utils";

const map: CircuitMapData = {
  circuit_name: "Test Circuit",
  year: 2026,
  width: 1000,
  height: 600,
  outline: [[0, 0], [1000, 0], [1000, 600], [0, 600], [0, 0]],
  corners: [
    { number: 1, letter: "", x: 1000, y: 0, label_x: 1030, label_y: 0 },
    { number: 2, letter: "A", x: 1000, y: 600, label_x: 1030, label_y: 630 },
  ],
  start: { x: 100, y: 0, ahead_x: 140, ahead_y: 0 },
};

describe("CircuitMap", () => {
  it("draws the outline, every supplied corner label and the start marker", () => {
    const html = renderToStaticMarkup(<CircuitMap state={{ kind: "available", map }} />);

    expect(html).toContain("<svg");
    expect(html).toContain('viewBox="-60 -60 1120 720"');
    expect(html).toContain(">1</text>");
    expect(html).toContain(">2A</text>");
    expect(html).toContain("<rect"); // start marker
    expect(html).toContain("Start / finish (approximate)");
    expect(html).toContain("Layout as of 2026");
    expect(html).toContain("Sector boundaries are not shown");
  });

  it("draws no start marker or corner labels when the data does not support them", () => {
    const html = renderToStaticMarkup(
      <CircuitMap state={{ kind: "available", map: { ...map, start: null, corners: [] } }} />,
    );

    expect(html).toContain("<path");
    expect(html).not.toContain("<rect");
    expect(html).not.toContain("<text");
    expect(html).not.toContain("Start / finish");
  });

  it("shows a clear message and no drawing when the map is unavailable", () => {
    const html = renderToStaticMarkup(<CircuitMap state={{ kind: "unavailable", reason: "no_data" }} />);

    expect(html).toContain("No circuit geometry is available");
    expect(html).not.toContain("<svg");
  });

  it("has distinct loading and error states", () => {
    expect(renderToStaticMarkup(<CircuitMap state={{ kind: "loading" }} />)).toContain("Loading circuit map");
    expect(renderToStaticMarkup(<CircuitMap state={{ kind: "error" }} />)).toContain("Could not load the circuit map");
  });
});
