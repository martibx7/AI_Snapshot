# services/clay_projection_service.py
import httpx
import asyncio
from PyPDF2 import PdfReader
import re
from typing import List, Dict, Any, Optional
from io import BytesIO # To process PDF in memory

from sqlalchemy import or_ # Import or_ for OR conditions in SQLAlchemy
from sqlalchemy.exc import MultipleResultsFound, NoResultFound # For better error handling
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from models import Player, ClayProjection # Make sure ClayProjection is in models.py
from utils.player_utils import normalize_player_name

# --- Constants (from your old script or new decisions) ---
CLAY_PDF_URL = 'https://g.espncdn.com/s/ffldraftkit/25/NFLDK2025_CS_ClayProjections2025.pdf' # Or make this configurable
# Define patterns and page ranges as in your old script
PATTERNS = {
    'QB': r'([A-Za-z.\' -]+) (\w+) (\d+) (\d+) (\d+) (\d+) (\d+) (\d+) (\d+) (\d+) (\d+) (\d+) (\d+) (\d+)',
    'RB': r'([A-Za-z.\' -]+) (\w+) (\d+) (\d+) (\d+) (\d+) (\d+) (\d+) (\d+) (\d+) (\d+) (\d+) (\d+)% (\d+)%?',
    'WR': r'([A-Za-z.\' -]+) (\w+) (\d+) (\d+) (\d+) (\d+) (\d+) (\d+) (\d+) (\d+) (\d+) (\d+) (\d+)% (\d+)%?',
    'TE': r'([A-Za-z.\' -]+) (\w+) (\d+) (\d+) (\d+) (\d+) (\d+) (\d+) (\d+) (\d+) (\d+) (\d+) (\d+)% (\d+)?'
}
POSITIONS_PAGES = {
    'QB': (34, 34), # Adjust these page numbers if the PDF changes year to year (0-indexed for PyPDF2)
    'RB': (35, 37),
    'WR': (38, 42),
    'TE': (43, 44)
}

# Clay-specific player ID exceptions (Normalized Name from Clay -> Sleeper Player ID)
# Review and consolidate these with your player_utils.py if possible,
# or keep them here if they are very specific to Clay's naming quirks.
CLAY_PLAYER_ID_EXCEPTIONS: Dict[str, str] = {
    # Example: "NORMALIZED_NAME POS": "sleeper_player_id" (e.g., "JOSH ALLEN QB")
    "JOSH ALLEN QB": "4984",
    "FRANK GORE RB": "11573",
    "KENNETH WALKER RB": "8151",
    "KYLE WILLIAMS WR": "12547",
    # Add C.J. Ham if needed, but the flexible lookup might handle it:
    # "C.J. HAM RB": "3832", # Only if the logic below isn't sufficient for specific cases
}


async def download_pdf_content(client: httpx.AsyncClient, url: str) -> Optional[BytesIO]:
    print(f"Downloading PDF from: {url}")
    try:
        response = await client.get(url, timeout=30.0)
        response.raise_for_status()
        return BytesIO(response.content)
    except httpx.RequestError as e:
        print(f"Error downloading PDF: {e}")
        return None

def parse_projections_from_pdf_text(
        pdf_content: BytesIO,
        position: str,
        start_page_idx: int, # PyPDF2 pages are 0-indexed
        end_page_idx: int,
        pattern: str
) -> List[Dict[str, Any]]:
    """
    Extracts projection data from PDF text content.
    Returns a list of dictionaries.
    """
    extracted_data: List[Dict[str, Any]] = []
    try:
        reader = PdfReader(pdf_content)
        text = ""
        # Ensure page indices are within bounds
        num_pages = len(reader.pages)
        actual_start_page = min(start_page_idx, num_pages -1)
        actual_end_page = min(end_page_idx, num_pages -1)

        for page_num in range(actual_start_page, actual_end_page + 1):
            if page_num < num_pages:
                page = reader.pages[page_num]
                text += page.extract_text() + "\n"
            else:
                print(f"Warning: Page number {page_num + 1} is out of bounds for the PDF.") # +1 for display

        lines = text.split('\n')
        for line_num, line in enumerate(lines): # Added line_num for better error reporting
            line = re.sub(r'\s+', ' ', line).strip() # Normalize whitespace
            match = re.match(pattern, line)
            if match:
                player_data: Dict[str, Any] = {"position": position}
                player_data['player_name_clay'] = match.group(1).strip() # Raw name from Clay
                player_data['team'] = match.group(2)
                try:
                    player_data['pos_rank'] = int(match.group(3))
                    player_data['ff_points'] = int(match.group(4)) # Fantasy Points
                    player_data['games'] = int(match.group(5))

                    if position == 'QB':
                        player_data['pass_att'] = int(match.group(6))
                        player_data['comp'] = int(match.group(7))
                        player_data['pass_yds'] = int(match.group(8))
                        player_data['pass_td'] = int(match.group(9))
                        player_data['ints'] = int(match.group(10))
                        player_data['sk'] = int(match.group(11)) # Sacks taken
                        player_data['carry'] = int(match.group(12))
                        player_data['ru_yds'] = int(match.group(13))
                        player_data['ru_tds'] = int(match.group(14))
                    else: # RB, WR, TE
                        player_data['carry'] = int(match.group(6))
                        player_data['ru_yds'] = int(match.group(7))
                        player_data['ru_tds'] = int(match.group(8))
                        player_data['targ'] = int(match.group(9))
                        player_data['rec'] = int(match.group(10))
                        player_data['re_yds'] = int(match.group(11))
                        player_data['re_tds'] = int(match.group(12))
                        player_data['car_pct'] = float(match.group(13).replace('%', ''))
                        player_data['targ_pct'] = float(match.group(14).replace('%', ''))
                    extracted_data.append(player_data)
                except (IndexError, ValueError) as e:
                    print(f"Skipping line due to parsing error (Index/Value): '{line}' on page {page_num+1}, line {line_num+1}. Error: {e}")
            # else:
            # print(f"Line did not match {position} pattern: {line}") # Can be very verbose
    except Exception as e:
        print(f"Error processing PDF content for {position}: {e}")
    return extracted_data

