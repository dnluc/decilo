"""Servidor exclusivo de pruebas: app/gateway reales, publicaciones sin IA.

Estos endpoints solo se agregan al importar este módulo desde Playwright;
no forman parte de decilo.app ni del servidor de producción.
"""
from decilo.app import app, registry, gateways, _gateway_for
from decilo.models import CaptionData, Session

for session_id, language in (("integration-en", "en"), ("integration-es", "es")):
    registry.register(Session(id=session_id, title=f"Integración {language}",
        source_language=language, translation_languages=["es"] if language == "en" else [],
        status="live"))


@app.post("/api/_test/{session_id}/publish")
async def publish(session_id: str, body: dict):
    gateway = _gateway_for(session_id)
    if body["type"] == "caption":
        event = gateway.stream.upsert_caption(CaptionData.model_validate(body["data"]))
    else:
        event = gateway.stream.record_status(gateway.stream.session.model_copy(update={"status": body["status"]}))
    gateway.publish_nowait(event)
    return {"seq": gateway.stream.seq}


@app.get("/api/_test/subscribers")
async def subscribers():
    return {key: len(value._subscribers) for key, value in gateways.items()}
