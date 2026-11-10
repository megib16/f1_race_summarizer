"use client";

import { useRaceDashboard } from "./lib/use-race-dashboard";
import CircuitMap from "./components/CircuitMap";
import KeyRaceFacts from "./components/KeyRaceFacts";
import FinishingOrder from "./components/FinishingOrder";
import PositionProgression from "./components/PositionProgression";
import TyreStints from "./components/TyreStints";
import ChampionshipStandings from "./components/ChampionshipStandings";

export default function Home() {
  const { race, results, lapData, pitstops, allRaces, championship, loadState,
    championshipError, raceErrors, circuit, loadingSections, selectRace } = useRaceDashboard();
  const season = race?.date?.slice(0, 4);
  const circuitName = circuit.kind === "available" ? circuit.map.circuit_name : null;

  return (
    <main className="min-h-screen bg-[#212121] text-white px-4 sm:px-8 py-4 sm:py-8 overflow-x-hidden">
      <div className="mx-auto max-w-6xl">
        <header className="text-center">
          {allRaces.length > 0 && (
            <select
              aria-label="Choose a race"
              value={race?.race_id ?? ""}
              onChange={(e) => {
                const picked = allRaces.find((r) => r.race_id === Number(e.target.value));
                if (picked) selectRace(picked);
              }}
              style={{ fontFamily: "Playfair" }}
              className="w-full sm:w-auto max-w-full px-3 py-2 sm:px-4 sm:py-3 rounded text-base sm:text-xl bg-gray-700 text-gray-300"
            >
              {[...allRaces].reverse().map((r) => (
                <option key={r.race_id} value={r.race_id}>
                  R{r.round} · {r.name}
                </option>
              ))}
            </select>
          )}

          {loadState === "error" && (
            <p role="alert" className="mt-6 text-xl text-red-400">
              Could not reach the race API. Check that the backend is running and try again.
            </p>
          )}
          {loadState === "empty" && <p className="mt-6 text-xl text-gray-400">No races have been loaded yet.</p>}
          {raceErrors.map((error) => <p key={error} role="alert" className="mt-6 text-xl text-red-400">{error}</p>)}

          <h1 style={{ fontFamily: "BitcountSingle_Cursive-SemiBold" }} className="mt-6 text-4xl sm:text-6xl lg:text-7xl font-bold text-red-600 break-words">
            {race ? race.name.toUpperCase() : loadState === "loading" ? "Loading..." : "F1 RACES"}
          </h1>
          {race && (
            <p style={{ fontFamily: "Playfair" }} className="mt-2 text-lg sm:text-2xl text-white">
              Round {race.round} · {race.date} · {race.location}
              {circuitName ? ` · ${circuitName}` : ""} · {race.total_laps} laps
            </p>
          )}
        </header>
        <section aria-label="Circuit map" className="mt-6 sm:mt-8 rounded-lg bg-[#1a1a1a] p-3 sm:p-6">
          <CircuitMap state={circuit} season={season} />
        </section>
        <KeyRaceFacts race={race} results={results} />
        <FinishingOrder results={results} loading={loadingSections.results} />
        <PositionProgression results={results} lapData={lapData} pitstops={pitstops} loading={loadingSections.laps} />
        <TyreStints results={results} lapData={lapData} pitstops={pitstops} totalLaps={race?.total_laps ?? 0} />
        <ChampionshipStandings race={race} championship={championship} loading={loadingSections.championship} championshipError={championshipError} />
      </div>
    </main>
  );
}
