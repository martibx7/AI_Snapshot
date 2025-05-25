# fantasy-backend/main.py
from fastapi import FastAPI, Depends, HTTPException, Path
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager # For newer FastAPI (0.90.0+)
from datetime import datetime
from typing import Optional, List, Any, Dict # Added List, Any
import asyncio

import httpx # Added for making HTTP requests

# Assuming db.py and models.py are in the same directory
from db import get_async_session
from services.player_service import fetch_all_sleeper_players, update_players_in_db
from services.ktc_service import run_ktc_data_ingestion
from services.sleeper_yearly_proj_service import run_sleeper_projection_ingestion
from services.clay_projection_service import run_clay_projection_ingestion
from services.fpros_projection_service import run_fpros_projection_ingestion
from services.sleeper_weekly_proj_service import run_sleeper_weekly_projection_ingestion

# --- Configuration for Sleeper API ---
SLEEPER_API_BASE_URL = "https://api.sleeper.app/v1"

# --- Pydantic Models for new Sleeper Endpoints ---
from pydantic import BaseModel, Field # BaseModel and Field might already be imported if used elsewhere

class ResolveUserInput(BaseModel):
    input_value: str = Field(..., description="Sleeper username or user ID")

class SleeperResolvedUserResponse(BaseModel):
    user_id: Optional[str] = None
    display_name: Optional[str] = None
    error: Optional[str] = None

class SleeperLeagueResponseItem(BaseModel):
    league_id: str
    name: str
    season: str
    total_rosters: int # Assuming this field comes from Sleeper API, adjust as necessary
    # Add any other fields you expect from the Sleeper league object
    # For example: status, sport, settings, etc.
    # settings: Optional[Any] = None
    # roster_positions: Optional[List[str]] = None
    # scoring_settings: Optional[Dict[str, Any]] = None

# --- New Pydantic Models for Detailed League Info ---
class LeagueSettingDetails(BaseModel):
    type: Optional[int] = None # 0: Redraft, 1: Keeper, 2: Dynasty etc.
    # name: Optional[str] = None # This 'name' field in Sleeper settings is usually for specific settings like "Best Ball", not the league name itself
    playoff_week_start: Optional[int] = None
    # Add other relevant league settings from league_data.settings as needed
    # e.g., taxi_slots: Optional[int] = None, reserve_slots: Optional[int] = None

class RosterDetail(BaseModel):
    roster_id: int
    owner_id: Optional[str] = None
    owner_display_name: Optional[str] = None
    players: Optional[List[str]] = Field(default_factory=list) # List of player_ids
    wins: Optional[int] = None
    losses: Optional[int] = None
    ties: Optional[int] = None
    fpts: Optional[float] = None # Combined fantasy points for

class LeagueDetailsResponse(BaseModel):
    league_id: str
    name: str
    season: str
    status: str # e.g., "in_season", "pre_season", "complete"
    total_rosters: int
    scoring_settings: Optional[Dict[str, Any]] = None
    roster_positions: Optional[List[str]] = None
    settings: Optional[LeagueSettingDetails] = None # Parsed league settings
    rosters: List[RosterDetail] = []


# Lifespan context manager for startup and shutdown events (recommended for FastAPI 0.90.0+)
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Lifespan event: Startup")
    yield
    print("Lifespan event: Shutdown")

app = FastAPI(
    lifespan=lifespan,
    title="LeagueLegacy Fantasy API",
    description="API for the Fantasy Sports Platform.",
    version="0.1.0"
)

# --- CORS Configuration ---
origins = [
    "http://localhost:3000",  # Your Next.js frontend
    # You can add other origins if needed, e.g., your deployed frontend URL
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Allows specific origins
    allow_credentials=True, # Allows cookies to be included in requests
    allow_methods=["*"],    # Allows all methods (GET, POST, etc.)
    allow_headers=["*"],    # Allows all headers
)
# --- END CORS Configuration ---

@app.get("/")
async def root():
    return {"message": "Hello World from Fantasy Backend!"}

# Example: Route to get a DB session (just for testing the connection for now)
@app.get("/test-db")
async def test_db_connection(session: AsyncSession = Depends(get_async_session)):
    if session:
        return {"message": "Successfully obtained a database session!"}
    else:
        return {"message": "Failed to obtain a database session."}

