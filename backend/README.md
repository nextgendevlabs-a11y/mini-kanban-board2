# Flowdeck backend

FastAPI mock backend for the frontend's service contract. The database is an
in-memory seeded workspace and is intentionally replaceable with a persistent
implementation later.

Install dependencies and run the tests:

```powershell
uv sync
uv run pytest
```

Run the API locally:

```powershell
uv run uvicorn backend.main:app --reload --port 8000
```

The API is served under `/api/v1`. Interactive documentation is available at
`http://localhost:8000/docs`.
