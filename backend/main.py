# backend/main.py
from fastapi import FastAPI, Depends, HTTPException, Path
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager # For newer FastAPI (0.90.0+)
from datetime import datetime
from typing import Optional, List, Any, Dict
import asyncio
import traceback # For more detailed error logging

import httpx

# Assuming db.py and models.py are in the same directory
from db import get_async_session
from services.player_service import fetch_all_sleeper_players, update_players_in_db
from services.ktc_service import run_ktc_data_ingestion
from services.sleeper_yearly_proj_service import run_sleeper_projection_ingestion
from services.clay_projection_service import run_clay_projection_ingestion
from services.fpros_projection_service import run_fpros_projection_ingestion
from services.sleeper_weekly_proj_service import run_sleeper_weekly_projection_ingestion
# --- ADD THIS IMPORT for the new nfl_data_service ---
from services.nfl_data_service import get_player_stats # Ensure this line is present and correct

# --- Configuration for Sleeper API ---
SLEEPER_API_BASE_URL = "https://api.sleeper.app/v1"

# --- Pydantic Models ---
from pydantic import BaseModel, Field

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
    total_rosters: int

class LeagueSettingDetails(BaseModel):
    type: Optional[int] = None
    playoff_week_start: Optional[int] = None

class RosterDetail(BaseModel):
    roster_id: int
    owner_id: Optional[str] = None
    owner_display_name: Optional[str] = None
    players: Optional[List[str]] = Field(default_factory=list)
    wins: Optional[int] = None
    losses: Optional[int] = None
    ties: Optional[int] = None
    fpts: Optional[float] = None

class LeagueDetailsResponse(BaseModel):
    league_id: str
    name: str
    season: str
    status: str
    total_rosters: int
    scoring_settings: Optional[Dict[str, Any]] = None
    roster_positions: Optional[List[str]] = None
    settings: Optional[LeagueSettingDetails] = None
    rosters: List[RosterDetail] = []

# --- Pydantic Models for NFL Player Stats (nfl_data_py) ---

class PlayerSeasonDetailedStats(BaseModel):
    games_played: Optional[int] = Field(None, description="Games played in the season")
    completions: Optional[int] = Field(None, description="Passing completions")
    attempts: Optional[int] = Field(None, alias="passing_attempts", description="Passing attempts")
    passing_yards: Optional[float] = Field(None, description="Passing yards")
    passing_tds: Optional[int] = Field(None, description="Passing touchdowns")
    interceptions: Optional[int] = Field(None, description="Interceptions thrown")
    sacks_taken: Optional[int] = Field(None, description="Sacks taken as a QB")
    passing_first_downs: Optional[int] = Field(None, description="Passing first downs")
    carries: Optional[int] = Field(None, description="Rushing attempts (carries)")
    rushing_yards: Optional[float] = Field(None, description="Rushing yards")
    rushing_tds: Optional[int] = Field(None, description="Rushing touchdowns")
    rushing_fumbles: Optional[int] = Field(None, description="Rushing fumbles")
    rushing_first_downs: Optional[int] = Field(None, description="Rushing first downs")
    receptions: Optional[int] = Field(None, description="Receptions")
    targets: Optional[int] = Field(None, description="Targets")
    receiving_yards: Optional[float] = Field(None, description="Receiving yards")
    receiving_tds: Optional[int] = Field(None, description="Receiving touchdowns")
    receiving_fumbles: Optional[int] = Field(None, description="Receiving fumbles")
    receiving_first_downs: Optional[int] = Field(None, description="Receiving first downs")
    fantasy_points: Optional[float] = Field(None, description="Fantasy points (Standard scoring)")
    fantasy_points_ppr: Optional[float] = Field(None, description="Fantasy points (PPR scoring)")
    passing_air_yards: Optional[float] = Field(None, description="Total passing air yards")
    passing_yards_after_catch: Optional[float] = Field(None, description="Total passing yards after catch for completions")
    passing_epa: Optional[float] = Field(None, description="Passing EPA (Expected Points Added)")
    avg_time_to_throw: Optional[float] = Field(None, description="Average time to throw (NGS - potentially aggregated)")
    avg_completed_air_yards: Optional[float] = Field(None, description="Average completed air yards (NGS - potentially aggregated)")
    rushing_epa: Optional[float] = Field(None, description="Rushing EPA (Expected Points Added)")
    yards_over_expected: Optional[float] = Field(None, alias="rush_yards_over_expected", description="Rushing yards over expected (NGS - potentially aggregated)")
    efficiency: Optional[float] = Field(None, description="Rushing efficiency (NGS - potentially aggregated)")
    receiving_air_yards: Optional[float] = Field(None, description="Total receiving air yards")
    receiving_yards_after_catch: Optional[float] = Field(None, alias="rec_yards_after_catch", description="Total receiving yards after catch")
    target_share: Optional[float] = Field(None, description="Share of team's total targets")
    air_yards_share: Optional[float] = Field(None, description="Share of team's total air yards")
    wopr: Optional[float] = Field(None, description="Weighted Opportunity Rating (WOPR)")
    avg_separation: Optional[float] = Field(None, description="Average separation from nearest defender (NGS - potentially aggregated)")
    avg_cushion: Optional[float] = Field(None, description="Average cushion by defender (NGS - potentially aggregated)")

