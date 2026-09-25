"""Mide latencia real con las dos sesiones de muestra corriendo en simultáneo.

Requiere el servidor corriendo con DECILO_DEMO_SESSIONS=1, arrancado justo
antes de correr este script (para minimizar el desfasaje entre el inicio
del pipeline y la conexión).

Latencia = (hora de llegada del evento - hora de conexión) - (end_ms / 1000)
Es una aproximación: el pipeline puede haber arrancado un poco antes de
que este script se conecte. Sirve para detectar contención real entre las
dos sesiones corriendo a la vez, no como medición de laboratorio exacta.

Uso: uv run scripts/measure_latency.py
"""

import asyncio
import json
import statistics
import time

import websockets

SESSIONS = ["konex-sala-1-charla-1", "konex-sala-2-charla-1"]


async def watch(session_id: str, results: dict) -> None:
    t_connect = time.monotonic()
    uri = f"ws://localhost:8000/api/v1/sessions/{session_id}/events"
    latencies = []
    try:
        async with websockets.connect(uri) as ws:
            while True:
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=90)
                except asyncio.TimeoutError:
                    break
                event = json.loads(raw)
                now = time.monotonic()
                if event["type"] == "caption.upsert":
                    end_ms = event["data"]["end_ms"]
                    latency = (now - t_connect) - (end_ms / 1000)
                    latencies.append((event["data"]["kind"], event["data"]["language"], latency))
                elif event["type"] == "session.status" and event["data"]["session"]["status"] == "ended":
                    break
    except (websockets.exceptions.ConnectionClosed, OSError):
        pass
    results[session_id] = latencies


async def main() -> None:
    results: dict[str, list] = {}
    await asyncio.gather(*(watch(s, results) for s in SESSIONS))

    for session_id, latencies in results.items():
        print(f"\n=== {session_id} ({len(latencies)} eventos) ===")
        by_kind: dict[str, list[float]] = {}
        for kind, lang, lat in latencies:
            by_kind.setdefault(f"{kind}/{lang}", []).append(lat)
        for key, values in by_kind.items():
            values.sort()
            p50 = statistics.median(values)
            p95 = values[min(len(values) - 1, int(len(values) * 0.95))]
            print(f"  {key}: n={len(values)} p50={p50:.2f}s p95={p95:.2f}s max={max(values):.2f}s")


if __name__ == "__main__":
    asyncio.run(main())
