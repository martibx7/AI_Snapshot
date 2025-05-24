# services/sleeper_weekly_proj_service.py
import httpx
import asyncio
from typing import Dict, Any, Optional, List
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from models import Player, WeeklyProjection # Ensure WeeklyProjection is defined in models.py
# from utils.player_utils import to_int_or_none, to_float_or_none # If needed for stats

# --- Constants ---
SLEEPER_WEEKLY_PROJ_API_URL_TEMPLATE = "https://api.sleeper.app/projections/nfl/player/{player_id}?season_type=regular&season={season}&grouping=week"
API_CALL_DELAY_SECONDS = 0.2 # Be polite to the Sleeper API

async def fetch_weekly_projections_for_player(
        client: httpx.AsyncClient,
        player_id: str,
        season: int
) -> Optional[Dict[str, Any]]: # Returns a dict where keys are week numbers (strings)
    """Fetches all weekly projection data for a single player for a given season."""
    url = SLEEPER_WEEKLY_PROJ_API_URL_TEMPLATE.format(player_id=player_id, season=season)
    try:
        response = await client.get(url, timeout=20.0)
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict): # Expecting a dictionary keyed by week
            print(f"Unexpected data format (not a dict) for player {player_id}, season {season}. Data: {data}")
            return None
        return data
    except httpx.RequestError as e:
        print(f"HTTP error fetching weekly projections for player {player_id}: {e}")
        return None
    except Exception as e:
        print(f"General error fetching weekly projections for player {player_id}: {e}")
        return None