class PlayerSeason(BaseModel):
    season: int = Field(..., description="Season year (e.g., 2023)")
    player_id_from_source: str = Field(..., description="Player's unique identifier as used in nfl_data_py (e.g., GSIS ID)")
    player_display_name: str = Field(..., description="Player's display name for that season")
    position: Optional[str] = Field(None, description="Player's primary position in that season")
    team_abbr: str = Field(..., description="Player's team abbreviation for that season (e.g., 'KC')")
    stats: PlayerSeasonDetailedStats = Field(..., description="Detailed stats for the season")

class PlayerStats(BaseModel):
    query_player_name: str = Field(..., description="The player name that was searched for")
    matched_player_id: Optional[str] = Field(None, description="The primary unique identifier for the matched player")
    matched_player_display_name: Optional[str] = Field(None, description="The display name of the matched player")
    current_position: Optional[str] = Field(None, description="Player's most recent or primary position")
    stats_by_season: List[PlayerSeason] = Field(default_factory=list, description="A list of player statistics for each season found")
    error_message: Optional[str] = Field(None, description="An error message if the player is not found or data is unavailable")

# --- End Pydantic Models ---

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

origins = [
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Hello World from Fantasy Backend!"}

@app.get("/test-db")
async def test_db_connection(session: AsyncSession = Depends(get_async_session)):
    if session:
        return {"message": "Successfully obtained a database session!"}
    else:
        raise HTTPException(status_code=500, detail="Failed to obtain a database session.")

# --- Admin Data Ingestion Endpoints ---
# ... (Keep all your existing admin endpoints here, I'm omitting them for brevity but they should remain) ...
@app.post("/admin/ingest/players", status_code=200, tags=["Admin - Data Ingestion"])
async def ingest_all_players(session: AsyncSession = Depends(get_async_session)):
    print("Admin endpoint: Starting player data ingestion...")
    sleeper_data = await fetch_all_sleeper_players()
    if not sleeper_data:
        raise HTTPException(status_code=502, detail="Failed to fetch player data from Sleeper API.")
    result = await update_players_in_db(session, sleeper_data)
    print(f"Admin endpoint: Player data ingestion result: {result}")
    return result

@app.post("/admin/ingest/ktc-values", status_code=200, tags=["Admin - Data Ingestion"])
async def ingest_ktc_values_endpoint(session: AsyncSession = Depends(get_async_session)):
    print("Admin endpoint: Starting KTC data ingestion...")
    try:
        await run_ktc_data_ingestion(session)
        return {"message": "KTC data ingestion process initiated and completed."}
    except Exception as e:
        print(f"Error during KTC ingestion endpoint: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to ingest KTC data: {str(e)}")

@app.post("/admin/ingest/sleeper-projections", status_code=200, tags=["Admin - Data Ingestion"])
async def ingest_sleeper_projections_endpoint(
        season: Optional[int] = None,
        session: AsyncSession = Depends(get_async_session)
):
    print("Admin endpoint: Starting Sleeper projection data ingestion...")
    current_season_to_fetch = season if season is not None else datetime.now().year
    try:
        result = await run_sleeper_projection_ingestion(session, current_season_to_fetch)
        return result
    except Exception as e:
        print(f"Error during Sleeper projection ingestion endpoint: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to ingest Sleeper projection data: {str(e)}")

@app.post("/admin/ingest/clay-projections", status_code=200, tags=["Admin - Data Ingestion"])
async def ingest_clay_projections_endpoint(session: AsyncSession = Depends(get_async_session)):
    print("Admin endpoint: Starting Clay projection data ingestion...")
    try:
        result = await run_clay_projection_ingestion(session)
        return result
    except Exception as e:
        print(f"Error during Clay projection ingestion endpoint: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to ingest Clay projection data: {str(e)}")

@app.post("/admin/ingest/fpros-projections", status_code=200, tags=["Admin - Data Ingestion"])
async def ingest_fpros_projections_endpoint(session: AsyncSession = Depends(get_async_session)):
    print("Admin endpoint: Starting FantasyPros projection data ingestion...")
    try:
        result = await run_fpros_projection_ingestion(session)
        return result
    except Exception as e:
        print(f"Error during FantasyPros projection ingestion endpoint: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to ingest FPros projection data: {str(e)}")

@app.post("/admin/ingest/sleeper-weekly-projections", status_code=200, tags=["Admin - Data Ingestion"])
async def ingest_sleeper_weekly_projections_endpoint(
        season: Optional[int] = None,
        week: Optional[int] = None,
        session: AsyncSession = Depends(get_async_session)
):
    target_season = season if season is not None else datetime.now().year
    print(f"Admin endpoint: Starting Sleeper weekly projection data ingestion for season {target_season}" + (f", week {week}" if week else "") + "...")
    try:
        result = await run_sleeper_weekly_projection_ingestion(session, target_season, specific_week=week)
        return result
    except Exception as e:
        print(f"Error during Sleeper weekly projection ingestion endpoint: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to ingest Sleeper weekly projection data: {str(e)}")

# --- Sleeper User/League Info Endpoints ---
# ... (Keep all your existing Sleeper endpoints here, I'm omitting them for brevity) ...
@app.post("/api/v1/sleeper/resolve-user", response_model=SleeperResolvedUserResponse, tags=["Sleeper Integration"])
async def resolve_sleeper_user(data: ResolveUserInput):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{SLEEPER_API_BASE_URL}/user/{data.input_value}")
            response.raise_for_status()
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
            print(f"HTTP error resolving user {data.input_value}: {exc.response.status_code} - {exc.response.text}")
            return SleeperResolvedUserResponse(error=f"Error resolving user from Sleeper API: Status {exc.response.status_code}")
        except httpx.RequestError as exc:
            print(f"Request error resolving user {data.input_value}: {exc}")
            return SleeperResolvedUserResponse(error=f"Failed to connect to Sleeper API: {exc}")
        except Exception as e:
            print(f"Unexpected error resolving user {data.input_value}: {traceback.format_exc()}")
            return SleeperResolvedUserResponse(error=f"An unexpected server error occurred: {str(e)}")

@app.get("/api/v1/sleeper/users/{user_id}/leagues/{year}", response_model=List[SleeperLeagueResponseItem], tags=["Sleeper Integration"])
async def get_sleeper_user_leagues(
        user_id: str = Path(..., description="The Sleeper user ID", example="213581055209246720"),
        year: int = Path(..., description="The NFL season year (e.g., 2023, 2024)", example=2023)
):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{SLEEPER_API_BASE_URL}/user/{user_id}/leagues/nfl/{year}")
            response.raise_for_status()
            leagues_data = response.json()
            if not isinstance(leagues_data, list):
                print(f"Unexpected data format from Sleeper leagues API for user {user_id}, year {year}: {leagues_data}")
                raise HTTPException(status_code=502, detail="Invalid data format received from Sleeper leagues API.")
            return leagues_data
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return [] # No leagues found, return empty list
            print(f"HTTP error fetching leagues for user {user_id}, year {year}: {exc.response.status_code} - {exc.response.text}")
            raise HTTPException(status_code=exc.response.status_code, detail=f"Error from Sleeper API: {exc.response.text}")
        except httpx.RequestError as exc:
            print(f"Request error fetching leagues for user {user_id}, year {year}: {exc}")
            raise HTTPException(status_code=503, detail=f"Failed to connect to Sleeper API: {exc}")
        except Exception as e:
            print(f"Unexpected error fetching leagues for user {user_id}, year {year}: {traceback.format_exc()}")
            raise HTTPException(status_code=500, detail=f"An unexpected server error occurred: {str(e)}")

@app.get("/api/v1/sleeper/league/{league_id}/details", response_model=LeagueDetailsResponse, tags=["Sleeper Integration"])
async def get_sleeper_league_details(
        league_id: str = Path(..., description="The Sleeper league ID")
):
    async with httpx.AsyncClient() as client:
        try:
            league_task = client.get(f"{SLEEPER_API_BASE_URL}/league/{league_id}")
            rosters_task = client.get(f"{SLEEPER_API_BASE_URL}/league/{league_id}/rosters")
            users_task = client.get(f"{SLEEPER_API_BASE_URL}/league/{league_id}/users")
            league_response, rosters_response, users_response = await asyncio.gather(league_task, rosters_task, users_task)
            league_response.raise_for_status()
            rosters_response.raise_for_status()
            users_response.raise_for_status()
            league_data = league_response.json()
            rosters_data = rosters_response.json()
            users_data = users_response.json()
            user_map = {user['user_id']: user.get('display_name', 'Unknown User') for user in users_data if user and 'user_id' in user}
            processed_rosters: List[RosterDetail] = []
            if isinstance(rosters_data, list):
                for r_data in rosters_data:
                    if not r_data or "roster_id" not in r_data: continue
                    owner_id = r_data.get("owner_id")
                    roster_settings = r_data.get("settings", {})
                    fantasy_points_for = roster_settings.get("fpts", 0)
                    fantasy_points_for_decimal = roster_settings.get("fpts_decimal", 0)
                    calculated_fpts = 0.0
                    try:
                        base_fpts = float(fantasy_points_for if fantasy_points_for is not None else 0.0)
                        decimal_fpts_val = float(fantasy_points_for_decimal if fantasy_points_for_decimal is not None else 0.0)
                        calculated_fpts = base_fpts + (decimal_fpts_val / 100.0) if decimal_fpts_val != 0 else base_fpts
                    except (ValueError, TypeError): calculated_fpts = 0.0
                    processed_rosters.append(RosterDetail(roster_id=r_data["roster_id"], owner_id=owner_id, owner_display_name=user_map.get(owner_id) if owner_id else "Team Available / CPU", players=r_data.get("players", []), wins=roster_settings.get("wins"), losses=roster_settings.get("losses"), ties=roster_settings.get("ties"), fpts=calculated_fpts))
            api_league_settings = league_data.get("settings", {})
            processed_league_settings = LeagueSettingDetails(type=api_league_settings.get("type"), playoff_week_start=api_league_settings.get("playoff_week_start"))
            return LeagueDetailsResponse(league_id=league_data["league_id"], name=league_data["name"], season=league_data["season"], status=league_data["status"], total_rosters=league_data["total_rosters"], scoring_settings=league_data.get("scoring_settings"), roster_positions=league_data.get("roster_positions"), settings=processed_league_settings, rosters=processed_rosters)
        except httpx.HTTPStatusError as exc:
            error_detail = f"Error from Sleeper API: {exc.response.status_code} for URL {exc.request.url}. Response: {exc.response.text}"
            print(f"HTTPStatusError in get_sleeper_league_details for league {league_id}: {error_detail}")
            raise HTTPException(status_code=exc.response.status_code, detail=error_detail)
        except httpx.RequestError as exc:
            error_detail = f"Failed to connect to Sleeper API for URL {exc.request.url}: {exc}"
            print(f"RequestError in get_sleeper_league_details for league {league_id}: {error_detail}")
            raise HTTPException(status_code=503, detail=error_detail)
        except Exception as e:
            error_trace = traceback.format_exc()
            error_detail = f"An unexpected server error occurred while fetching details for league {league_id}: {str(e)}"
            print(f"Unexpected error in get_sleeper_league_details for league {league_id}: {error_detail}\nTrace: {error_trace}")
            raise HTTPException(status_code=500, detail=error_detail)

# --- NEW Player Stats Endpoint (using nfl_data_py) ---
@app.get("/api/v1/player-stats/{player_name}", response_model=PlayerStats, tags=["Player Stats (nfl_data_py)"])
async def get_nfl_player_fantasy_stats(
        player_name: str = Path(..., description="Name of the NFL player to search for (e.g., 'Patrick Mahomes')"),
        # db_session: AsyncSession = Depends(get_async_session) # Uncomment if your get_player_stats service needs DB access
):
    print(f"API ENDPOINT: Calling get_player_stats with player_name variable: '{player_name}' (This is a POSITIONAL call)")
    try:
        # ****** THIS IS THE KEY CHANGE: Call get_player_stats POSITIonALLY ******
        player_data_dict = get_player_stats(player_name)

        if player_data_dict.get("error_message") and \
                player_data_dict.get("error_message") != "Player lookup successful, stats fetching not yet implemented in this step." and \
                not player_data_dict.get("stats_by_season"): # More specific error check
            status_code = 404 if "not found" in player_data_dict["error_message"].lower() else 500
            raise HTTPException(status_code=status_code, detail=player_data_dict["error_message"])

        return player_data_dict
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        error_trace = traceback.format_exc()
        error_detail = f"An unexpected server error occurred while fetching stats for player '{player_name}': {str(e)}"
        print(f"Error in get_nfl_player_fantasy_stats for player {player_name}: {error_detail}\nTrace: {error_trace}")
        raise HTTPException(status_code=500, detail=error_detail)

# --- Placeholder for future player routes ---
# (Your existing placeholders remain unchanged)