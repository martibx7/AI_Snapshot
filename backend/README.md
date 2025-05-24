Markdown

# Fantasy Sports Platform - Backend API

This project is the backend API for a comprehensive Fantasy Sports Platform, built with a modern Python stack. It handles:
* Ingestion of player data, values, and projections from various sources (Sleeper, KeepTradeCut, ESPN/Clay, FantasyPros).
* Storage and management of this data in a PostgreSQL database.
* Providing API endpoints for a frontend application.

## Tech Stack

* **Framework:** [FastAPI](https://fastapi.tiangolo.com/)
* **Language:** Python 3.11+
* **Database:** PostgreSQL
* **ORM / Data Validation:** [SQLModel](https://sqlmodel.tiangolo.com/) (combines Pydantic and SQLAlchemy)
* **Database Migrations:** [Alembic](https://alembic.sqlalchemy.org/)
* **HTTP Client (for external APIs):** [httpx](https://www.python-httpx.org/)
* **Web Scraping (HTML Parsing):** [BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/bs4/doc/)
* **PDF Parsing:** [PyPDF2](https://pypdf2.readthedocs.io/)
* **ASGI Server (for running FastAPI):** [Uvicorn](https://www.uvicorn.org/)

## Project Structure
Okay, that's excellent! With all the primary data ingestion services refactored, getting the README updated for clarity and for your brother to get started is a perfect next step.

The draft you have is a great foundation. I'll help clean it up, update it based on our progress, and make it more comprehensive for a new developer joining the project.

Here's an updated version. I'll provide it in a format you can copy and paste directly into a README.md file.

Markdown

# Fantasy Sports Platform - Backend API

This project is the backend API for a comprehensive Fantasy Sports Platform, built with a modern Python stack. It handles:
* Ingestion of player data, values, and projections from various sources (Sleeper, KeepTradeCut, ESPN/Clay, FantasyPros).
* Storage and management of this data in a PostgreSQL database.
* Providing API endpoints for a frontend application.

## Tech Stack

The backend is built with the following technologies, prioritizing modernity, scalability, and developer experience:

* **Core Framework:**
    * **[FastAPI](https://fastapi.tiangolo.com/) (Python):** A modern, high-performance web framework for building APIs with Python.
        * *Rationale:* Chosen for its speed, automatic data validation (via Pydantic), dependency injection, native asynchronous support, and strong Python ecosystem.
* **ASGI Server:**
    * **[Uvicorn](https://www.uvicorn.org/):** A lightning-fast ASGI server, used to run the FastAPI application.
        * *Rationale:* Standard, high-performance choice for FastAPI.
* **Database & Data Layer:**
    * **[PostgreSQL](https://www.postgresql.org/):** The primary relational database system.
        * *Rationale:* Robust, reliable, and feature-rich for structured data like users, leagues, players, and statistics.
    * **[SQLModel](https://sqlmodel.tiangolo.com/):** Python library for interacting with SQL databases, elegantly combining Pydantic and SQLAlchemy.
        * *Rationale:* Defines data models that serve as both Pydantic models for API validation and SQLAlchemy models for database interaction, promoting code reusability and type safety.
    * **[Alembic](https://alembic.sqlalchemy.org/):** A lightweight database migration tool for SQLAlchemy.
        * *Rationale:* Manages and applies changes to the PostgreSQL database schema over time as your models evolve.
* **Caching & In-Memory Store (Planned):**
    * **[Redis](https://redis.io/):** An advanced key-value store.
        * *Rationale (Planned Use):* Intended for caching API responses, potentially managing user sessions, rate limiting, and as a message broker for light background tasks if the need arises.
* **Key Libraries for Data Acquisition & Utilities:**
    * **[Python](https://www.python.org/):** Version 3.11+
    * **[httpx](https://www.python-httpx.org/):** A fully featured asynchronous HTTP client, used for making requests to external sports APIs.
    * **[BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/bs4/doc/):** A library for parsing HTML and XML documents, utilized for web scraping tasks.
    * **[PyPDF2](https://pypdf2.readthedocs.io/):** A library for reading and extracting text from PDF files, used for sources like Clay's projections.
* **Containerization (for Development Environment):**
    * **[Docker](https://www.docker.com/):** Used to run a consistent PostgreSQL database environment locally.

## Project Structure

```text
fantasy-backend/
├── alembic/                      # Alembic migration scripts and environment
│   ├── env.py                    # Alembic runtime configuration
│   ├── script.py.mako            # Migration script template
│   └── versions/                 # Individual migration scripts
├── services/                     # Business logic and data ingestion
│   ├── __init__.py
│   ├── clay_projection_service.py        # ESPN/Clay PDF projections
│   ├── fpros_projection_service.py       # FantasyPros projections
│   ├── ktc_service.py                   # KeepTradeCut values
│   ├── player_service.py               # Sleeper player data
│   ├── sleeper_weekly_proj_service.py  # Sleeper weekly projections
│   ├── sleeper_yearly_proj_service.py  # Sleeper yearly projections
├── utils/                         # Shared utilities
│   ├── __init__.py
│   └── player_utils.py            # Player name normalization
├── .gitignore
├── alembic.ini                   # Alembic config file
├── db.py                         # SQLModel engine and session setup
├── main.py                       # FastAPI app instance, routes, startup logic
├── models.py                     # SQLModel table definitions
├── README.md
├── requirements.txt              # Python dependencies
└── .venv/                        # Python virtual environment (should be in .gitignore)
```

## Getting Started (Setup for a New Developer)

These instructions will guide you through setting up the backend development environment.

### Prerequisites

* Python 3.11 or newer installed.
* [Git](https://git-scm.com/) installed.
* [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running (for PostgreSQL).

### Setup Steps

1.  **Clone the Repository:**
    Open your terminal or command prompt and run:
    ```bash
    git clone <URL_of_your_fantasy-backend_repo>
    cd fantasy-backend
    ```

2.  **Create and Activate Python Virtual Environment:**
    Using a virtual environment is crucial for managing project-specific dependencies.
    ```bash
    python -m venv .venv 
    ```
    Activate the virtual environment:
    * **Windows (PowerShell):**
        ```powershell
        .\.venv\Scripts\Activate.ps1
        ```
      (If you get an execution policy error, you might need to run: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process` first, then try activating again.)
    * **Windows (Command Prompt):**
        ```cmd
        .\.venv\Scripts\activate.bat
        ```
    * **macOS/Linux (Bash/Zsh):**
        ```bash
        source .venv/bin/activate
        ```
    Your terminal prompt should now be prefixed with `(.venv)`.

3.  **Install Dependencies:**
    With the virtual environment active, install the required Python packages from `requirements.txt`:
    ```bash
    pip install -r requirements.txt
    ```
    *(If `requirements.txt` is missing or outdated, the primary developer can generate it from their active virtual environment using: `pip freeze > requirements.txt`)*

4.  **Set Up PostgreSQL Database using Docker:**
    This project uses a PostgreSQL database running in a Docker container for local development.
    * Ensure Docker Desktop is running.
    * Open your terminal and run the following command to start a PostgreSQL container:
        ```bash
        docker run --name fantasy-postgres -e POSTGRES_USER=fant_dev -e POSTGRES_PASSWORD=devgrind -e POSTGRES_DB=fantasydb -p 5432:5432 -d postgres:15 
        ```
      (This uses PostgreSQL version 15. Adjust if needed.)
    * **Verify the container is running:**
        ```bash
        docker ps 
        ```
      You should see `fantasy-postgres` in the list.
    * **To stop the container later:** `docker stop fantasy-postgres`
    * **To start it again if stopped:** `docker start fantasy-postgres`
    * **To view logs:** `docker logs fantasy-postgres`

5.  **Database Connection Configuration:**
    * The database connection URL is configured in `db.py`. For local development against the Docker container, it's set up to use:
        * User: `fant_dev`
        * Password: `devgrind`
        * Database Name: `fantasydb`
        * Host: `localhost`
        * Port: `5432`
    * These values in `db.py` must match the `-e` environment variables used in the `docker run` command.
    * **(Future):** These settings will be moved to environment variables (e.g., using a `.env` file) for better security and configuration management.

6.  **Run Database Migrations (Alembic):**
    Alembic manages changes to the database schema. To create all necessary tables and bring your local database schema up to date:
    * Make sure your virtual environment `(.venv)` is active.
    * Ensure you are in the root `fantasy-backend` directory.
    * Run:
        ```bash
        alembic upgrade head
        ```
    This command applies all migration scripts found in the `alembic/versions/` directory. If this is the first time, it will create all your tables as defined in `models.py` (via the migrations).

7.  **Run the FastAPI Development Server:**
    To start the backend API:
    * Make sure your virtual environment `(.venv)` is active.
    * Ensure you are in the root `fantasy-backend` directory.
    * Run:
        ```bash
        uvicorn main:app --reload
        ```
    * `--reload` enables auto-reloading when you save code changes.
    * The API should now be running, typically at `http://127.0.0.1:8000`.
    * You can access the interactive API documentation (Swagger UI) at `http://127.0.0.1:8000/docs`.
    * Alternative API documentation (ReDoc) is at `http://127.0.0.1:8000/redoc`.

## Development Workflow

### Making Changes to Database Models (`models.py`)

When you add, remove, or modify fields in your SQLModel classes in `models.py`, you need to generate and apply a database migration:

1.  **Modify `models.py`** with your changes.
2.  **Generate a new migration script with Alembic:**
    Open your terminal (with the virtual environment active) and run:
    ```bash
    alembic revision -m "describe_your_model_change_here" --autogenerate
    ```
    Replace `"describe_your_model_change_here"` with a short, descriptive message (e.g., "add_user_email_field", "create_leagues_table").
3.  **Inspect and Edit the Generated Migration Script:**
    * A new file will be created in the `alembic/versions/` directory.
    * **Open this new script and review it carefully.** Alembic's autogenerate is good but not always perfect.
    * **Important for SQLModel:** If your models use specific SQLModel types that Alembic doesn't recognize by default (like `sqlmodel.sql.sqltypes.AutoString`), you might need to add `import sqlmodel` at the top of the generated migration script. Typically, ensuring `target_metadata = SQLModel.metadata` in `alembic/env.py` and importing your models there correctly handles this.
4.  **Apply the Migration to Your Database:**
    ```bash
    alembic upgrade head
    ```
5.  **Commit your changes:** Add and commit `models.py` and the new migration script in `alembic/versions/` to Git.

### Running Data Ingestion Services

The backend provides administrative API endpoints to trigger data ingestion from various sources. You can easily run these using the `/docs` interface:

1.  Navigate to `http://127.0.0.1:8000/docs`.
2.  Find the desired `POST` endpoint under the "admin" tag.
3.  Click "Try it out", then "Execute".

**Available Ingestion Endpoints:**

* `POST /admin/ingest/players`: Fetches and updates core player data from Sleeper.
* `POST /admin/ingest/ktc-values`: Fetches player values from KeepTradeCut.
* `POST /admin/ingest/sleeper-projections`: Fetches yearly player projections from Sleeper. (Note: API also supports `season` parameter)
* `POST /admin/ingest/clay-projections`: Fetches player projections from ESPN/Clay's PDF.
* `POST /admin/ingest/fpros-projections`: Fetches player projections from FantasyPros.
* `POST /admin/ingest/sleeper-weekly-projections`: Fetches weekly player projections from Sleeper. (Note: API also supports `season` and `week` parameters)

Check the console output where `uvicorn` is running to see the progress and logs from these services.

## TODO / Next Steps & Future Enhancements

* **Refine Player Matching:** Continue to monitor and refine player name normalization (`player_utils.py`) and source-specific exception maps to improve match rates for all data sources.
* **Develop Core Application APIs:** Design and implement API endpoints for frontend consumption (e.g., fetching player lists, individual player details with all aggregated data, league information, user team management).
* **User Authentication & Authorization:** Implement a robust authentication system (e.g., JWT-based) to secure endpoints and manage user accounts.
* **Environment Variable Management:** Move sensitive configurations (like database credentials, API keys) to environment variables using a `.env` file and Pydantic's settings management.
* **Comprehensive Error Handling & Logging:** Enhance error handling across services and implement structured logging for better monitoring and debugging.
* **Automated Testing:** Develop unit and integration tests for services, API endpoints, and utilities.
* **Scheduled Data Updates:** Implement a mechanism for automatic, periodic data updates (e.g., using FastAPI's `BackgroundTasks` for simple tasks, or a dedicated task queue like Celery for more complex needs, or OS-level cron/scheduler).
* **Deployment:** Plan and implement deployment to a PaaS like Render (as outlined in the tech stack document), including setting up CI/CD pipelines.

---

