export interface Race {
  race_id: number;
  name: string;
  location: string;
  date: string;
  round: number;
  total_laps: number;
  summary: string | null;
  fastest_lap_driver: string | null;
  fastest_lap_time: string | null;
  fastest_lap_number: number | null;
  fastest_lap_team: string | null;
  air_temp: number | null;
  track_temp: number | null;
  rainfall: string | null;
}

export interface DriverResult {
  driver_id: number;
  position: number;
  grid_position: number | null;
  full_name: string;
  abbreviation: string;
  team: string;
  time: string;
  fastest_lap: string;
}

export interface LapEntry {
  driver: string;
  lap_number: number;
  position: number;
}

export interface ChampionshipEntry {
  full_name: string;
  team: string;
  points: number;
}

