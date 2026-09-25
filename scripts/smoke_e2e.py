"""Prueba manual de punta a punta contra el servidor real (con modelos).

Requiere que el servidor este corriendo con DECILO_DEMO_SESSIONS=1:

    DECILO_DEMO_SESSIONS=1 uv run uvicorn decilo.app:app --port 8000

Uso: uv run scripts/smoke_e2e.py <session_id> [segundos]
"""

import asyncio
import json
import sys
import time

import httpx
import websockets


async def main() -> None:
    session_id = sys.argv[1] if len(sys.argv) > 1 else "konex-sala-1-charla-1"
    duration = float(sys.argv[2]) if len(sys.argv) > 2 else 30.0

    async with httpx.AsyncClient() as client:
        catalog = (await client.get("http://localhost:8000/api/v1/sessions")).json()
        print("Catalogo:", json.dumps(catalog, indent=2, ensure_ascii=False))

    t0 = time.monotonic()
    uri = f"ws://localhost:8000/api/v1/sessions/{session_id}/events"
    async with websockets.connect(uri) as ws:
        while time.monotonic() - t0 < duration:
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=duration - (time.monotonic() - t0))
            except asyncio.TimeoutError:
                break
            event = json.loads(raw)
            elapsed = time.monotonic() - t0
            if event["type"] == "caption.upsert":
                d = event["data"]
                print(f"[{elapsed:6.2f}s] seq={event['seq']} {d['kind']}/{d['language']} "
                      f"({d['status']}): {d['text']}")
            else:
                print(f"[{elapsed:6.2f}s] seq={event['seq']} {event['type']}: {event['data']}")


if __name__ == "__main__":
    asyncio.run(main())
