# models.py
from sqlmodel import Field, SQLModel, UniqueConstraint
from typing import Optional
from datetime import datetime, date # For last_updated

class PlayerBase(SQLModel):
    # player_id from Sleeper is a string, so we'll use str here.
    # If it was an auto-incrementing int, we'd use int.
    # We'll make it the primary key in the table model.
    player_name: Optional[str] = Field(default=None, index=True)
    team: Optional[str] = Field(default=None, index=True)
    position: Optional[str] = Field(default=None, index=True)
    fantasy_position: Optional[str] = Field(default=None) # Was VARCHAR, a comma-separated string is fine.
    # If it were stored as a JSON array in PG, different handling.
    rotowire_id: Optional[str] = Field(default=None, unique=True, nullable=True) # Assuming rotowire_id should be unique if present
    years_exp: Optional[int] = Field(default=None)
    weight: Optional[int] = Field(default=None)
    height: Optional[str] = Field(default=None) # e.g., "6-2"
    first_name: Optional[str] = Field(default=None)
    last_name: Optional[str] = Field(default=None, index=True)
    age: Optional[int] = Field(default=None)
    status: Optional[str] = Field(default="Inactive", index=True) # Default to Inactive as per your script

    # Timestamps
    # For created_at (if you want it)
    # created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    last_updated: datetime = Field(default_factory=datetime.utcnow,
                                   sa_column_kwargs={"onupdate": datetime.utcnow},
                                   nullable=False)

class Player(PlayerBase, table=True):
    # player_id from Sleeper is typically a string (e.g., "4984").
    # It makes a good primary key if it's guaranteed unique and always present from your main source (Sleeper).
    # If you prefer an auto-incrementing integer ID internal to your DB,
    # you would add: id: Optional[int] = Field(default=None, primary_key=True)
    # And then player_id_sleeper: str = Field(unique=True, index=True)
    # For now, let's assume the Sleeper player_id IS your primary key.
    player_id: str = Field(primary_key=True, index=True)


# Pydantic models for API input/output (can be expanded later)
class PlayerRead(PlayerBase):
    player_id: str

class PlayerCreate(PlayerBase):
    player_id: str # If you expect client to provide it from Sleeper

class PlayerUpdate(SQLModel):
    player_name: Optional[str] = None
    team: Optional[str] = None
    position: Optional[str] = None
    fantasy_position: Optional[str] = None
    rotowire_id: Optional[str] = None
    years_exp: Optional[int] = None
    weight: Optional[int] = None
    height: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    age: Optional[int] = None
    status: Optional[str] = None

class KTCValueBase(SQLModel):
    player_name: Optional[str] = Field(default=None) # Name from KTC, might differ slightly from official
    ktc_1qb_position_rank: Optional[str] = Field(default=None) # e.g., "QB10"
    position: Optional[str] = Field(default=None, index=True)
    team: Optional[str] = Field(default=None, index=True)
    ktc_1qb_value: Optional[int] = Field(default=None)
    age: Optional[float] = Field(default=None) # KTC sometimes uses decimal ages
    rookie: Optional[str] = Field(default=None) # "Yes" / "No" or similar

    ktc_sf_position_rank: Optional[str] = Field(default=None) # Superflex
    ktc_sf_value: Optional[int] = Field(default=None)

    ktc_1qb_redraft_position_rank: Optional[str] = Field(default=None)
    ktc_1qb_redraft_value: Optional[int] = Field(default=None)

    ktc_sf_redraft_position_rank: Optional[str] = Field(default=None)
    ktc_sf_redraft_value: Optional[int] = Field(default=None)

    # Trend data - your schema has more, I'm simplifying for now, can be expanded
    # ktc_1qb_value_1m: Optional[float] = None
    # ktc_1qb_delta_1m: Optional[float] = None
    # ... many other trend fields ... you can add these if needed

    ktc_value_updated: Optional[date] = Field(default=None) # From your schema

    # Timestamps for your DB record
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow,
                                 sa_column_kwargs={"onupdate": datetime.utcnow},
                                 nullable=False)

class KTCValue(KTCValueBase, table=True):
    # Using an auto-incrementing ID for this table as KTC data might not have its own unique ID per record type,
    # and player_id + format (1QB/SF, Dynasty/Redraft) could be a composite, but simpler to have its own PK.
    # However, your MySQL schema uses player_id as PK for ktc_values. Let's stick to that for consistency.
    # If player_id is from the Sleeper ID string:
    player_id: str = Field(foreign_key="player.player_id", primary_key=True)
    # If player.id was an int, it would be:
    # player_id: int = Field(foreign_key="player.id", primary_key=True)

    # Add a relationship back to Player (optional but useful for ORM features)
    # player: Optional["Player"] = Relationship(back_populates="ktc_values") # Needs "ktc_values" list on Player model

