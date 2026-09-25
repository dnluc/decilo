"""Punto de entrada de la aplicacion Decilo (backend)."""

from fastapi import FastAPI, HTTPException

from decilo.models import Session, SessionCatalog
from decilo.sessions import SessionNotFound, SessionRegistry

app = FastAPI(title="Decilo")
registry = SessionRegistry()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/v1/sessions", response_model=SessionCatalog)
async def list_sessions() -> SessionCatalog:
    return SessionCatalog(sessions=registry.list_sessions())


@app.get("/api/v1/sessions/{session_id}", response_model=Session)
async def get_session(session_id: str) -> Session:
    try:
        return registry.get(session_id).session
    except SessionNotFound:
        raise HTTPException(status_code=404, detail="sesión no encontrada") from None


def main() -> None:
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
