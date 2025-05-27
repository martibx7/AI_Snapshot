# backend/services/nfl_data_service.py
print("--- LOADING NFL_DATA_SERVICE.PY - V_FINAL_STAT_MAPPING ---") # New version

import nfl_data_py as nfl
import pandas as pd
import traceback
import urllib

def get_player_stats(player_name_query: str):
    print(f"--- ENTERED get_player_stats (Final Stat Mapping) ---")
    print(f"Service: Received player_name_query: '{player_name_query}'")

    service_response = {
        "query_player_name": player_name_query,
        "matched_player_id": None,
        "matched_player_display_name": None,
        "current_position": None,
        "stats_by_season": [],
        "error_message": None
    }
    player_id_val = None

    try:
        # Step 1: Player Lookup (Verified Working)
        roster_years = list(range(pd.Timestamp.now().year - 3, pd.Timestamp.now().year + 1))
        all_rosters_df = pd.DataFrame()
        for year in roster_years:
            try:
                df = nfl.import_seasonal_rosters(years=[year])
                if not df.empty:
                    all_rosters_df = pd.concat([all_rosters_df, df], ignore_index=True)
            except Exception as e_roster:
                print(f"Warning: Could not fetch nfl_data_py roster for year {year}: {e_roster}")

        if all_rosters_df.empty:
            service_response["error_message"] = "Roster data source is currently unavailable to find player."
            return service_response

        id_column_roster = 'player_id'
        name_column_roster = 'player_name'
        position_column_roster = 'position'

        if id_column_roster not in all_rosters_df.columns or name_column_roster not in all_rosters_df.columns:
            service_response["error_message"] = "Internal server error processing roster data (missing columns)."
            return service_response

        all_rosters_df = all_rosters_df.drop_duplicates(subset=[id_column_roster])
        player_search_df = pd.DataFrame()
        if player_name_query and isinstance(player_name_query, str):
            player_search_df = all_rosters_df[
                all_rosters_df[name_column_roster].astype(str).str.contains(player_name_query, case=False, na=False)
            ]

        if player_search_df.empty:
            service_response["error_message"] = f"Player '{player_name_query}' not found in rosters."
            return service_response

        player_series = player_search_df.iloc[0]
        player_id_val = player_series[id_column_roster]
        matched_player_name_val = player_series[name_column_roster]
        position_val = player_series.get(position_column_roster)

        service_response["matched_player_id"] = str(player_id_val)
        service_response["matched_player_display_name"] = str(matched_player_name_val)
        service_response["current_position"] = str(position_val) if pd.notna(position_val) else None
        print(f"Service: Player Lookup Successful - ID: {player_id_val}, Name: {matched_player_name_val}, Pos: {position_val}")

        # Step 2: Fetch Seasonal Stats Year by Year (Verified Working)
        current_py_year = pd.Timestamp.now().year
        potential_stat_years = list(range(1999, current_py_year))
        successfully_fetched_yearly_dfs = []

        for year_to_try in potential_stat_years:
            try:
                yearly_df = nfl.import_seasonal_data(years=[year_to_try], s_type='ALL') # Keep s_type='ALL' for now
                if not yearly_df.empty:
                    successfully_fetched_yearly_dfs.append(yearly_df)
            except urllib.error.HTTPError as e_http:
                if e_http.code == 404: print(f"Service: Data not found (404) for year {year_to_try}. Skipping.")
                else: print(f"Service: HTTPError (code: {e_http.code}) for year {year_to_try}: {e_http}. Skipping.")
            except Exception as e_year: print(f"Service: General error for year {year_to_try}: {e_year}. Skipping.")

        if not successfully_fetched_yearly_dfs:
            service_response["error_message"] = f"No seasonal stats data could be fetched for {matched_player_name_val}."
            return service_response

        seasonal_stats_df_all_players = pd.concat(successfully_fetched_yearly_dfs, ignore_index=True)

        id_column_seasonal = 'player_id' # From your DEBUG output

        player_all_seasons_stats_df = seasonal_stats_df_all_players[
            seasonal_stats_df_all_players[id_column_seasonal] == player_id_val
            ].copy()

        if player_all_seasons_stats_df.empty:
            service_response["error_message"] = f"No specific seasonal stats entries found for {matched_player_name_val}."
            return service_response

        # --- Fix for React Key Warning: Filter for regular season only ---
        # The 'season_type' column in your debug output is key here.
        # This ensures one row per player per actual season year.
        if 'season_type' in player_all_seasons_stats_df.columns:
            player_all_seasons_stats_df = player_all_seasons_stats_df[player_all_seasons_stats_df['season_type'] == 'REG'].copy()
            print(f"Service: Filtered for REG season_type. Rows remaining: {len(player_all_seasons_stats_df)}")
        else:
            print("Warning: 'season_type' column not found in seasonal stats. Cannot filter for REG season. React key warning might persist if there are duplicates per season.")

        if player_all_seasons_stats_df.empty: # Check again after filtering
            service_response["error_message"] = f"No regular season stats found for {matched_player_name_val}."
            return service_response

        player_all_seasons_stats_df.loc[:, 'season'] = player_all_seasons_stats_df['season'].astype(int)

        seasons_data = []
        # You can remove this debug print once stat mapping is confirmed:
        # print(f"DEBUG: Columns for stat mapping for '{matched_player_name_val}': {player_all_seasons_stats_df.columns.tolist()}")

        for _, row in player_all_seasons_stats_df.sort_values(by='season').iterrows():
            # --- USER ACTION: Verify ALL these row.get() calls with your DEBUG output ---
            detailed_stats = {
                "games_played": row.get('games'), # Your log has 'games'
                "completions": row.get('completions'),
                "passing_attempts": row.get('attempts'),
                "passing_yards": row.get('passing_yards'),
                "passing_tds": row.get('passing_tds'),
                "interceptions": row.get('interceptions'),
                "sacks_taken": row.get('sacks'),
                "passing_first_downs": row.get('passing_first_downs'),
                "carries": row.get('carries'),
                "rushing_yards": row.get('rushing_yards'),
                "rushing_tds": row.get('rushing_tds'),
                "rushing_fumbles": row.get('rushing_fumbles_lost') or row.get('rushing_fumbles'), # Prefer fumbles_lost if available
                "rushing_first_downs": row.get('rushing_first_downs'),
                "receptions": row.get('receptions'),
                "targets": row.get('targets'),
                "receiving_yards": row.get('receiving_yards'),
                "receiving_tds": row.get('receiving_tds'),
                "receiving_fumbles": row.get('receiving_fumbles_lost') or row.get('receiving_fumbles'),
                "receiving_first_downs": row.get('receiving_first_downs'),
                "fantasy_points": row.get('fantasy_points'),
                "fantasy_points_ppr": row.get('fantasy_points_ppr'),
                "passing_air_yards": row.get('passing_air_yards'),
                "passing_yards_after_catch": row.get('passing_yards_after_catch'),
                "passing_epa": row.get('passing_epa'),
                # For the next 3, if not directly in seasonal_data, they'd come from aggregated NGS data
                "avg_time_to_throw": row.get('avg_time_to_throw'), # Placeholder - likely from NGS
                "avg_completed_air_yards": row.get('avg_completed_air_yards'), # Placeholder - likely from NGS
                "rushing_epa": row.get('rushing_epa'),
                "rush_yards_over_expected": row.get('rushing_yards_over_expected'), # Placeholder if not in seasonal
                "efficiency": row.get('rushing_efficiency'), # Placeholder if not in seasonal
                "receiving_air_yards": row.get('receiving_air_yards'),
                "rec_yards_after_catch": row.get('receiving_yards_after_catch'),
                "target_share": row.get('tgt_sh') or row.get('target_share'), # Your log has 'tgt_sh'
                "air_yards_share": row.get('ay_sh') or row.get('air_yards_share'), # Your log has 'ay_sh'
                "wopr": row.get('wopr_x') or row.get('wopr_y') or row.get('wopr'), # Your log has wopr_x and wopr_y
                # Add other specific market share stats from your log if desired:
                # 'yac_sh', 'ry_sh', 'rtd_sh', 'rfd_sh', 'rtdfd_sh', 'dom', 'w8dom', 'yptmpa', 'ppr_sh'
                "avg_separation": row.get('avg_separation'), # Placeholder - likely from NGS
                "avg_cushion": row.get('avg_cushion'),       # Placeholder - likely from NGS
            }
            seasons_data.append({
                "season": int(row['season']),
                "player_id_from_source": str(player_id_val),
                "player_display_name": str(row.get('player_name', matched_player_name_val)),
                "position": str(row.get('position', position_val)) if pd.notna(row.get('position', position_val)) else None,
                "team_abbr": str(row.get('team', 'UNK')), # 'team' seems to be the per-season team in seasonal_stats
                "stats": detailed_stats
            })

        service_response["stats_by_season"] = seasons_data
        service_response["error_message"] = None
        print(f"Service: Successfully processed seasonal stats for {matched_player_name_val}. Found {len(seasons_data)} REG seasons.")
        return service_response

    except Exception as e_global:
        print(f"Service Error: Top-level unexpected error for '{player_name_query}': {str(e_global)}")
        print(traceback.format_exc())
        service_response["error_message"] = "A critical internal server error occurred while processing player data."
        return service_response