# Pydantic models for API
class KTCValueRead(KTCValueBase):
    player_id: str

class KTCValueCreate(KTCValueBase):
    player_id: str

class SleeperProjectionBase(SQLModel):
    source: Optional[str] = Field(default="sleeper")
    season: int = Field(index=True)
    first_name: Optional[str] = Field(default=None)
    last_name: Optional[str] = Field(default=None)
    team: Optional[str] = Field(default=None, index=True)
    position: Optional[str] = Field(default=None, index=True)

    # Statistical fields from your schema
    rec: Optional[int] = Field(default=None)
    rec_yd: Optional[float] = Field(default=None)
    rec_td: Optional[int] = Field(default=None)
    rec_fd: Optional[float] = Field(default=None)
    rec_0_4: Optional[float] = Field(default=None)
    rec_5_9: Optional[float] = Field(default=None)
    rec_10_19: Optional[float] = Field(default=None)
    rec_20_29: Optional[float] = Field(default=None)
    rec_30_39: Optional[float] = Field(default=None)
    rec_40p: Optional[float] = Field(default=None)
    rush_yd: Optional[float] = Field(default=None)
    rush_td: Optional[int] = Field(default=None)
    rush_fd: Optional[float] = Field(default=None)
    rush_att: Optional[int] = Field(default=None)
    pass_yd: Optional[float] = Field(default=None)
    pass_td: Optional[int] = Field(default=None)
    pass_int: Optional[int] = Field(default=None)
    pass_fd: Optional[float] = Field(default=None)
    pass_cmp: Optional[int] = Field(default=None)
    pass_att: Optional[int] = Field(default=None)
    pass_2pt: Optional[int] = Field(default=None)
    cmp_pct: Optional[float] = Field(default=None)
    pts_std: Optional[float] = Field(default=None)
    pts_ppr: Optional[float] = Field(default=None)
    pts_half_ppr: Optional[float] = Field(default=None)
    gp: Optional[int] = Field(default=None)
    fum_lost: Optional[int] = Field(default=None)
    bonus_rec_wr: Optional[float] = Field(default=None)
    bonus_rec_te: Optional[float] = Field(default=None)
    bonus_rec_rb: Optional[float] = Field(default=None)
    adp_std: Optional[float] = Field(default=None)
    adp_ppr: Optional[float] = Field(default=None)
    adp_half_ppr: Optional[float] = Field(default=None)
    adp_dynasty_std: Optional[float] = Field(default=None)
    adp_dynasty_ppr: Optional[float] = Field(default=None)
    adp_dynasty_half_ppr: Optional[float] = Field(default=None)
    adp_dynasty_2qb: Optional[float] = Field(default=None)
    adp_2qb: Optional[float] = Field(default=None)
    adp_idp: Optional[float] = Field(default=None) # Assuming this is Sleeper's general IDP ADP
    adp_rookie: Optional[float] = Field(default=None)
    adp_dynasty: Optional[float] = Field(default=None) # A more general dynasty ADP

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow,
                                 sa_column_kwargs={"onupdate": datetime.utcnow},
                                 nullable=False)

class SleeperProjection(SleeperProjectionBase, table=True):
    # Your MySQL table uses an auto-incrementing 'id' as PK
    # and a UNIQUE KEY on (player_id, season)
    id: Optional[int] = Field(default=None, primary_key=True)
    player_id: str = Field(foreign_key="player.player_id", index=True)

    # Define the composite unique constraint
    __table_args__ = (UniqueConstraint("player_id", "season", name="uq_sleeper_projection_player_season"),)

# Pydantic models for API (can be expanded later if needed for specific views)
class SleeperProjectionRead(SleeperProjectionBase):
    id: int
    player_id: str

class SleeperProjectionCreate(SleeperProjectionBase):
    player_id: str

