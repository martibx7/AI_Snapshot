# fantasy-backend/services/ktc_service.py
import httpx
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
import asyncio
from datetime import datetime, timezone

from models import Player, KTCValue
from utils.player_utils import normalize_player_name
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, delete
# from sqlalchemy import func # Only if you bring back the count in print statements

# --- KTC Specific Mappings (Overrides after general normalization) ---
KTC_PLAYER_ID_EXCEPTIONS: Dict[str, str] = {
    "Josh Allen": "4984",
    "Kenneth Walker": "8151", # If KTC says "Ken Walker" and it normalizes to "Kenneth Walker"
    "Frank Gore": "11573",
    "Cameron Ward": "11612",
    "Chig Okonkwo": "8210"
    # Add more based on players your normalization misses FOR KTC SPECIFICALLY
}

# --- KTC Scraping Logic ---
KTC_DYNASTY_URL_TEMPLATE = "https://keeptradecut.com/dynasty-rankings?page={page}&filters=QB|WR|RB|TE|RDP&format={format}"
KTC_REDRAFT_URL_TEMPLATE = "https://keeptradecut.com/fantasy-rankings?page={page}&filters=QB|WR|RB|TE&format={format}"

def extract_ktc_data_from_element(player_element: BeautifulSoup, ktc_format_code: int, is_redraft: bool) -> Optional[Dict[str, Any]]:
    """
    Adapted directly from your working KTC_data.py's extract_player_info function.
    ktc_format_code: 1 for 1QB, 0 for Superflex.
    is_redraft: boolean.
    """
    try:
        player_name_element = player_element.find(class_="player-name")
        player_position_element = player_element.find(class_="position") # Rank like QB1
        player_value_element = player_element.find(class_="value")

        # Using your original logic for finding the age/rookie element
        player_age_element = player_element.find(class_="position hidden-xs")

        if not (player_name_element and player_position_element and player_value_element):
            return None

        # Get raw full name text (e.g., "Ja'Marr Chase CIN")
        full_name_from_ktc = player_name_element.get_text(strip=True)
        if not full_name_from_ktc:
            return None

        # Your original team_suffix logic
        team_suffix = (full_name_from_ktc[-3:] if full_name_from_ktc[-3:] == 'RFA'
                       else full_name_from_ktc[-4:] if len(full_name_from_ktc) >=4 and full_name_from_ktc[-4] == 'R' and full_name_from_ktc[-3:].isupper()
        else full_name_from_ktc[-2:] if full_name_from_ktc[-2:] == 'FA'
        else full_name_from_ktc[-3:] if len(full_name_from_ktc) >=3 and full_name_from_ktc[-3:].isupper() and full_name_from_ktc[-3:] not in ["JR.", "SR.", "III", "II", "IV", "V", ".JR", ".SR"]
        else "")

        player_name_cleaned = full_name_from_ktc.replace(team_suffix, "").strip()

        # If stripping the suffix made the name empty (e.g. name was just "CIN"), this is not a valid player name
        if not player_name_cleaned:
            return None

        ktc_position_rank_text = player_position_element.get_text(strip=True)
        ktc_value = int(player_value_element.get_text(strip=True))

        # Your original position extraction
        position = ktc_position_rank_text[:2] if len(ktc_position_rank_text) >= 2 else None

        if position == "RD": # Skip Rookie Draft Picks
            return None
        if position not in ['QB', 'RB', 'WR', 'TE']:
            return None

        age = 0.0 # Default from your script
        if player_age_element:
            player_age_text_content = player_age_element.get_text(strip=True)
            try:
                # Your script takes first 4 chars for age: float(player_age_text[:4])
                age_text_part = player_age_text_content.split('|')[0].strip()
                if age_text_part:
                    age = float(age_text_part[:4])
            except (ValueError, IndexError):
                age = 0.0

        player_team_final = None
        rookie = "No"
        if team_suffix:
            if team_suffix.startswith('R') and len(team_suffix) > 1 and team_suffix[1:].isupper():
                player_team_final = team_suffix[1:]
                rookie = "Yes"
            elif team_suffix.isupper() and team_suffix not in ["FA", "RFA"]:
                player_team_final = team_suffix

        return {
            "raw_player_name": player_name_cleaned, # Name after KTC's suffix removal
            "ktc_position_rank": ktc_position_rank_text,
            "position": position.upper(),
            "team": player_team_final,
            "ktc_value": ktc_value,
            "age": age if age > 0 else None,
            "rookie": rookie,
            "is_redraft": is_redraft,
            "ktc_format_code": ktc_format_code,
        }
    except Exception as e:
        # This is a useful print if an individual element parsing blows up unexpectedly
        # print(f"Error during KTC element parsing: {e}. Element: {str(player_element)[:200]}")
        return None

