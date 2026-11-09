"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { CircuitState } from "../components/CircuitMap";
import { CircuitResponse } from "./circuit-utils";
import { PitStop, byDateAscending } from "./race-utils";
import { Race, DriverResult, LapEntry, ChampionshipEntry } from "./race-types";
import { ApiError, getJson, getPages } from "./api-client";

export function useRaceDashboard() {
  const [race, setRace] = useState<Race | null>(null);
  const [results, setResults] = useState<DriverResult[]>([]);
  const [lapData, setLapData] = useState<LapEntry[]>([]);
  const [pitstops, setPitStops] = useState<PitStop[]>([]);
  const [allRaces, setAllRaces] = useState<Race[]>([]);
  const [championship, setChampionship] = useState<ChampionshipEntry[]>([]);
  const [loadState, setLoadState] = useState<"loading" | "ready" | "empty" | "error">("loading");
  const [championshipError, setChampionshipError] = useState<string | null>(null);
  const [raceErrors, setRaceErrors] = useState<string[]>([]);
  const [circuit, setCircuit] = useState<CircuitState>({ kind: "loading" });
  const [loadingSections, setLoadingSections] = useState({ results: false, laps: false, pits: false, championship: false });
  const active = useRef<AbortController | null>(null);

  const selectRace = useCallback((r: Race) => {
    active.current?.abort();
    const controller = new AbortController();
    active.current = controller;
    const { signal } = controller;
    setRace(r);
    setRaceErrors([]);
    setResults([]);
    setLapData([]);
    setPitStops([]);
    setChampionship([]);
    setChampionshipError(null);
    setCircuit({ kind: "loading" });
    const season = r.date?.slice(0, 4);
    const hasScope = Boolean(season && r.round != null);
    setLoadingSections({ results: true, laps: true, pits: true, championship: hasScope });

    getJson<CircuitResponse>(`/races/${r.race_id}/circuit`, signal)
      .then((c) => {
        if (!signal.aborted) setCircuit(c.status === "available" && c.map
          ? { kind: "available", map: c.map } : { kind: "unavailable", reason: c.reason });
      })
      .catch(() => { if (!signal.aborted) setCircuit({ kind: "error" }); });

    function load<T>(section: "results" | "laps" | "pits", task: Promise<T>, update: (data: T) => void) {
      task.then((data) => { if (!signal.aborted) update(data); })
        .catch(() => { if (!signal.aborted) setRaceErrors((errors) => [...errors, `Could not load ${section} for ${r.name}.`]); })
        .finally(() => { if (!signal.aborted) setLoadingSections((state) => ({ ...state, [section]: false })); });
    }
    load("results", getJson<DriverResult[]>(`/races/${r.race_id}/results`, signal),
      (rows) => setResults([...rows].sort((a, b) => a.position - b.position)));
    load("laps", getPages<LapEntry>(`/races/${r.race_id}/laps`, 10000, signal), setLapData);
    load("pits", getJson<PitStop[]>(`/races/${r.race_id}/pits`, signal), setPitStops);
    if (hasScope) {
      getJson<ChampionshipEntry[]>(`/championship?season=${season}&through_round=${r.round}`, signal)
        .then((rows) => { if (!signal.aborted) setChampionship(rows); })
        .catch((error: unknown) => {
          if (!signal.aborted) setChampionshipError(error instanceof ApiError && error.status === 409
            ? "Standings are waiting for complete race and sprint results."
            : "Could not load standings.");
        })
        .finally(() => { if (!signal.aborted) setLoadingSections((state) => ({ ...state, championship: false })); });
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    getPages<Race>("/races", 500, controller.signal)
      .then((races) => {
        if (controller.signal.aborted) return;
        if (races.length === 0) {
          setLoadState("empty");
          setCircuit({ kind: "unavailable", reason: "not_fetched" });
          return;
        }
        const sorted = byDateAscending(races);
        setAllRaces(sorted);
        setLoadState("ready");
        selectRace(sorted[sorted.length - 1]);
      })
      .catch(() => {
        if (!controller.signal.aborted) { setLoadState("error"); setCircuit({ kind: "error" }); }
      });
    return () => { controller.abort(); active.current?.abort(); };
  }, [selectRace]);

  return { race, results, lapData, pitstops, allRaces, championship, loadState,
    championshipError, raceErrors, circuit, loadingSections, selectRace };
}
