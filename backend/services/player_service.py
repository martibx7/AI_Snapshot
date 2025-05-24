# fantasy-backend/services/player_service.py
import httpx
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional

from models import Player
from db import get_async_session
from utils.player_utils import normalize_player_name

SLEEPER_PLAYERS_URL = "https://api.sleeper.app/v1/players/nfl"

# Define the set of fantasy-relevant offensive positions
RELEVANT_FANTASY_POSITIONS = {"QB", "RB", "WR", "TE", "FB"}

# Helper function for converting values to int or None
def to_int_or_none(value: Any) -> Optional[int]:
    if value is None or value == '':
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None

async def fetch_all_sleeper_players() -> Optional[Dict[str, Any]]:
    """Fetches all player data from the Sleeper API."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(SLEEPER_PLAYERS_URL)
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as e:
            print(f"An error occurred while requesting Sleeper players: {e}")
            return None
        except httpx.HTTPStatusError as e:
            print(f"Sleeper API returned an error: {e.response.status_code} - {e.response.text}")
            return None
        except Exception as e:
            print(f"A general error occurred fetching Sleeper players: {e}")
            return None

async def update_players_in_db(session: AsyncSession, sleeper_players_data: Dict[str, Any]):
    """
    Updates the 'player' table with Sleeper data, normalizing names and
    only processing players in RELEVANT_FANTASY_POSITIONS.
    """
    if not sleeper_players_data:
        print("No player data from Sleeper to update.")
        return {"message": "No player data received", "updated": 0, "created": 0, "skipped_position": 0}

    updated_count = 0
    created_count = 0
    skipped_position_count = 0

    for sleeper_player_id, details in sleeper_players_data.items():
        try:
            # --- Filter by Position EARLY ---
            current_player_position = details.get('position')
            if current_player_position not in RELEVANT_FANTASY_POSITIONS:
                skipped_position_count += 1
                # If player exists in DB and was relevant, log change. They won't be updated further.
                # If they don't exist, they won't be created.
                # db_player_check = await session.get(Player, sleeper_player_id)
                # if db_player_check and db_player_check.position in RELEVANT_FANTASY_POSITIONS:
                #    print(f"Player {db_player_check.player_name} ({sleeper_player_id}) changed from relevant position {db_player_check.position} to {current_player_position}. Skipping further updates for this player via this service.")
                # elif not db_player_check:
                #    print(f"Skipping non-relevant position player from Sleeper: {details.get('full_name', sleeper_player_id)} ({current_player_position})")
                continue # Skip to the next player
            # --- End Position Filter ---

            # Specific player skips (like Frank Gore Sr.) can remain if needed for other reasons
            if sleeper_player_id == "232": # Example: Skip Frank Gore Sr.
                print(f"Skipping Frank Gore Sr. (Sleeper ID: {sleeper_player_id}) - Explicit skip")
                continue

            db_player = await session.get(Player, sleeper_player_id)

            # Normalize names (this happens only for relevant players now)
            raw_full_name = details.get('full_name')
            player_name_norm = normalize_player_name(raw_full_name)
            raw_first_name = details.get('first_name')
            first_name_norm = normalize_player_name(raw_first_name)
            raw_last_name = details.get('last_name')
            last_name_norm = normalize_player_name(raw_last_name)

            fantasy_positions_list = details.get('fantasy_positions')
            fantasy_position_str = ','.join(fantasy_positions_list) if isinstance(fantasy_positions_list, list) else None
            rotowire_id_raw = details.get('rotowire_id')
            years_exp_raw = details.get('years_exp')
            weight_raw = details.get('weight')
            age_raw = details.get('age')
            rotowire_id_val = str(rotowire_id_raw) if rotowire_id_raw is not None else None
            years_exp_val = to_int_or_none(years_exp_raw)
            weight_val = to_int_or_none(weight_raw)
            age_val = to_int_or_none(age_raw)

            proceed_with_rotowire_update = True
            if rotowire_id_val is not None:
                stmt = select(Player).where(Player.rotowire_id == rotowire_id_val)
                if db_player:
                    stmt = stmt.where(Player.player_id != db_player.player_id)
                result = await session.execute(stmt)
                conflicting_player_db_obj = result.scalar_one_or_none()
                if conflicting_player_db_obj:
                    print(f"Warning: Rotowire ID {rotowire_id_val} for player {player_name_norm} ({sleeper_player_id}) "
                          f"is already assigned to player {conflicting_player_db_obj.player_name} ({conflicting_player_db_obj.player_id}). "
                          f"Skipping rotowire_id update for {player_name_norm}.")
                    proceed_with_rotowire_update = False

            if db_player:
                # Update existing player (who is confirmed to be a relevant position from Sleeper)
                db_player.player_name = player_name_norm if raw_full_name is not None else db_player.player_name
                db_player.first_name = first_name_norm if raw_first_name is not None else db_player.first_name
                db_player.last_name = last_name_norm if raw_last_name is not None else db_player.last_name
                db_player.team = details.get('team', db_player.team)
                db_player.position = current_player_position # Update with current position from Sleeper
                db_player.fantasy_position = fantasy_position_str if fantasy_position_str is not None else db_player.fantasy_position
                if proceed_with_rotowire_update:
                    db_player.rotowire_id = rotowire_id_val
                elif rotowire_id_val is None and db_player.rotowire_id is not None:
                    db_player.rotowire_id = None
                db_player.years_exp = years_exp_val if years_exp_raw is not None else db_player.years_exp
                db_player.weight = weight_val if weight_raw is not None else db_player.weight
                db_player.height = details.get('height', db_player.height)
                db_player.age = age_val if age_raw is not None else db_player.age
                db_player.status = details.get('status', db_player.status if db_player.status else "Inactive")
                updated_count += 1
            else:
                # Create new player (only if they are of a relevant position)
                current_rotowire_id_for_new_player = rotowire_id_val if proceed_with_rotowire_update else None
                db_player = Player(
                    player_id=sleeper_player_id,
                    player_name=player_name_norm,
                    first_name=first_name_norm,
                    last_name=last_name_norm,
                    team=details.get('team'),
                    position=current_player_position, # Store the relevant position
                    fantasy_position=fantasy_position_str,
                    rotowire_id=current_rotowire_id_for_new_player,
                    years_exp=years_exp_val,
                    weight=weight_val,
                    height=details.get('height'),
                    age=age_val,
                    status=details.get('status', "Inactive")
                )
                session.add(db_player)
                created_count += 1
        except Exception as e_player:
            current_player_name_for_log = details.get('full_name', 'Unknown Name')
            print(f"CRITICAL ERROR processing player {sleeper_player_id} ({current_player_name_for_log}): {e_player}")

    try:
        await session.commit()
    except Exception as e_commit:
        await session.rollback()
        print(f"Error during final database commit: {e_commit}")
        raise

    print(f"Player update complete. Updated: {updated_count}, Created: {created_count}, Skipped (non-relevant position): {skipped_position_count}")
    return {
        "message": "Player update complete.",
        "updated_count": updated_count,
        "created_count": created_count,
        "skipped_position_count": skipped_position_count
    }

async def run_player_update_service():
    """
    High-level service function to fetch Sleeper players and update them in the DB.
    """
    print("Starting player update service...")
    sleeper_data = await fetch_all_sleeper_players()
    if sleeper_data:
        session_gen = get_async_session()
        try:
            async with session_gen as session:
                result = await update_players_in_db(session, sleeper_data)
                print(result)
        except Exception as e_update:
            print(f"Error during player DB update service: {e_update}")
    else:
        print("Failed to fetch player data from Sleeper.")
    print("Player update service finished.")

# Optional: To run this script directly for testing
# if __name__ == "__main__":
#     import asyncio
#     asyncio.run(run_player_update_service())