async def scrape_ktc_pages(client: httpx.AsyncClient, url_template: str, ktc_format_code: int, is_redraft: bool, max_pages: int = 10) -> List[Dict[str, Any]]:
    all_scraped_players = []
    for page_num in range(max_pages):
        url = url_template.format(page=page_num, format=ktc_format_code)
        print(f"Scraping KTC URL: {url}")
        try:
            response = await client.get(url, timeout=20.0)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "html.parser")
            player_elements = soup.find_all(class_="onePlayer")

            if not player_elements and page_num > 0:
                print(f"  No players found on page {page_num + 1}. Stopping for this format.")
                break

            found_on_page = 0
            for element in player_elements:
                player_info = extract_ktc_data_from_element(element, ktc_format_code, is_redraft)
                if player_info:
                    all_scraped_players.append(player_info)
                    found_on_page +=1
            print(f"  Successfully parsed {found_on_page} players on KTC page {page_num + 1}.")
            if found_on_page == 0 and page_num > 0:
                break
            await asyncio.sleep(0.75) # Slightly increased politeness delay
        except httpx.TimeoutException:
            print(f"  Timeout scraping KTC URL {url}.")
        except httpx.RequestError as e:
            print(f"  HTTP error scraping KTC URL {url}: {e}")
        except Exception as e:
            print(f"  General error during KTC scrape of {url}: {e}")
    return all_scraped_players

async def fetch_player_name_id_map_from_db(session: AsyncSession) -> Dict[str, str]:
    player_map: Dict[str, str] = {}
    # Player.player_name from the DB IS the canonical, normalized name.
    stmt = select(Player.player_id, Player.player_name)
    result = await session.execute(stmt)
    db_players_rows = result.all() # result.all() gives Row objects

    for p_row in db_players_rows:
        # Use the already normalized Player.player_name directly as the key
        if p_row.player_name: # Ensure it's not None or an empty string
            player_map[p_row.player_name] = str(p_row.player_id)

    print(f"Built player_name_to_id_map with {len(player_map)} entries. Example key: '{next(iter(player_map)) if player_map else 'N/A'}'") # Debug
    return player_map

