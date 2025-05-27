import React from 'react';
import PlayerStatsForm from '@/components/player-stats/PlayerStatsForm'; // Updated import path

const PlayerStatsPage = () => {
  return (
    <div style={{ padding: '20px' }}> {/* Example styling */}
      <h1>NFL Player Stats Lookup</h1>
      <p>Enter the name of an NFL player to see their yearly standard and advanced fantasy stats.</p>
      <PlayerStatsForm />
    </div>
  );
};

export default PlayerStatsPage;