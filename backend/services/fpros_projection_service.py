# services/fpros_projection_service.py
import httpx
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
import asyncio # For potential delays if needed, though not explicitly in old script

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from models import Player, FProsProjection # Ensure FProsProjection is defined in models.py
from utils.player_utils import normalize_player_name

# --- Constants ---
FPROS_URLS = {
    'QB': 'https://www.fantasypros.com/nfl/projections/qb.php?week=draft',
    'RB': 'https://www.fantasypros.com/nfl/projections/rb.php?week=draft',
    'WR': 'https://www.fantasypros.com/nfl/projections/wr.php?week=draft',
    'TE': 'https://www.fantasypros.com/nfl/projections/te.php?week=draft'
}

# For names that are consistently hard to match even after normalization,
# using the output of normalize_player_name(raw_fpros_name) as the key.
FPROS_PLAYER_ID_EXCEPTIONS: Dict[str, str] = {
    # Key: normalize_player_name(RAW_FPROS_NAME) + " " + FPROS_POSITION_FROM_LOG
    "Mike Williams WR": "4068",    # Active Mike Williams
    "Kyle Williams WR": "12547",   # Active Kyle Williams

    # For position mismatches, if you want to link them:
    # Raw FPros Name was 'Justin Shorter', Normalized 'Justin Shorter', FPros Pos 'TE'
    # DB has Justin Shorter (ID 9489) as WR, Active.
    "Justin Shorter TE": "9489",

    # Raw FPros Name was 'Robbie Ouzts', Normalized 'Robbie Ouzts', FPros Pos 'RB'
    # DB has Robbie Ouzts (ID 12656) as TE, Active.
    "Robbie Ouzts RB": "12656",

    # Raw FPros Name was 'Velus Jones Jr.', Normalized 'Velus Jones', FPros Pos 'RB'
    # DB has Velus Jones (ID 8223) as WR, Active.
    "Velus Jones RB": "8223",

    # Raw FPros Name was 'Brady Russell', Normalized 'Brady Russell', FPros Pos 'RB'
    # DB has Brady Russell (ID 11280) as TE, Active.
    "Brady Russell RB": "11280",
}

# --- Helper Functions ---
def clean_number(value_str: Optional[str]) -> Optional[float]:
    """Remove commas and convert to float. Handles None input."""
    if value_str is None:
        return None
    try:
        return float(value_str.replace(',', '').strip())
    except ValueError:
        # print(f"Warning: Could not convert '{value_str}' to float.")
        return None

