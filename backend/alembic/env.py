from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import AsyncEngine

from alembic import context
# This line is important! Import your SQLModel base and metadata.
# Assuming your models.py is at the root of your project (fantasy-backend/models.py)
# Adjust the import path if your models.py is elsewhere.
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1])) # Adds project root to Python path
from models import SQLModel # Import SQLModel base from your models file
# OR if you defined a specific Base = SQLModel, import that.
# OR from your_project.models import Base # if your models are in a package

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = SQLModel.metadata # Use the metadata from SQLModel

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = config.attributes.get("connection", None)

    if connectable is None:
        # Using AsyncEngine for our async setup
        connectable = AsyncEngine(
            engine_from_config(
                config.get_section(config.config_ini_section, {}),
                prefix="sqlalchemy.",
                poolclass=pool.NullPool,
                future=True, # Ensure future=True for SQLAlchemy 2.0 style
            )
        )

    if isinstance(connectable, AsyncEngine):
        async def run_async_migrations():
            async with connectable.connect() as connection:
                await connection.run_sync(do_run_migrations)
            await connectable.dispose()

        import asyncio
        asyncio.run(run_async_migrations())
    else: # Fallback for synchronous engine if configured differently
        with connectable.connect() as connection:
            do_run_migrations(connection)

def do_run_migrations(connection):
    context.configure(
        connection=connection,
        target_metadata=target_metadata
    )
    with context.begin_transaction():
        context.run_migrations()

# Existing call to run_migrations_online() at the end of the file
run_migrations_online()