class ClayProjectionBase(SQLModel):
    player_name: Optional[str] = Field(default=None)
    team: Optional[str] = Field(default=None, index=True)
    position: Optional[str] = Field(default=None, index=True)
    pos_rank: Optional[int] = Field(default=None)
    ff_points: Optional[int] = Field(default=None) # Fantasy Points
    games: Optional[int] = Field(default=None)

    # Passing stats
    pass_att: Optional[int] = Field(default=None)
    comp: Optional[int] = Field(default=None)     # Completions
    pass_yds: Optional[int] = Field(default=None)
    pass_td: Optional[int] = Field(default=None)
    ints: Optional[int] = Field(default=None)     # Interceptions
    sk: Optional[int] = Field(default=None)       # Sacks taken

    # Rushing stats
    carry: Optional[int] = Field(default=None)
    ru_yds: Optional[int] = Field(default=None)   # Rushing Yards
    ru_tds: Optional[int] = Field(default=None)   # Rushing Touchdowns

    # Receiving stats
    targ: Optional[int] = Field(default=None)     # Targets
    rec: Optional[int] = Field(default=None)      # Receptions
    re_yds: Optional[int] = Field(default=None)   # Receiving Yards
    re_tds: Optional[int] = Field(default=None)   # Receiving Touchdowns

    # Percentage stats
    car_pct: Optional[int] = Field(default=None)  # Carry Percentage
    targ_pct: Optional[int] = Field(default=None) # Target Percentage

    # Timestamps for your DB record
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow,
                                 sa_column_kwargs={"onupdate": datetime.utcnow},
                                 nullable=False)

class ClayProjection(ClayProjectionBase, table=True):
    player_id: str = Field(foreign_key="player.player_id", primary_key=True)
    # Assuming 'player' is the table name for your Player model

# Pydantic models for API (optional for now if these are just for data storage)
class ClayProjectionRead(ClayProjectionBase):
    player_id: str

class ClayProjectionCreate(ClayProjectionBase):
    player_id: str

class FantasyCalcValueBase(SQLModel):
    name: Optional[str] = Field(default=None) # Name from FantasyCalc
    position: Optional[str] = Field(default=None, index=True)

    # Dynasty values
    value_1qb_12team_0ppr: Optional[int] = Field(default=None)
    value_1qb_12team_05ppr: Optional[int] = Field(default=None)
    value_1qb_12team_1ppr: Optional[int] = Field(default=None)
    value_1qb_14team_0ppr: Optional[int] = Field(default=None)
    value_1qb_14team_05ppr: Optional[int] = Field(default=None)
    value_1qb_14team_1ppr: Optional[int] = Field(default=None)
    value_2qb_12team_0ppr: Optional[int] = Field(default=None) # Note: '2qb' is often referred to as Superflex (sf)
    value_2qb_12team_05ppr: Optional[int] = Field(default=None)
    value_2qb_12team_1ppr: Optional[int] = Field(default=None)
    value_2qb_14team_0ppr: Optional[int] = Field(default=None)
    value_2qb_14team_05ppr: Optional[int] = Field(default=None)
    value_2qb_14team_1ppr: Optional[int] = Field(default=None)

    # Redraft values
    redraft_value_1qb_12team_0ppr: Optional[int] = Field(default=None)
    redraft_value_1qb_12team_05ppr: Optional[int] = Field(default=None)
    redraft_value_1qb_12team_1ppr: Optional[int] = Field(default=None)
    redraft_value_1qb_14team_0ppr: Optional[int] = Field(default=None)
    redraft_value_1qb_14team_05ppr: Optional[int] = Field(default=None)
    redraft_value_1qb_14team_1ppr: Optional[int] = Field(default=None)
    redraft_value_2qb_12team_0ppr: Optional[int] = Field(default=None)
    redraft_value_2qb_12team_05ppr: Optional[int] = Field(default=None)
    redraft_value_2qb_12team_1ppr: Optional[int] = Field(default=None)
    redraft_value_2qb_14team_0ppr: Optional[int] = Field(default=None)
    redraft_value_2qb_14team_05ppr: Optional[int] = Field(default=None)
    redraft_value_2qb_14team_1ppr: Optional[int] = Field(default=None)

    # Ranks and trends
    overall_rank: Optional[int] = Field(default=None)
    position_rank: Optional[int] = Field(default=None)
    trend_30_day: Optional[int] = Field(default=None) # Assuming this is a value change, not a percentage
    redraft_dynasty_value_difference: Optional[int] = Field(default=None)
    redraft_dynasty_value_perc_difference: Optional[float] = Field(default=None) # Changed to float for percentage
    combined_value: Optional[int] = Field(default=None)

    # Standard deviation fields
    maybe_moving_standard_deviation: Optional[int] = Field(default=None)
    maybe_moving_standard_deviation_perc: Optional[float] = Field(default=None)
    maybe_moving_standard_deviation_adjusted: Optional[int] = Field(default=None)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow,
                                 sa_column_kwargs={"onupdate": datetime.utcnow},
                                 nullable=False)

class FantasyCalcValue(FantasyCalcValueBase, table=True):
    player_id: str = Field(foreign_key="player.player_id", primary_key=True)

