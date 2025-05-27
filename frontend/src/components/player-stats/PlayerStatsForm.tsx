"use client";
import React, { useState } from 'react';
import axios from 'axios';

// Define an interface for the expected stats structure from your API
// This should match the Pydantic model 'PlayerStats' you defined for the backend.
interface PlayerSeasonDetailedStats {
  games_played?: number;
  completions?: number;
  passing_attempts?: number; // Or 'attempts' if you didn't use an alias
  passing_yards?: number;
  passing_tds?: number;
  interceptions?: number;
  sacks_taken?: number;
  passing_first_downs?: number;
  carries?: number;
  rushing_yards?: number;
  rushing_tds?: number;
  rushing_fumbles?: number;
  rushing_first_downs?: number;
  receptions?: number;
  targets?: number;
  receiving_yards?: number;
  receiving_tds?: number;
  receiving_fumbles?: number;
  receiving_first_downs?: number;
  fantasy_points?: number;
  fantasy_points_ppr?: number;
  passing_air_yards?: number;
  passing_yards_after_catch?: number;
  passing_epa?: number;
  avg_time_to_throw?: number;
  avg_completed_air_yards?: number;
  rushing_epa?: number;
  rush_yards_over_expected?: number; // Or 'yards_over_expected'
  efficiency?: number;
  receiving_air_yards?: number;
  rec_yards_after_catch?: number; // Or 'receiving_yards_after_catch'
  target_share?: number;
  air_yards_share?: number;
  wopr?: number;
  avg_separation?: number;
  avg_cushion?: number;
  // Add any other fields from PlayerSeasonDetailedStats Pydantic model
}

interface PlayerSeasonData {
  season: number;
  player_id_from_source: string; // Important for unique keys if player has multiple stints in a season (rare)
  player_display_name: string;
  position?: string;
  team_abbr: string;
  stats: PlayerSeasonDetailedStats;
}

interface ApiPlayerStatsResponse {
  query_player_name: string;
  matched_player_id?: string;
  matched_player_display_name?: string;
  current_position?: string;
  stats_by_season: PlayerSeasonData[];
  error_message?: string;
}

const PlayerStatsForm = () => {
  const [playerName, setPlayerName] = useState('');
  const [statsData, setStatsData] = useState<ApiPlayerStatsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setStatsData(null);
    setLoading(true);

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_BASE_URL; // This should be "http://127.0.0.1:8000/api/v1" from your .env.local

      if (!apiUrl) {
        console.error("NEXT_PUBLIC_API_BASE_URL environment variable is not set.");
        setError("API configuration error. Please check a_admin_n."); // A more user-friendly message
        setLoading(false);
        return;
      }

      // Construct the URL correctly:
      // apiUrl is "http://127.0.0.1:8000/api/v1"
      // We want to hit "http://127.0.0.1:8000/api/v1/player-stats/{playerName}"
      const response = await axios.get(`${apiUrl}/player-stats/${playerName}`);
      setStatsData(response.data);

    } catch (err: any) {
      let message = 'An error occurred while fetching player stats.';
      if (err.response) {
        // The request was made and the server responded with a status code
        // that falls out of the range of 2xx
        console.error('API Error Response:', err.response);
        message = err.response.data?.detail || `Error: ${err.response.status} - ${err.response.statusText}`;
      } else if (err.request) {
        // The request was made but no response was received
        console.error('API No Response:', err.request);
        message = 'No response from server. Please check your network or if the backend is running.';
      } else {
        // Something happened in setting up the request that triggered an Error
        console.error('Axios Setup Error:', err.message);
        message = err.message;
      }
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <form onSubmit={handleSearch}>
        <input
          type="text"
          value={playerName}
          onChange={(e) => setPlayerName(e.target.value)}
          placeholder="Enter player name (e.g., Patrick Mahomes)"
          disabled={loading}
        />
        <button type="submit" disabled={loading}>
          {loading ? 'Searching...' : 'Search'}
        </button>
      </form>

      {error && <p style={{ color: 'red' }}>{error}</p>}

      {statsData && !statsData.error_message && (
        <div>
          <h2>Stats for {statsData.matched_player_display_name || statsData.query_player_name}</h2>
          {statsData.current_position && <p>Position: {statsData.current_position}</p>}

          {statsData.stats_by_season && statsData.stats_by_season.length > 0 ? (
            statsData.stats_by_season.map((seasonData) => (
              // Using a more unique key if player_id_from_source is available per season entry
              <div key={`${seasonData.player_id_from_source}-${seasonData.season}`} style={{ border: '1px solid #ccc', margin: '10px', padding: '10px' }}>
                <h3>{seasonData.season} Season ({seasonData.team_abbr})</h3>
                <p><strong>Player:</strong> {seasonData.player_display_name} ({seasonData.position || 'N/A'})</p>
                <h4>Stats:</h4>
                {/* You'll want to render these stats more nicely than JSON.stringify */}
                <pre>{JSON.stringify(seasonData.stats, null, 2)}</pre>
                {/* Example of rendering specific stats:
                <p>Passing Yards: {seasonData.stats.passing_yards ?? 'N/A'}</p>
                <p>Rushing TDs: {seasonData.stats.rushing_tds ?? 'N/A'}</p>
                <p>Receptions: {seasonData.stats.receptions ?? 'N/A'}</p>
                <p>PPR Points: {seasonData.stats.fantasy_points_ppr ?? 'N/A'}</p>
                */}
              </div>
            ))
          ) : (
            <p>No season stats found for this player.</p>
          )}
        </div>
      )}
      {/* Display error message if it's part of the successful API response data */}
      {statsData?.error_message && <p style={{ color: 'orange' }}>Notice: {statsData.error_message}</p>}
    </div>
  );
};

export default PlayerStatsForm;