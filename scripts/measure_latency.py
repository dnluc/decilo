"""Mide desde fin de audio hasta publicación del backend, con reloj compartido.

Uso: uv run scripts/measure_latency.py --output /tmp/decilo-latency.json
Inicia dos workers con modelos reales; no requiere un servidor previo.
No mide transporte/renderizado del navegador ni acredita el protocolo de
10 minutos/100 segmentos. Incluye arranque frío; usa WAV sintéticos cortos.
"""

import argparse
import asyncio
import json
import math
import statistics
from pathlib import Path

from decilo.gateway import SessionGateway
from decilo.models import Session
from decilo.pipeline import run_file_session
from decilo.stream import SessionStream

SAMPLES = Path(__file__).resolve().parents[1] / "samples"


class MeasuringGateway(SessionGateway):
    def __init__(self, stream, started_at):
        super().__init__(stream)
        self.started_at = started_at
        self.observations = []

    def publish_nowait(self, event):
        if event is not None:
            elapsed = asyncio.get_running_loop().time() - self.started_at
            self.observations.append({"elapsed_seconds": elapsed,
                                      "event": event.model_dump(mode="json")})
        super().publish_nowait(event)


async def measure(language):
    stream = SessionStream(Session(
        id=f"measure-{language}", title=f"Medición {language}",
        source_language=language, translation_languages=["es"] if language == "en" else [],
        target_locale="es-AR", status="live",
    ))
    started_at = asyncio.get_running_loop().time()
    gateway = MeasuringGateway(stream, started_at)
    await asyncio.wait_for(run_file_session(
        stream, gateway, SAMPLES / f"{language}_tech_talk.wav", started_at=started_at,
    ), timeout=300)
    return gateway.observations


async def main(output):
    recordings = await asyncio.gather(measure("en"), measure("es"))
    report = {"measurement": "audio end to backend publication; includes cold start",
              "source": "synthetic WAV; two concurrent sessions", "sessions": {}}
    for language, observations in zip(("en", "es"), recordings, strict=True):
        groups = {}
        for item in observations:
            event = item["event"]
            if event["type"] == "caption.upsert":
                data = event["data"]
                key = f"{data['kind']}/{data['language']}"
                delay = item["elapsed_seconds"] - data["end_ms"] / 1000
                groups.setdefault(key, []).append(delay)
        summary = {}
        for key, values in groups.items():
            values.sort()
            summary[key] = {"n": len(values), "p50": statistics.median(values),
                            "p95": values[math.ceil(len(values) * .95) - 1],
                            "max": max(values)}
        report["sessions"][language] = {"summary": summary, "observations": observations}
        print(language, json.dumps(summary), flush=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    errors = [item for observations in recordings for item in observations
              if item["event"]["type"] in {"session.error", "session.gap"}]
    if errors:
        raise SystemExit(f"Medición incompleta: {len(errors)} errores/gaps; ver {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    asyncio.run(main(parser.parse_args().output))
