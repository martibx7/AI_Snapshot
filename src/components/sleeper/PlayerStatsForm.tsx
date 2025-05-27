import React, { useState } from 'react';
import axios from 'axios';

const PlayerStatsForm = () => {
  const [playerName, setPlayerName] = useState('');
  const [stats, setStats] = useState(null);
  const [error, setError] = useState(null);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setStats(null);

    try {
      const response = await axios.get(`/api/player-stats/${playerName}`);
      setStats(response.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'An error occurred');
    }
  };

  return (
    <div>
      <form onSubmit={handleSearch}>
        <input
          type="text"
          value={playerName}
          onChange={(e) => setPlayerName(e.target.value)}
          placeholder="Enter player name"
        />
        <button type="submit">Search</button>
      </form>

      {error && <p style={{ color: 'red' }}>{error}</p>}

      {stats && (
        <div>
          <h2>Player Stats</h2>
          <h3>Standard Stats</h3>
          <pre>{JSON.stringify(stats.standard_stats, null, 2)}</pre>

          <h3>Advanced Stats</h3>
          <pre>{JSON.stringify(stats.advanced_stats, null, 2)}</pre>
        </div>
      )}
    </div>
  );
};

export default PlayerStatsForm;