async def get_player_id_for_clay_player(
        session: AsyncSession,
        clay_player_name: str,
        clay_position: str,
        clay_team: Optional[str] # Optional: use team for disambiguation if needed
) -> Optional[str]:
    """
    Normalizes Clay player name and attempts to find a matching player_id (Sleeper ID).
    This function handles position discrepancies and potential ambiguities.
    """
    normalized_name = normalize_player_name(clay_player_name)
    if not normalized_name:
        print(f"Player ID not found for Clay: '{clay_player_name}' (Normalized: 'N/A', Pos: {clay_position}) - Name normalization failed.")
        return None

    clay_position_upper = clay_position.upper()
    clay_team_upper = clay_team.upper() if clay_team else None

    # 1. Check Clay-specific exact match exceptions (normalized name + position)
    exception_key = f"{normalized_name} {clay_position_upper}"
    if exception_key in CLAY_PLAYER_ID_EXCEPTIONS:
        # print(f"Found player '{normalized_name}' by Clay exception: {CLAY_PLAYER_ID_EXCEPTIONS[exception_key]}") # Keep for debugging exceptions
        return CLAY_PLAYER_ID_EXCEPTIONS[exception_key]

    # --- Primary Lookup Logic (Ordered by specificity/preference) ---

    # Attempt 1: Name + fantasy_position + team (if available)
    stmt = select(Player.player_id).where(
        Player.player_name == normalized_name,
        Player.fantasy_position == clay_position_upper
    )
    if clay_team_upper:
        stmt = stmt.where(Player.team == clay_team_upper)

    try:
        result = await session.execute(stmt)
        player_ids = result.scalars().all()

        if len(player_ids) == 1:
            # print(f"Found player '{normalized_name}' by fantasy_position: {player_ids[0]}") # Remove verbose print
            return str(player_ids[0])
        elif len(player_ids) > 1:
            print(f"Ambiguity: Multiple players found for '{normalized_name}' (fantasy_position: {clay_position_upper}, team: {clay_team_upper}) when matching by fantasy_position. IDs: {player_ids}")
            # Continue to next lookup strategy, hoping for a more specific match or letting it fail if truly ambiguous
            pass

    except Exception as e:
        # print(f"Error during initial player lookup by fantasy_position for '{normalized_name}': {e}") # Debug print
        pass


    # Attempt 2: RB-FB Fallback (if Clay position is RB, try DB's position as FB)
    if clay_position_upper == 'RB':
        stmt_fb_fallback = select(Player.player_id).where(
            Player.player_name == normalized_name,
            Player.position == 'FB'
        )
        if clay_team_upper:
            stmt_fb_fallback = stmt_fb_fallback.where(Player.team == clay_team_upper)

        try:
            result_fb = await session.execute(stmt_fb_fallback)
            player_ids_fb = result_fb.scalars().all()

            if len(player_ids_fb) == 1:
                # print(f"Found player '{normalized_name}' by position fallback (FB): {player_ids_fb[0]}") # Remove verbose print
                return str(player_ids_fb[0])
            elif len(player_ids_fb) > 1:
                print(f"Ambiguity: Multiple players found for '{normalized_name}' (position: FB, team: {clay_team_upper}) during RB-FB fallback. IDs: {player_ids_fb}")
                pass

        except Exception as e:
            # print(f"Error during FB fallback lookup for '{normalized_name}': {e}") # Debug print
            pass


    # Attempt 3 (Last Resort): Name Only
    stmt_name_only = select(Player.player_id).where(Player.player_name == normalized_name)
    try:
        result_name_only = await session.execute(stmt_name_only)
        all_matching_players = result_name_only.scalars().all()

        if len(all_matching_players) == 1:
            # print(f"Found player '{normalized_name}' by name only: {all_matching_players[0]}") # Remove verbose print
            return str(all_matching_players[0])
        elif len(all_matching_players) > 1:
            print(f"Ambiguity: Multiple players found for '{clay_player_name}' (Normalized: '{normalized_name}') when matching by name only. Cannot uniquely identify. IDs: {all_matching_players}")
            return None

    except NoResultFound:
        pass # This means no player was found at all by name.
    except Exception as e:
        # print(f"Error during name-only player lookup for '{normalized_name}': {e}") # Debug print
        pass

    # If all attempts fail
    print(f"Player ID not found for Clay: '{clay_player_name}' (Normalized: '{normalized_name}', Pos: {clay_position})")
    return None

