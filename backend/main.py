# fantasy-backend/main.py
from fastapi import FastAPI, Depends, HTTPException, Path
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager # For newer FastAPI (0.90.0+)
from datetime import datetime
from typing import Optional, List, Any # Added List, Any

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


# --- Placeholder for future player routes ---
# @app.post("/players/", response_model=PlayerRead)
# async def create_player_endpoint(player: PlayerCreate, session: AsyncSession = Depends(get_async_session)):
#     # Logic to create player
#     pass

# @app.get("/players/", response_model=list[PlayerRead])
# async def read_players_endpoint(session: AsyncSession = Depends(get_async_session)):
#     # Logic to read players
#     pass