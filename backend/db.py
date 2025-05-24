# fantasy-backend/db.py
from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker  # sessionmaker is now part of sqlalchemy.orm

# --- Database URL ---
# IMPORTANT: Use environment variables for credentials in a real application!
# For local development with your Docker container:
POSTGRES_USER = "fant_dev"  # The user you set in the docker run command
POSTGRES_PASSWORD = "devgrind"  # The password you set
POSTGRES_SERVER = "localhost"  # Docker maps port 5432 to localhost
POSTGRES_PORT = "5432"
POSTGRES_DB = "fantasydb"  # The DB name you set

DATABASE_URL = f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_SERVER}:{POSTGRES_PORT}/{POSTGRES_DB}"

# Create the async engine
# echo=True will log SQL statements, useful for debugging, can be turned off for production
async_engine = create_async_engine(DATABASE_URL, echo=False)


async def get_async_session() -> AsyncSession:  # type: ignore # for type hinting with yield
    async_session_maker = sessionmaker(
        bind=async_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session_maker() as session:
        yield session


# Function to create all tables (though Alembic will primarily handle this)
# This can be useful for initial setup or tests if not using Alembic for that part.
async def create_db_and_tables():
    async with async_engine.begin() as conn:
        # await conn.run_sync(SQLModel.metadata.drop_all) # To drop all tables (use with caution)
        await conn.run_sync(SQLModel.metadata.create_all)