async def run_clay_projection_ingestion(session: AsyncSession):
    print("Starting Clay projection ingestion service...")
    all_parsed_clay_players: List[Dict[str, Any]] = []

    async with httpx.AsyncClient() as client:
        pdf_bytes_io = await download_pdf_content(client, CLAY_PDF_URL)
        if not pdf_bytes_io:
            print("Failed to download Clay PDF. Aborting.")
            return {"message": "Failed to download Clay PDF.", "players_processed": 0}

        for position, (start_page, end_page) in POSITIONS_PAGES.items():
            print(f"Extracting Clay projections for {position} (Pages {start_page+1}-{end_page+1})...")

            parsed_for_pos = parse_projections_from_pdf_text(
                pdf_bytes_io, position, start_page, end_page, PATTERNS[position]
            )
            all_parsed_clay_players.extend(parsed_for_pos)
            pdf_bytes_io.seek(0)

    if not all_parsed_clay_players:
        print("No players extracted from Clay PDF.")
        return {"message": "No players extracted from Clay PDF.", "players_processed": 0}

    print(f"Successfully parsed {len(all_parsed_clay_players)} raw entries from Clay PDF.")
    upserted_count = 0
    not_matched_count = 0

    for i, clay_data in enumerate(all_parsed_clay_players):
        # We can keep this processing print, it's just one line per player
        # print(f"[{i+1}/{len(all_parsed_clay_players)}] Processing Clay player: {clay_data.get('player_name_clay', 'N/A')} ({clay_data.get('position', 'N/A')}, {clay_data.get('team', 'N/A')})")

        player_id = await get_player_id_for_clay_player(
            session,
            clay_data.get('player_name_clay',''),
            clay_data.get('position',''),
            clay_data.get('team')
        )

        if not player_id:
            not_matched_count +=1
            # The "Player ID not found" print is already handled inside get_player_id_for_clay_player
            continue

        db_clay_projection = await session.get(ClayProjection, player_id)
        if not db_clay_projection:
            db_clay_projection = ClayProjection(player_id=player_id)
            created = True
        else:
            created = False

        db_clay_projection.player_name = clay_data.get('player_name_clay')
        db_clay_projection.team = clay_data.get('team')
        db_clay_projection.position = clay_data.get('position')
        db_clay_projection.pos_rank = clay_data.get('pos_rank')
        db_clay_projection.ff_points = clay_data.get('ff_points')
        db_clay_projection.games = clay_data.get('games')
        db_clay_projection.pass_att = clay_data.get('pass_att')
        db_clay_projection.comp = clay_data.get('comp')
        db_clay_projection.pass_yds = clay_data.get('pass_yds')
        db_clay_projection.pass_td = clay_data.get('pass_td')
        db_clay_projection.ints = clay_data.get('ints')
        db_clay_projection.sk = clay_data.get('sk')
        db_clay_projection.carry = clay_data.get('carry')
        db_clay_projection.ru_yds = clay_data.get('ru_yds')
        db_clay_projection.ru_tds = clay_data.get('ru_tds')
        db_clay_projection.targ = clay_data.get('targ')
        db_clay_projection.rec = clay_data.get('rec')
        db_clay_projection.re_tds = clay_data.get('re_tds')
        db_clay_projection.car_pct = clay_data.get('car_pct')
        db_clay_projection.targ_pct = clay_data.get('targ_pct')

        session.add(db_clay_projection)
        upserted_count += 1

    try:
        await session.commit()
        print(f"Clay projection ingestion successful. Upserted: {upserted_count} records.")
        if not_matched_count > 0:
            print(f"Could not match Player ID for {not_matched_count} Clay players.")
    except Exception as e:
        await session.rollback()
        print(f"Error during Clay projection database commit: {e}")
        raise

    return {
        "message": "Clay projection ingestion complete.",
        "players_upserted": upserted_count,
        "players_not_matched": not_matched_count
    }