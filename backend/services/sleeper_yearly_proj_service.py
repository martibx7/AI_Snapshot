# services/sleeper_yearly_proj_service.py
import httpx
import asyncio
from typing import Dict, Any, Optional, List
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from models import Player, SleeperProjection # Make sure SleeperProjection is defined in models.py
# from utils.player_utils import to_int_or_none # If you need a similar helper for data conversion

# --- Constants ---
SLEEPER_PROJECTION_API_URL_TEMPLATE = "https://api.sleeper.app/projections/nfl/player/{player_id}?season_type=regular&season={season}&grouping=total"
# Consider a small delay between API calls if fetching for many players
API_CALL_DELAY_SECONDS = 0.2

async def fetch_sleeper_projection_for_player(
        client: httpx.AsyncClient,
        player_id: str,
        season: int
) -> Optional[Dict[str, Any]]:
    """Fetches projection data for a single player from the Sleeper API."""
    url = SLEEPER_PROJECTION_API_URL_TEMPLATE.format(player_id=player_id, season=season)
    try:
        response = await client.get(url, timeout=20.0)
        response.raise_for_status()
        data = response.json()
        if not data or 'stats' not in data: # Basic validation
            print(f"No valid projection data found for player {player_id}, season {season}.")
            return None
        # You might want to include player identifying info from the response if needed later,
        # though your old script extracts it from the 'player' sub-dict in the projection data.
        return data
    except httpx.RequestError as e:
        print(f"HTTP error fetching projection for player {player_id}: {e}")
        return None
    except Exception as e:
        print(f"General error fetching projection for player {player_id}: {e}")
        return None

async def run_sleeper_projection_ingestion(session: AsyncSession, current_season: Optional[int] = None):
    print(f"Starting Sleeper projection ingestion service for season {current_season}...")

    if current_season is None:
        current_season = datetime.now().year

    # 1. Fetch active players (QB, RB, WR, TE) from your Player table
    stmt_players = select(Player).where(
        Player.position.in_(['QB', 'RB', 'WR', 'TE']) # type: ignore
    ).where(Player.status == "Active")
    active_players_result = await session.execute(stmt_players)
    players_to_fetch = active_players_result.scalars().all()

    if not players_to_fetch:
        print("No active players found to fetch projections for.")
        return {"message": "No active players found.", "projections_updated_or_created": 0}

    print(f"Found {len(players_to_fetch)} active players to process for projections.")
    updated_or_created_count = 0

    async with httpx.AsyncClient() as client:
        for player in players_to_fetch:
            if not player.player_id: # Should not happen if player_id is primary key
                continue

            # print(f"Fetching projection for player: {player.player_name} ({player.player_id})")
            projection_data = await fetch_sleeper_projection_for_player(client, player.player_id, current_season)

            if projection_data:
                # The API response is a list containing one projection object
                # Ensure you handle if the list is empty or has multiple elements
                if isinstance(projection_data, list) and len(projection_data) > 0:
                    proj_item = projection_data[0] # Assuming the first item is the one we want
                elif isinstance(projection_data, dict): # Sometimes it's a single dict
                    proj_item = projection_data
                else:
                    print(f"Unexpected projection data format for player {player.player_id}")
                    continue

                # 2. Check if a projection already exists for this player_id and season
                stmt_existing_proj = select(SleeperProjection).where(
                    SleeperProjection.player_id == player.player_id # type: ignore
                ).where(SleeperProjection.season == current_season) # type: ignore
                existing_proj_result = await session.execute(stmt_existing_proj)
                db_projection = existing_proj_result.scalar_one_or_none()

                # Extract details (similar to your old script)
                # Ensure these keys match the Sleeper API response structure for projections
                # The projection API response might be a list of projections for different groups/types.
                # The example URL you used `grouping=total` suggests one item.

                # The API response for player projections is usually a LIST of projection objects.
                # Let's assume for `grouping=total` it returns a list with one item.
                # If proj_item is from response.json() and is a list: proj_details = proj_item[0]
                # If proj_item is already the dict: proj_details = proj_item

                # Based on your old script, the projection data structure is:
                # { 'player_id': '123', 'player': {'first_name': ..., 'last_name': ..., ...}, 'stats': {...}, ... }
                # The new API (https://api.sleeper.app/projections/nfl/player/{player_id}...)
                # returns a list of projection objects. Each object contains:
                # `player_id`, `stats`, `projected_points`, `company`, etc.
                # It does NOT typically include the nested `player` dictionary with first_name/last_name directly.
                # We already have player details from the `Player` object.

                stats = proj_item.get('stats', {})
                # player_details_from_proj = proj_item.get('player', {}) # Less likely in this API response

                if not db_projection:
                    db_projection = SleeperProjection(
                        player_id=player.player_id,
                        season=current_season,
                        # Default other fields or get from Player object if needed for SleeperProjection
                        # source = proj_item.get('source', 'sleeper') # API typically doesn't provide this
                        # first_name=player.first_name, # From your Player model
                        # last_name=player.last_name,   # From your Player model
                        # team=player.team,             # From your Player model
                        # position=player.position      # From your Player model
                    )
                    created = True
                else:
                    created = False

                # Populate all the stat fields from `stats` dict into `db_projection`
                # Example for a few fields:
                db_projection.rec = stats.get('rec')
                db_projection.rec_yd = stats.get('rec_yd')
                db_projection.rec_td = stats.get('rec_td')
                # ... (add all other stat fields from your SleeperProjection model) ...
                db_projection.pass_yd = stats.get('pass_yd')
                db_projection.pass_td = stats.get('pass_td')
                db_projection.pass_int = stats.get('pass_int')
                # ... and so on for all fields in SleeperProjectionBase ...
                db_projection.pts_std = stats.get('pts_std')
                db_projection.pts_ppr = stats.get('pts_ppr')
                db_projection.pts_half_ppr = stats.get('pts_half_ppr')

                # Add any non-stat fields from the projection item if relevant
                # Example: db_projection.source = proj_item.get('company', 'sleeper')

                session.add(db_projection)
                updated_or_created_count += 1
                if created:
                    print(f"  Created projection for {player.player_name}")
                else:
                    print(f"  Updated projection for {player.player_name}")

            if API_CALL_DELAY_SECONDS > 0:
                await asyncio.sleep(API_CALL_DELAY_SECONDS) # Be polite to the API

    try:
        await session.commit()
        print(f"Sleeper projection ingestion successful. Updated/Created: {updated_or_created_count} records.")
    except Exception as e:
        await session.rollback()
        print(f"Error during Sleeper projection database commit: {e}")
        # Consider raising e or returning an error status
        raise

    return {"message": "Sleeper projection ingestion complete.", "projections_processed": updated_or_created_count}