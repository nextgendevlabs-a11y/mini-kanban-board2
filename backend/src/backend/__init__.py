from .main import app


def main() -> None:
    import uvicorn

    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)


__all__ = ["app", "main"]
