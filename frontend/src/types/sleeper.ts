// frontend/src/types/sleeper.ts

export interface LeagueSettingDetails {
  type?: number | null;
  playoff_week_start?: number | null;
  // Add other relevant settings from your backend Pydantic model as they are added
}

export interface RosterDetail {
  roster_id: number;
  owner_id?: string | null;
  owner_display_name?: string | null;
  players?: string[] | null; // List of player_ids
  wins?: number | null;
  losses?: number | null;
  ties?: number | null;
  fpts?: number | null;
}

export interface LeagueDetails {
  league_id: string;
  name: string;
  season: string;
  status: string;
  total_rosters: number;
  scoring_settings?: Record<string, any> | null;
  roster_positions?: string[] | null;
  settings?: LeagueSettingDetails | null;
  rosters: RosterDetail[];
}

// You can also move other shared Sleeper-related types here if you have them,
// for example, the BasicSleeperLeague type if it's used in multiple places.
export interface BasicSleeperLeague {
  league_id: string;
  name: string;
  season: string;
  // Add other relevant league properties
}

export interface SleeperResolvedUser {
    user_id: string;
    display_name: string;
    error?: string;
}