async def run_ktc_data_ingestion(session: AsyncSession):
    print("Starting KTC data ingestion service...")
    player_name_to_id_map = await fetch_player_name_id_map_from_db(session)

    all_scraped_entries: List[Dict[str, Any]] = []
    async with httpx.AsyncClient(timeout=httpx.Timeout(20.0, connect=10.0)) as client:
        print("\n--- Scraping Dynasty 1QB ---")
        all_scraped_entries.extend(await scrape_ktc_pages(client, KTC_DYNASTY_URL_TEMPLATE, 1, False))
        print("\n--- Scraping Dynasty Superflex ---")
        all_scraped_entries.extend(await scrape_ktc_pages(client, KTC_DYNASTY_URL_TEMPLATE, 0, False))
        print("\n--- Scraping Redraft 1QB ---")
        all_scraped_entries.extend(await scrape_ktc_pages(client, KTC_REDRAFT_URL_TEMPLATE, 1, True))
        print("\n--- Scraping Redraft Superflex ---")
        all_scraped_entries.extend(await scrape_ktc_pages(client, KTC_REDRAFT_URL_TEMPLATE, 0, True))

    consolidated_player_data: Dict[str, KTCValue] = {}
    skipped_player_messages: List[str] = []
    processed_player_count = 0

    for entry in all_scraped_entries:
        if not entry or not entry.get("raw_player_name"):
            continue

        normalized_ktc_name = normalize_player_name(entry["raw_player_name"])

        if not normalized_ktc_name:
            skipped_player_messages.append(f"Could not normalize KTC raw name: '{entry['raw_player_name']}'")
            continue

        player_id = player_name_to_id_map.get(normalized_ktc_name)
        if not player_id:
            player_id = KTC_PLAYER_ID_EXCEPTIONS.get(normalized_ktc_name)

        if not player_id:
            # Only log actual player names, not draft pick placeholders if any slip through
            if "pick" not in entry["raw_player_name"].lower():
                skipped_player_messages.append(f"ID NOT FOUND: Raw KTC='{entry['raw_player_name']}', Normalized KTC='{normalized_ktc_name}', Pos='{entry.get('position', 'N/A')}', Team='{entry.get('team', 'N/A')}'")
            continue

        processed_player_count +=1
        player_id = str(player_id)

        if player_id not in consolidated_player_data:
            consolidated_player_data[player_id] = KTCValue(player_id=player_id)

        ktc_obj = consolidated_player_data[player_id]

        ktc_obj.player_name = normalized_ktc_name
        ktc_obj.position = entry["position"] if entry["position"] else ktc_obj.position
        ktc_obj.team = entry["team"] if entry["team"] else ktc_obj.team
        ktc_obj.age = entry["age"] if entry["age"] is not None else ktc_obj.age
        ktc_obj.rookie = entry["rookie"] if entry["rookie"] is not None else ktc_obj.rookie
        ktc_obj.ktc_value_updated = datetime.now(timezone.utc).date() # Use timezone.utc

        if entry["is_redraft"]:
            if entry["ktc_format_code"] == 1:
                ktc_obj.ktc_1qb_redraft_value = entry["ktc_value"]
                ktc_obj.ktc_1qb_redraft_position_rank = entry["ktc_position_rank"]
            elif entry["ktc_format_code"] == 0:
                ktc_obj.ktc_sf_redraft_value = entry["ktc_value"]
                ktc_obj.ktc_sf_redraft_position_rank = entry["ktc_position_rank"]
        else:
            if entry["ktc_format_code"] == 1:
                ktc_obj.ktc_1qb_value = entry["ktc_value"]
                ktc_obj.ktc_1qb_position_rank = entry["ktc_position_rank"]
            elif entry["ktc_format_code"] == 0:
                ktc_obj.ktc_sf_value = entry["ktc_value"]
                ktc_obj.ktc_sf_position_rank = entry["ktc_position_rank"]

        # TODO: Populate trend fields from KTCValue model if scraped

    try:
        if consolidated_player_data: # Only proceed if there's data to add/update
            print(f"\nDeleting existing KTC values from database...")
            delete_stmt = delete(KTCValue)
            await session.execute(delete_stmt)

            print(f"Adding {len(consolidated_player_data)} KTC value records to session (Matched KTC Players: {processed_player_count})...")
            for ktc_value_obj in consolidated_player_data.values():
                session.add(ktc_value_obj)

            await session.commit()
            upserted_count = len(consolidated_player_data)
            print(f"KTC data ingestion successful. Upserted {upserted_count} player KTC records.")
        else:
            upserted_count = 0
            print("No KTC data to upsert after processing and matching.")

        if skipped_player_messages:
            print("\n--- KTC Players Not Matched to DB Player IDs (Review and Update Normalization/Exceptions) ---")
            for msg in skipped_player_messages:
                print(msg)

        return {"message": "KTC data ingestion complete.", "players_upserted": upserted_count, "players_skipped_no_id": len(skipped_player_messages)}

    except Exception as e:
        await session.rollback()
        print(f"CRITICAL ERROR during KTC database commit: {e}")
        import traceback
        traceback.print_exc()
        raise