def _extract_data_from_row(row: BeautifulSoup, position: str) -> Optional[Dict[str, Any]]:
    """Helper to extract projection data from a single table row."""
    cols = row.find_all('td')
    if not cols or len(cols) < 2: # Need at least name/team and one stat
        return None

    player_name_team_cell = cols[0].find('a') # Name is usually in an <a> tag
    if not player_name_team_cell:
        player_name_team_cell = cols[0] # Fallback if no <a> tag

    player_name_team_text = player_name_team_cell.text.strip()

    # Attempt to split name and team (FantasyPros often has "Player Name TEAM")
    # This might need adjustment if team codes are sometimes missing or format varies
    name_parts = player_name_team_text.split()
    raw_player_name = ""
    team_code = None

    if len(name_parts) > 1 and name_parts[-1].isupper() and len(name_parts[-1]) <= 3: # Common team code pattern
        team_code = name_parts[-1]
        raw_player_name = ' '.join(name_parts[:-1])
    else:
        raw_player_name = player_name_team_text # Assume no team code or it's part of name

    if not raw_player_name:
        return None

    data = {
        'raw_player_name': raw_player_name,
        'team': team_code, # This is the team from FPros
        'position': position, # This is the FPros designated position for this table
    }

    try:
        if position == 'QB':
            data.update({
                'pass_attempts': clean_number(cols[1].text), 'completions': clean_number(cols[2].text),
                'pass_yards': clean_number(cols[3].text), 'pass_tds': clean_number(cols[4].text),
                'interceptions': clean_number(cols[5].text), 'rush_attempts': clean_number(cols[6].text),
                'rush_yards': clean_number(cols[7].text), 'rush_tds': clean_number(cols[8].text),
                'fumbles_lost': clean_number(cols[9].text), 'fantasy_points': clean_number(cols[10].text)
            })
        elif position == 'RB':
            data.update({
                'rush_attempts': clean_number(cols[1].text), 'rush_yards': clean_number(cols[2].text),
                'rush_tds': clean_number(cols[3].text), 'receptions': clean_number(cols[4].text),
                'rec_yards': clean_number(cols[5].text), 'rec_tds': clean_number(cols[6].text),
                'fumbles_lost': clean_number(cols[7].text), 'fantasy_points': clean_number(cols[8].text)
            })
        elif position == 'WR':
            data.update({
                'receptions': clean_number(cols[1].text), 'rec_yards': clean_number(cols[2].text),
                'rec_tds': clean_number(cols[3].text), 'rush_attempts': clean_number(cols[4].text),
                'rush_yards': clean_number(cols[5].text), 'rush_tds': clean_number(cols[6].text),
                'fumbles_lost': clean_number(cols[7].text), 'fantasy_points': clean_number(cols[8].text)
            })
        elif position == 'TE':
            data.update({
                'receptions': clean_number(cols[1].text), 'rec_yards': clean_number(cols[2].text),
                'rec_tds': clean_number(cols[3].text), 'fumbles_lost': clean_number(cols[4].text), # Check col index
                'fantasy_points': clean_number(cols[5].text) # Check col index
            })
        return data
    except IndexError:
        # print(f"IndexError parsing row for {raw_player_name}, cols count: {len(cols)}")
        return None
    except Exception as e:
        # print(f"Unexpected error parsing row for {raw_player_name}: {e}")
        return None


async def scrape_fpros_page(client: httpx.AsyncClient, url: str, position: str) -> List[Dict[str, Any]]:
    """Scrapes a single FantasyPros projection page for a given position."""
    print(f"Scraping FantasyPros URL for {position}: {url}")
    scraped_players: List[Dict[str, Any]] = []
    try:
        response = await client.get(url, timeout=20.0)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")

        # FantasyPros table structure might change, this selector needs to be robust
        # The old script used `soup.find('table', {'class': 'table'})`
        # Often, projections are in a table with id="data" or a specific class.
        table = soup.find('table', id='data') # Common ID for their main data table
        if not table:
            table = soup.find('table', class_='table') # Fallback to class

        if not table:
            print(f"  Could not find projection table on page for {position} at {url}")
            return scraped_players

        rows = table.find_all('tr')
        if not rows or len(rows) <=1 : # Check for header row
            print(f"  No data rows found in table for {position} at {url}")
            return scraped_players

        for row in rows[1:]: # Skip header row (usually rows[0])
            player_data = _extract_data_from_row(row, position)
            if player_data:
                scraped_players.append(player_data)

        print(f"  Successfully parsed {len(scraped_players)} players for {position} from page.")
    except httpx.RequestError as e:
        print(f"  HTTP error scraping FantasyPros URL {url}: {e}")
    except Exception as e:
        print(f"  General error during FantasyPros scrape of {url}: {e}")
    return scraped_players