async def run_sleeper_weekly_projection_ingestion(
        session: AsyncSession,
        target_season: Optional[int] = None,
        specific_week: Optional[int] = None # Option to run for only one week
):
    if target_season is None:
        target_season = datetime.now().year

    service_name = f"Sleeper Weekly Projections (Season: {target_season}"
    if specific_week:
        service_name += f", Week: {specific_week}"
    service_name += ")"
    print(f"Starting {service_name} ingestion service...")

    # 1. Fetch active, relevant players from your Player table
    stmt_players = select(Player).where(
        Player.position.in_(['QB', 'RB', 'WR', 'TE']) # type: ignore
    ).where(Player.status == "Active")
    active_players_result = await session.execute(stmt_players)
    players_to_process = active_players_result.scalars().all()

    if not players_to_process:
        print(f"No active players (QB, RB, WR, TE) found to fetch weekly projections for {service_name}.")
        return {"message": "No active players found.", "projections_upserted": 0}

    print(f"Found {len(players_to_process)} active players for {service_name}.")
    upserted_count = 0
    total_projections_processed = 0

    async with httpx.AsyncClient() as client:
        for player in players_to_process:
            if not player.player_id:
                continue

            # print(f"Fetching weekly projections for player: {player.player_name} (ID: {player.player_id})")
            weekly_data_map = await fetch_weekly_projections_for_player(client, player.player_id, target_season)

            if weekly_data_map:
                for week_str, week_proj_data in weekly_data_map.items():
                    try:
                        week_num = int(week_str)
                        if specific_week is not None and week_num != specific_week:
                            continue # Skip if processing a specific week and this isn't it

                        if not week_proj_data or 'stats' not in week_proj_data:
                            # print(f"  Skipping week {week_num} for player {player.player_id} - no stats or data.")
                            continue

                        total_projections_processed += 1
                        stats = week_proj_data.get('stats', {})

                        # Upsert logic: Find existing or create new
                        stmt_existing = select(WeeklyProjection).where(
                            WeeklyProjection.player_id == player.player_id, # type: ignore
                            WeeklyProjection.week == week_num, # type: ignore
                            WeeklyProjection.season == target_season # type: ignore
                        )
                        existing_proj_result = await session.execute(stmt_existing)
                        db_weekly_proj = existing_proj_result.scalar_one_or_none()

                        if not db_weekly_proj:
                            db_weekly_proj = WeeklyProjection(
                                player_id=player.player_id,
                                week=week_num,
                                season=target_season
                            )
                            # created = True
                        # else:
                        # created = False

                        # Populate/Update fields
                        # Non-stat fields from week_proj_data
                        db_weekly_proj.opponent = week_proj_data.get('opponent')
                        db_weekly_proj.team = player.team # Use team from Player table for consistency
                        db_weekly_proj.company = week_proj_data.get('company', 'Sleeper') # Or 'source'
                        db_weekly_proj.game_id = week_proj_data.get('game_id')

                        date_str = week_proj_data.get('date') # API 'date' field
                        if date_str:
                            try:
                                # Sleeper API date is usually YYYY-MM-DD
                                db_weekly_proj.projection_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                            except ValueError:
                                print(f"Warning: Could not parse date '{date_str}' for player {player.player_id} week {week_num}")
                                db_weekly_proj.projection_date = None
                        else:
                            db_weekly_proj.projection_date = None


                        # Statistical fields from stats dict
                        # Ensure these keys match your WeeklyProjection model and Sleeper API
                        db_weekly_proj.rush_yd = stats.get('rush_yd')
                        db_weekly_proj.rush_fd = stats.get('rush_fd')
                        db_weekly_proj.rush_att = stats.get('rush_att')
                        db_weekly_proj.rec_yd = stats.get('rec_yd')
                        db_weekly_proj.rec_tgt = stats.get('rec_tgt')
                        db_weekly_proj.rec_td_40p = stats.get('rec_td_40p')
                        db_weekly_proj.rec_td = stats.get('rec_td')
                        db_weekly_proj.rec_fd = stats.get('rec_fd')
                        db_weekly_proj.rec_5_9 = stats.get('rec_5_9')
                        db_weekly_proj.rec_40p = stats.get('rec_40p')
                        db_weekly_proj.rec_30_39 = stats.get('rec_30_39')
                        db_weekly_proj.rec_20_29 = stats.get('rec_20_29')
                        db_weekly_proj.rec_10_19 = stats.get('rec_10_19')
                        db_weekly_proj.rec_0_4 = stats.get('rec_0_4')
                        db_weekly_proj.rec = stats.get('rec')
                        db_weekly_proj.pts_std = stats.get('pts_std')
                        db_weekly_proj.pts_ppr = stats.get('pts_ppr')
                        db_weekly_proj.pts_half_ppr = stats.get('pts_half_ppr')
                        db_weekly_proj.pos_adp_dd_ppr = stats.get('pos_adp_dd_ppr') # Verify this key
                        db_weekly_proj.gp = stats.get('gp')
                        db_weekly_proj.fum_lost = stats.get('fum_lost')
                        db_weekly_proj.fum = stats.get('fum')
                        db_weekly_proj.bonus_rec_wr = stats.get('bonus_rec_wr')
                        db_weekly_proj.adp_dd_ppr = stats.get('adp_dd_ppr') # Verify this key

                        # created_at and updated_at_db are handled by model defaults/onupdate

                        session.add(db_weekly_proj)
                        upserted_count +=1
                        # Optional: log creation/update per record
                        # action = "Created" if created else "Updated"
                        # print(f"  {action} weekly (Wk{week_num}) projection for {player.player_name} (ID: {player.player_id})")

                    except ValueError: # For int(week_str)
                        print(f"Warning: Could not parse week number '{week_str}' for player {player.player_id}")
                    except Exception as e_week_proc:
                        print(f"Error processing week {week_str} for player {player.player_id}: {e_week_proc}")

            if API_CALL_DELAY_SECONDS > 0:
                await asyncio.sleep(API_CALL_DELAY_SECONDS) # Be polite after each player's full weekly data

    try:
        await session.commit()
        print(f"{service_name} ingestion successful. Upserted/Processed: {upserted_count} weekly projection records (from {total_projections_processed} raw projections).")
    except Exception as e:
        await session.rollback()
        print(f"Error during {service_name} database commit: {e}")
        import traceback
        traceback.print_exc()
        raise

    return {"message": f"{service_name} ingestion complete.", "projections_upserted": upserted_count}