# --- Admin Data Ingestion Endpoints ---
@app.post("/admin/ingest/players", status_code=200) # Using POST as it changes data
async def ingest_all_players(session: AsyncSession = Depends(get_async_session)):
    """
    Fetches all player data from the Sleeper API and updates the local database.
    """
    print("Admin endpoint: Starting player data ingestion...")
    sleeper_data = await fetch_all_sleeper_players()
    if not sleeper_data:
        raise HTTPException(status_code=502, detail="Failed to fetch player data from Sleeper API.")

    result = await update_players_in_db(session, sleeper_data)
    print(f"Admin endpoint: Player data ingestion result: {result}")
    return result

@app.post("/admin/ingest/ktc-values", status_code=200)
async def ingest_ktc_values_endpoint(session: AsyncSession = Depends(get_async_session)):
    """
    Scrapes KTC data and updates the local ktcvalue table.
    """
    print("Admin endpoint: Starting KTC data ingestion...")
    try:
        await run_ktc_data_ingestion(session)
        return {"message": "KTC data ingestion process initiated and completed."}
    except Exception as e:
        print(f"Error during KTC ingestion endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to ingest KTC data: {str(e)}")

@app.post("/admin/ingest/sleeper-projections", status_code=200)
async def ingest_sleeper_projections_endpoint(
        season: Optional[int] = None,
        session: AsyncSession = Depends(get_async_session)
):
    """
    Fetches Sleeper projection data for active players and updates the database.
    Specify 'season' or it defaults to the current year.
    """
    print("Admin endpoint: Starting Sleeper projection data ingestion...")
    current_season_to_fetch = season if season is not None else datetime.now().year
    try:
        result = await run_sleeper_projection_ingestion(session, current_season_to_fetch)
        return result
    except Exception as e:
        print(f"Error during Sleeper projection ingestion endpoint: {e}")
        # Consider logging the full traceback here
        raise HTTPException(status_code=500, detail=f"Failed to ingest Sleeper projection data: {str(e)}")

@app.post("/admin/ingest/clay-projections", status_code=200)
async def ingest_clay_projections_endpoint(session: AsyncSession = Depends(get_async_session)):
    print("Admin endpoint: Starting Clay projection data ingestion...")
    try:
        result = await run_clay_projection_ingestion(session)
        return result
    except Exception as e:
        print(f"Error during Clay projection ingestion endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to ingest Clay projection data: {str(e)}")

@app.post("/admin/ingest/fpros-projections", status_code=200)
async def ingest_fpros_projections_endpoint(session: AsyncSession = Depends(get_async_session)):
    print("Admin endpoint: Starting FantasyPros projection data ingestion...")
    try:
        result = await run_fpros_projection_ingestion(session)
        return result
    except Exception as e:
        print(f"Error during FantasyPros projection ingestion endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to ingest FPros projection data: {str(e)}")

@app.post("/admin/ingest/sleeper-weekly-projections", status_code=200)
async def ingest_sleeper_weekly_projections_endpoint(
        season: Optional[int] = None,
        week: Optional[int] = None, # Allow specifying a week
        session: AsyncSession = Depends(get_async_session)
):
    target_season = season if season is not None else datetime.now().year
    # If week is None, the service will process all weeks for the season.
    print(f"Admin endpoint: Starting Sleeper weekly projection data ingestion for season {target_season}" + (f", week {week}" if week else "") + "...")
    try:
        result = await run_sleeper_weekly_projection_ingestion(session, target_season, specific_week=week)
        return result
    except Exception as e:
        print(f"Error during Sleeper weekly projection ingestion endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to ingest Sleeper weekly projection data: {str(e)}")