async def get_player_id_for_fpros_player(
        session: AsyncSession,
        raw_fpros_name: str,
        fpros_position: str, # Position from FantasyPros (QB, RB, WR, TE)
        fpros_team: Optional[str]
) -> Optional[str]:
    normalized_name = normalize_player_name(raw_fpros_name)
    if not normalized_name:
        print(f"Could not normalize FPros name: '{raw_fpros_name}' for position {fpros_position}")
        return None

    fpros_position_upper = fpros_position.upper()

    # 1. Check FantasyPros-specific exact match exceptions first
    # These keys should use the name as produced by normalize_player_name() + FPros Position
    exception_key = f"{normalized_name} {fpros_position_upper}"
    if exception_key in FPROS_PLAYER_ID_EXCEPTIONS:
        # print(f"Found player ID via FPROS_PLAYER_ID_EXCEPTIONS for key: '{exception_key}' -> ID: {FPROS_PLAYER_ID_EXCEPTIONS[exception_key]}")
        return FPROS_PLAYER_ID_EXCEPTIONS[exception_key]

    # 2. Primary Lookup: Normalized Name + FPros Position
    # We will fetch all matches first, then filter by active status.
    stmt = select(Player.player_id, Player.status) \
        .where(Player.player_name == normalized_name) \
        .where(Player.position == fpros_position_upper) # Match FPros position against Player.position in DB

    # Optional: Add team for more specificity if FPros team data is reliable & matches your DB team codes
    # if fpros_team:
    #    stmt = stmt.where(Player.team == fpros_team.upper())

    result = await session.execute(stmt)
    all_name_pos_matches = result.all() # List of (player_id, status) tuples

    active_matches_name_pos = [row.player_id for row in all_name_pos_matches if row.status == "Active"]

    if len(active_matches_name_pos) == 1:
        return str(active_matches_name_pos[0])
    elif len(active_matches_name_pos) > 1:
        print(f"AMBIGUITY (Active): Multiple ACTIVE Player IDs ({active_matches_name_pos}) found for FPros: '{raw_fpros_name}' (Normalized: '{normalized_name}', FPros Pos: {fpros_position_upper}, Team: {fpros_team}). Needs FPROS_PLAYER_ID_EXCEPTIONS entry or team matching.")
        return None

        # If no unique active match on name + FPros position, try RB/FB fallback if applicable
    # (Only if there were NO active matches from the primary query)
    if len(active_matches_name_pos) == 0 and fpros_position_upper == 'RB':
        # print(f"Attempting RB/FB fallback for FPros: '{raw_fpros_name}' (Normalized: '{normalized_name}')")
        stmt_fallback = select(Player.player_id, Player.status) \
            .where(Player.player_name == normalized_name) \
            .where(Player.position.in_(['RB', 'FB'])) # type: ignore
        # if fpros_team:
        #     stmt_fallback = stmt_fallback.where(Player.team == fpros_team.upper())

        result_fallback = await session.execute(stmt_fallback)
        all_fallback_matches = result_fallback.all()
        active_fallback_matches = [row.player_id for row in all_fallback_matches if row.status == "Active"]

        if len(active_fallback_matches) == 1:
            return str(active_fallback_matches[0])
        elif len(active_fallback_matches) > 1:
            print(f"AMBIGUITY (RB/FB Fallback - Active): Multiple ACTIVE Player IDs ({active_fallback_matches}) for FPros: '{raw_fpros_name}' (Normalized: '{normalized_name}', RB/FB, Team: {fpros_team}). Needs FPROS_PLAYER_ID_EXCEPTIONS entry.")
            return None

        # If RB/FB fallback also yields no active matches, but there were inactive matches from initial name/pos query:
        if len(all_name_pos_matches) > 0 and len(active_fallback_matches) == 0 : # Check original all_name_pos_matches
            print(f"Player ID found but INACTIVE (or matched different pos in fallback) in DB for FPros: '{raw_fpros_name}' (Normalized: '{normalized_name}', FPros Pos: {fpros_position_upper}, Team: {fpros_team}). Inactive IDs from primary lookup: {[row.player_id for row in all_name_pos_matches if row.status != 'Active']}.")
            return None


    # If no matches at all from primary name/pos query, or only inactive ones and no fallback success
    if len(all_name_pos_matches) == 0 and not (fpros_position_upper == 'RB' and len(active_fallback_matches) > 0): # Ensure we don't double-log "not found" if fallback was tried and failed
        print(f"Player ID not found in DB for FPros: '{raw_fpros_name}' (Normalized: '{normalized_name}', FPros Pos: {fpros_position_upper}, Team: {fpros_team})")
    elif len(active_matches_name_pos) == 0 and (not (fpros_position_upper == 'RB') or len(active_fallback_matches) == 0): # Matched only inactive players and fallback didn't yield active one
        inactive_ids = [row.player_id for row in all_name_pos_matches if row.status != "Active"]
        if inactive_ids: # only print if there were indeed inactive matches
            print(f"Player ID found but INACTIVE in DB for FPros: '{raw_fpros_name}' (Normalized: '{normalized_name}', FPros Pos: {fpros_position_upper}, Team: {fpros_team}). Inactive IDs: {inactive_ids}.")

    return None # Default if no unique active player is identified


