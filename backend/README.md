# Flowdeck backend

FastAPI backend for the frontend's service contract. Workspace state is stored
with SQLAlchemy in a database selected by `DATABASE_URL`. SQLite is the default
and stores data in `backend/flowdeck.db` when the server is run from this
directory.

Install dependencies and run the tests:

```powershell
uv sync
uv run pytest
```

To use another SQLAlchemy-supported database, set `DATABASE_URL` before
starting the server. For example:

```powershell
$env:DATABASE_URL = "sqlite:///./flowdeck-dev.db"
uv run uvicorn backend.main:app --reload --port 8000
```

The application uses a standard SQLAlchemy engine and does not depend on
SQLite-specific queries, so a PostgreSQL URL can be supplied later once its
SQLAlchemy driver is installed.

Run the API locally:

```powershell
uv run uvicorn backend.main:app --reload --port 8000
```

The API is served under `/api/v1`. Interactive documentation is available at
`http://localhost:8000/docs`.