# --- New Sleeper User/League Info Endpoints ---
@app.post("/api/v1/sleeper/resolve-user", response_model=SleeperResolvedUserResponse, tags=["Sleeper"])
async def resolve_sleeper_user(data: ResolveUserInput):
    """
    Resolves a Sleeper username or user ID to get the canonical user_id and display_name.
    Calls the public Sleeper API.
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{SLEEPER_API_BASE_URL}/user/{data.input_value}")
            response.raise_for_status()  # Raises an HTTPError for bad responses (4XX or 5XX)

            sleeper_user_data = response.json()

            if not sleeper_user_data or "user_id" not in sleeper_user_data:
                return SleeperResolvedUserResponse(error="User not found or invalid data from Sleeper")

            return SleeperResolvedUserResponse(
                user_id=sleeper_user_data.get("user_id"),
                display_name=sleeper_user_data.get("display_name", "N/A")
            )
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return SleeperResolvedUserResponse(error=f"Sleeper user '{data.input_value}' not found.")
            # print(f"HTTP error occurred: {exc}") # For logging
            return SleeperResolvedUserResponse(error=f"Error fetching data from Sleeper API: {exc.response.status_code}")
        except httpx.RequestError as exc:
            # print(f"Request error occurred: {exc}") # For logging
            return SleeperResolvedUserResponse(error=f"Failed to connect to Sleeper API: {exc}")
        except Exception as e:
            # print(f"An unexpected error occurred: {e}") # For logging
            return SleeperResolvedUserResponse(error=f"An unexpected server error occurred: {e}")


@app.get("/api/v1/sleeper/users/{user_id}/leagues/{year}", response_model=List[SleeperLeagueResponseItem], tags=["Sleeper"])
async def get_sleeper_user_leagues(
        user_id: str = Path(..., description="The Sleeper user ID", example="213581055209246720"),
        year: int = Path(..., description="The NFL season year (e.g., 2023, 2024)", example=2023)
):
    """
    Fetches all fantasy football leagues for a given Sleeper user for a specific NFL season.
    Calls the public Sleeper API.
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{SLEEPER_API_BASE_URL}/user/{user_id}/leagues/nfl/{year}")
            response.raise_for_status()
            leagues_data = response.json()

            if not isinstance(leagues_data, list):
                print(f"Unexpected data format from Sleeper leagues API for user {user_id}, year {year}: {leagues_data}")
                # Depending on strictness, could raise HTTPException or return empty list
                # For now, let Pydantic try to parse, or it will fail if structure is wrong.
                # If it's an error from Sleeper not in list format, Pydantic will fail validation.
                # If it's a valid non-list JSON error from Sleeper, this might need more specific handling.
                # We expect a list, so if it's not, it's an issue.
                raise HTTPException(status_code=502, detail="Invalid data format received from Sleeper leagues API.")

            # Pydantic will validate each item in the list against SleeperLeagueResponseItem
            return leagues_data
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404: # Sleeper might 404 if user_id is bad, or empty list if user has no leagues
                return []
            print(f"HTTP error fetching leagues: {exc} - Response: {exc.response.text}")
            raise HTTPException(status_code=exc.response.status_code, detail=f"Error from Sleeper API: {exc.response.text}")
        except httpx.RequestError as exc:
            print(f"Request error fetching leagues: {exc}")
            raise HTTPException(status_code=503, detail=f"Failed to connect to Sleeper API: {exc}")
        except Exception as e: # Catch-all for other errors, including JSON decoding if response isn't JSON
            print(f"Unexpected error fetching leagues: {e}")
            raise HTTPException(status_code=500, detail=f"An unexpected server error occurred: {str(e)}")