async def run_fpros_projection_ingestion(session: AsyncSession):
    print("Starting FantasyPros projection ingestion service...")
    all_scraped_fpros_players: List[Dict[str, Any]] = []

    async with httpx.AsyncClient() as client:
        for position, url in FPROS_URLS.items():
            scraped_data = await scrape_fpros_page(client, url, position)
            all_scraped_fpros_players.extend(scraped_data)
            if scraped_data: # Add a small delay if we successfully scraped
                await asyncio.sleep(0.5) # Be polite

    if not all_scraped_fpros_players:
        print("No players extracted from FantasyPros.")
        return {"message": "No players extracted.", "players_upserted": 0, "players_not_matched": 0}

    print(f"Successfully parsed {len(all_scraped_fpros_players)} raw entries from FantasyPros.")
    upserted_count = 0
    not_matched_count = 0

    # Store player_id and all relevant projection data
    for i, fpros_data in enumerate(all_scraped_fpros_players):
        raw_name = fpros_data.get('raw_player_name','')
        raw_pos = fpros_data.get('position','')
        raw_team = fpros_data.get('team')

        # print(f"[{i+1}/{len(all_scraped_fpros_players)}] Processing FPros player: {raw_name} ({raw_pos}, {raw_team})")

        player_id = await get_player_id_for_fpros_player(session, raw_name, raw_pos, raw_team)

        if not player_id:
            not_matched_count +=1
            continue

        db_fpros_projection = await session.get(FProsProjection, player_id)
        if not db_fpros_projection:
            db_fpros_projection = FProsProjection(player_id=player_id)
            # created = True
        # else:
        # created = False

        # Populate fields from fpros_data into db_fpros_projection
        # This needs to match your FProsProjection model in models.py
        db_fpros_projection.player_name = raw_name # Store FPros's raw name (or normalized if preferred)
        db_fpros_projection.team = fpros_data.get('team')
        db_fpros_projection.position = fpros_data.get('position') # Position from FPros

        # Map all stat fields from fpros_data to db_fpros_projection
        db_fpros_projection.pass_attempts = fpros_data.get('pass_attempts')
        db_fpros_projection.completions = fpros_data.get('completions')
        db_fpros_projection.pass_yards = fpros_data.get('pass_yards')
        db_fpros_projection.pass_tds = fpros_data.get('pass_tds')
        db_fpros_projection.interceptions = fpros_data.get('interceptions')
        db_fpros_projection.rush_attempts = fpros_data.get('rush_attempts')
        db_fpros_projection.rush_yards = fpros_data.get('rush_yards')
        db_fpros_projection.rush_tds = fpros_data.get('rush_tds')
        db_fpros_projection.receptions = fpros_data.get('receptions')
        db_fpros_projection.rec_yards = fpros_data.get('rec_yards')
        db_fpros_projection.rec_tds = fpros_data.get('rec_tds')
        db_fpros_projection.fumbles_lost = fpros_data.get('fumbles_lost')
        db_fpros_projection.fantasy_points = fpros_data.get('fantasy_points')
        # created_at and updated_at will be handled by model defaults

        session.add(db_fpros_projection)
        upserted_count += 1
        # Optional: log created/updated status
        # if created:
        #     print(f"  Created FPros projection for player ID: {player_id} ({raw_name})")
        # else:
        #     print(f"  Updated FPros projection for player ID: {player_id} ({raw_name})")


    try:
        await session.commit()
        print(f"FantasyPros projection ingestion successful. Upserted: {upserted_count} records.")
        if not_matched_count > 0:
            print(f"Could not match Player ID for {not_matched_count} FantasyPros players (see previous logs).")
    except Exception as e:
        await session.rollback()
        print(f"Error during FantasyPros projection database commit: {e}")
        import traceback
        traceback.print_exc() # Print full traceback for DB errors
        raise

    return {
        "message": "FantasyPros projection ingestion complete.",
        "players_upserted": upserted_count,
        "players_not_matched": not_matched_count
    }