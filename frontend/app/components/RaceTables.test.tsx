// @vitest-environment jsdom
import { afterEach, expect, it } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import FinishingOrder from "./FinishingOrder";
import ChampionshipStandings from "./ChampionshipStandings";
import { DriverResult } from "../lib/race-types";

afterEach(cleanup);

const drivers: DriverResult[] = Array.from({ length: 12 }, (_, i) => ({
  driver_id: i + 1, position: i + 1, grid_position: 12 - i,
  full_name: `Driver ${i + 1}`, abbreviation: `D${i + 1}`, team: "Ferrari",
  time: "0 days 00:00:02.000", fastest_lap: "",
}));

it("finishing order keeps the expandable results and loading indicator", () => {
  render(<FinishingOrder results={drivers} loading />);
  expect(screen.getByRole("status").textContent).toBe("Loading results…");
  expect(screen.queryByText("Driver 12")).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "▼ Show all" }));
  expect(screen.getByText("Driver 12")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "▲ Show less" }));
  expect(screen.queryByText("Driver 12")).toBeNull();
});

it("standings retain driver rows when reordered and identify the selected round", () => {
  const race = { name: "Test GP", date: "2026-03-01", round: 1 };
  const championship = drivers.map((d) => ({ full_name: d.full_name, team: d.team, points: 20 - d.position }));
  const { rerender } = render(<ChampionshipStandings race={race} championship={championship} loading={false} championshipError={null} />);
  expect(screen.getByText(/standings after round 1/)).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "▼ Show all" }));
  const firstDriverRow = screen.getByText("Driver 1").closest("tr");
  rerender(<ChampionshipStandings race={{ ...race, round: 2 }} championship={[...championship].reverse()} loading={false} championshipError={null} />);
  expect(screen.getByText(/standings after round 2/)).toBeTruthy();
  expect(screen.getByText("Driver 1").closest("tr")).toBe(firstDriverRow);
});

it("standings distinguish loading, empty results and errors", () => {
  const race = { name: "Test GP", date: "2026-03-01", round: 1 };
  const { rerender } = render(<ChampionshipStandings race={race} championship={[]} loading championshipError={null} />);
  expect(screen.getByRole("status").textContent).toBe("Loading standings…");
  expect(screen.queryByText("No standings available.")).toBeNull();
  rerender(<ChampionshipStandings race={race} championship={[]} loading={false} championshipError={null} />);
  expect(screen.getByText("No standings available.")).toBeTruthy();
  rerender(<ChampionshipStandings race={race} championship={[]} loading={false} championshipError="Results incomplete" />);
  expect(screen.getByRole("alert").textContent).toBe("Results incomplete");
  expect(screen.queryByText("No standings available.")).toBeNull();
});