@app.get("/api/v1/sleeper/league/{league_id}/details", response_model=LeagueDetailsResponse, tags=["Sleeper"])
async def get_sleeper_league_details(
        league_id: str = Path(..., description="The Sleeper league ID")
):
    """
    Fetches detailed information for a specific Sleeper league,
    including basic settings, rosters, and user display names.
    """
    async with httpx.AsyncClient() as client:
        try:
            # Concurrently fetch league data, rosters, and users
            league_task = client.get(f"{SLEEPER_API_BASE_URL}/league/{league_id}")
            rosters_task = client.get(f"{SLEEPER_API_BASE_URL}/league/{league_id}/rosters")
            users_task = client.get(f"{SLEEPER_API_BASE_URL}/league/{league_id}/users")

            league_response, rosters_response, users_response = await asyncio.gather(
                league_task, rosters_task, users_task
            )

            # Check for errors in responses
            league_response.raise_for_status()
            rosters_response.raise_for_status()
            users_response.raise_for_status()

            league_data = league_response.json()
            rosters_data = rosters_response.json() # This is a list of roster objects
            users_data = users_response.json()     # This is a list of user objects for the league

            # Create a mapping for user_id to display_name for efficient lookup
            user_map = {user['user_id']: user.get('display_name', 'Unknown User') for user in users_data if user and 'user_id' in user}

            # Prepare roster details
            processed_rosters: List[RosterDetail] = []
            if isinstance(rosters_data, list): # Ensure rosters_data is a list
                for r_data in rosters_data:
                    if not r_data or "roster_id" not in r_data: # Skip if roster data is malformed
                        continue

                    owner_id = r_data.get("owner_id")
                    roster_settings = r_data.get("settings", {})

                    # Calculate total fantasy points (fpts)
                    # Sleeper provides fpts (integer part) and fpts_decimal (the decimal part as an integer)
                    fantasy_points_for = roster_settings.get("fpts", 0)
                    fantasy_points_for_decimal = roster_settings.get("fpts_decimal", 0)

                    # Safely convert to float and combine
                    calculated_fpts = 0.0
                    try:
                        base_fpts = float(fantasy_points_for) if fantasy_points_for is not None else 0.0
                        decimal_fpts_val = float(fantasy_points_for_decimal) if fantasy_points_for_decimal is not None else 0.0

                        # Determine number of decimal places for fpts_decimal (e.g., if 25 -> 0.25, if 5 -> 0.05)
                        # Assuming it represents raw decimal values, e.g. 25 means 0.25.
                        # A common way Sleeper represents this is fpts_decimal are the digits after decimal.
                        # If fpts_decimal is 25 it's .25. If it's 5 it might mean .05 or .5.
                        # For simplicity and robustness, we'll treat it as hundredths if non-zero.
                        if decimal_fpts_val != 0:
                            # This assumes fpts_decimal are the raw digits, e.g., 25 for .25
                            # A common pattern is `fpts_decimal / (10 ** num_digits_in_fpts_decimal)`
                            # For now, a simple division by 100 if non-zero.
                            # Example: fpts: 100, fpts_decimal: 25 -> 100.25
                            # Example: fpts: 100, fpts_decimal: 5 -> 100.05
                            # Let's assume fpts_decimal should be scaled by 0.01
                            calculated_fpts = base_fpts + (decimal_fpts_val / 100.0)
                        else:
                            calculated_fpts = base_fpts
                    except (ValueError, TypeError):
                        calculated_fpts = 0.0 # Fallback if conversion fails

                    processed_rosters.append(
                        RosterDetail(
                            roster_id=r_data["roster_id"],
                            owner_id=owner_id,
                            owner_display_name=user_map.get(owner_id) if owner_id else "Team Available / CPU",
                            players=r_data.get("players") if r_data.get("players") is not None else [],
                            wins=roster_settings.get("wins"),
                            losses=roster_settings.get("losses"),
                            ties=roster_settings.get("ties"),
                            fpts=calculated_fpts
                        )
                    )

            # Prepare detailed league settings
            api_league_settings = league_data.get("settings", {})
            processed_league_settings = LeagueSettingDetails(
                type=api_league_settings.get("type"),
                playoff_week_start=api_league_settings.get("playoff_week_start")
                # Map other settings from api_league_settings to LeagueSettingDetails as needed
            )

            return LeagueDetailsResponse(
                league_id=league_data["league_id"],
                name=league_data["name"],
                season=league_data["season"],
                status=league_data["status"],
                total_rosters=league_data["total_rosters"],
                scoring_settings=league_data.get("scoring_settings"),
                roster_positions=league_data.get("roster_positions"),
                settings=processed_league_settings,
                rosters=processed_rosters
            )

        except httpx.HTTPStatusError as exc:
            error_detail = f"Error from Sleeper API: {exc.response.status_code} for URL {exc.request.url}. Response: {exc.response.text}"
            print(f"HTTPStatusError in get_sleeper_league_details: {error_detail}")
            raise HTTPException(status_code=exc.response.status_code, detail=error_detail)
        except httpx.RequestError as exc:
            error_detail = f"Failed to connect to Sleeper API for URL {exc.request.url}: {exc}"
            print(f"RequestError in get_sleeper_league_details: {error_detail}")
            raise HTTPException(status_code=503, detail=error_detail)
        except Exception as e:
            # Log the full traceback for unexpected errors
            import traceback
            error_trace = traceback.format_exc()
            error_detail = f"An unexpected server error occurred: {str(e)}"
            print(f"Unexpected error in get_sleeper_league_details: {error_detail}\nTrace: {error_trace}")
            raise HTTPException(status_code=500, detail=error_detail)



# --- Placeholder for future player routes ---
# @app.post("/players/", response_model=PlayerRead)
# async def create_player_endpoint(player: PlayerCreate, session: AsyncSession = Depends(get_async_session)):
#     # Logic to create player
#     pass

# @app.get("/players/", response_model=list[PlayerRead])
# async def read_players_endpoint(session: AsyncSession = Depends(get_async_session)):
#     # Logic to read players
#     pass