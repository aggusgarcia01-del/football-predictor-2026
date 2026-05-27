export type Team = {
  id: string;
  name: string;
  confederation: string;
  elo: number;
};

export type Venue = {
  id: string;
  city: string;
  country: string;
  altitude_meters: number;
  avg_temp_c: number;
  avg_humidity: number;
  surface_type: string;
};

export type MatchView = {
  id: string;
  date: string;
  stage: string;
  home_team: Team;
  away_team: Team;
  venue: Venue;
};

export type MarketProbability = {
  selection: string;
  probability: number;
  odds?: number | null;
  implied_probability?: number | null;
  ev?: number | null;
  confidence_tier?: string | null;
};

export type Prediction = {
  match: MatchView;
  status: string;
  disclaimer: string;
  expected_goals_home: number;
  expected_goals_away: number;
  markets: Record<string, MarketProbability[]>;
};

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`API request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export async function getMatches(): Promise<MatchView[]> {
  return getJson<MatchView[]>("/matches");
}

export async function getPrediction(matchId: string): Promise<Prediction> {
  return getJson<Prediction>(`/predictions/${matchId}`);
}