# Pydantic models for API
class FantasyCalcValueRead(FantasyCalcValueBase):
    player_id: str

class FantasyCalcValueCreate(FantasyCalcValueBase):
    player_id: str

class FProsProjectionBase(SQLModel):
    player_name: Optional[str] = Field(default=None) # Name from FantasyPros
    team: Optional[str] = Field(default=None, index=True)
    position: Optional[str] = Field(default=None, index=True)

    # Passing stats
    pass_attempts: Optional[float] = Field(default=None)
    completions: Optional[float] = Field(default=None)
    pass_yards: Optional[float] = Field(default=None)
    pass_tds: Optional[float] = Field(default=None)
    interceptions: Optional[float] = Field(default=None)

    # Rushing stats
    rush_attempts: Optional[float] = Field(default=None)
    rush_yards: Optional[float] = Field(default=None)
    rush_tds: Optional[float] = Field(default=None)

    # Receiving stats
    receptions: Optional[float] = Field(default=None)
    rec_yards: Optional[float] = Field(default=None)
    rec_tds: Optional[float] = Field(default=None)

    # Other stats
    fumbles_lost: Optional[float] = Field(default=None)
    fantasy_points: Optional[float] = Field(default=None) # The specific fantasy points calculated by FPros

    # Timestamps for your DB record
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow,
                                 sa_column_kwargs={"onupdate": datetime.utcnow},
                                 nullable=False)

class FProsProjection(FProsProjectionBase, table=True):
    player_id: str = Field(foreign_key="player.player_id", primary_key=True)

# Pydantic models for API
class FProsProjectionRead(FProsProjectionBase):
    player_id: str

class FProsProjectionCreate(FProsProjectionBase):
    player_id: str

class WeeklyProjectionBase(SQLModel):
    week: int = Field(index=True)
    season: int = Field(index=True)
    opponent: Optional[str] = Field(default=None)
    team: Optional[str] = Field(default=None, index=True)
    company: Optional[str] = Field(default=None) # Source of the projection
    game_id: Optional[str] = Field(default=None, index=True)
    projection_date: Optional[date] = Field(default=None) # Renamed from 'date' to be more descriptive
    # and avoid conflict with Python's date type if used directly as a variable name

    # Statistical fields
    rush_yd: Optional[float] = Field(default=None)
    rush_fd: Optional[float] = Field(default=None)
    rush_att: Optional[float] = Field(default=None)
    rec_yd: Optional[float] = Field(default=None)
    rec_tgt: Optional[float] = Field(default=None)
    rec_td_40p: Optional[float] = Field(default=None) # Reception TD 40+ yards
    rec_td: Optional[float] = Field(default=None)
    rec_fd: Optional[float] = Field(default=None)
    rec_5_9: Optional[float] = Field(default=None)   # Receptions for 5-9 yards
    rec_40p: Optional[float] = Field(default=None)   # Receptions for 40+ yards
    rec_30_39: Optional[float] = Field(default=None)
    rec_20_29: Optional[float] = Field(default=None)
    rec_10_19: Optional[float] = Field(default=None)
    rec_0_4: Optional[float] = Field(default=None)
    rec: Optional[float] = Field(default=None)
    pts_std: Optional[float] = Field(default=None)
    pts_ppr: Optional[float] = Field(default=None)
    pts_half_ppr: Optional[float] = Field(default=None)
    pos_adp_dd_ppr: Optional[int] = Field(default=None)
    gp: Optional[int] = Field(default=None)
    fum_lost: Optional[float] = Field(default=None)
    fum: Optional[float] = Field(default=None)
    bonus_rec_wr: Optional[float] = Field(default=None)
    adp_dd_ppr: Optional[int] = Field(default=None)

    # Timestamps for your DB record
    # MySQL's 'updated_at' bigint(20) was likely a Unix timestamp.
    # We'll use standard datetime for consistency in our new DB.
    # If you need to store the original bigint, add another field.
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at_db: datetime = Field(default_factory=datetime.utcnow,  # Renamed to avoid conflict if 'updated_at' comes from source
                                    sa_column_kwargs={"onupdate": datetime.utcnow},
                                    nullable=False)

class WeeklyProjection(WeeklyProjectionBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    player_id: str = Field(foreign_key="player.player_id", index=True)

    # Define the composite unique constraint
    __table_args__ = (UniqueConstraint("player_id", "week", "season", name="uq_weekly_projection_player_week_season"),)

# Pydantic models for API
class WeeklyProjectionRead(WeeklyProjectionBase):
    id: int
    player_id: str

class WeeklyProjectionCreate(WeeklyProjectionBase):
    player_id: str
