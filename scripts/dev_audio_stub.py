"""Servidor de prueba SOLO para desarrollar el reproductor de audio en el
frontend, sin depender de que el backend real (Codex) tenga el endpoint
de audio-playback listo todavia. No es parte de la aplicacion — no se usa
en produccion ni en la demo final.

Sirve el catalogo real (via el registro normal) y el audio de las dos
sesiones de muestra desde samples/. Uso:

    DECILO_DEMO_SESSIONS=1 uv run uvicorn scripts.dev_audio_stub:app --port 8000
"""

from __future__ import annotations

from pathlib import Path

from fastapi.responses import FileResponse

from decilo.app import app, registry

SAMPLES_DIR = Path(__file__).parent.parent / "samples"
AUDIO_BY_SESSION = {
    "konex-sala-1-charla-1": SAMPLES_DIR / "en_tech_talk.wav",
    "konex-sala-2-charla-1": SAMPLES_DIR / "es_tech_talk.wav",
}


@app.get("/api/v1/sessions/{session_id}/audio")
async def session_audio(session_id: str):
    from fastapi import HTTPException

    try:
        registry.get(session_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="sesión no encontrada") from None
    path = AUDIO_BY_SESSION.get(session_id)
    if path is None or not path.exists():
        raise HTTPException(status_code=404, detail="audio no disponible")
    return FileResponse(path, media_type="audio/wav")
