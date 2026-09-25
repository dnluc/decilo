"""Mide desde fin de audio hasta publicación del backend, con reloj compartido.

Uso: uv run scripts/measure_latency.py --output /tmp/decilo-latency.json
Inicia uno o dos workers con modelos reales; no requiere un servidor previo.
No mide transporte/renderizado del navegador ni acredita el protocolo de
10 minutos/100 segmentos. Usa WAV sintéticos cortos; --warmup separa la carga inicial.
"""

import argparse
import asyncio
import json
import math
import re
import statistics
from functools import partial
from pathlib import Path

from decilo.gateway import SessionGateway
from decilo.models import Session
from decilo.pipeline import run_file_session
from decilo.stream import SessionStream

SAMPLES = Path(__file__).resolve().parents[1] / "samples"


def word_error_rate(reference, hypothesis):
    """Diagnostic WER: lowercase words, ignore punctuation; not translation quality."""
    expected = re.findall(r"\w+", reference.lower())
    actual = re.findall(r"\w+", hypothesis.lower())
    row = list(range(len(actual) + 1))
    for index, word in enumerate(expected, start=1):
        next_row = [index]
        for column, candidate in enumerate(actual, start=1):
            next_row.append(min(next_row[-1] + 1, row[column] + 1,
                                row[column - 1] + (word != candidate)))
        row = next_row
    return {"errors": row[-1], "reference_words": len(expected),
            "wer": row[-1] / len(expected) if expected else None}


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


async def measure(language, keep_all):
    stream = SessionStream(Session(
        id=f"measure-{language}", title=f"Medición {language}",
        source_language=language, translation_languages=["es"] if language == "en" else [],
        target_locale="es-AR", status="live",
    ))
    started_at = asyncio.get_running_loop().time()
    gateway = MeasuringGateway(stream, started_at)
    stages = []
    await asyncio.wait_for(run_file_session(
        stream, gateway, SAMPLES / f"{language}_tech_talk.wav", started_at=started_at, observe=stages.append,
        max_backlog_seconds=None if keep_all else 10.0,
    ), timeout=300)
    return gateway.observations, stages


async def main(output, languages, warmup, beam_size, keep_all):
    from decilo import pipeline, stt
    pipeline.transcribe = partial(stt.transcribe, beam_size=beam_size)
    if warmup:
        from decilo.pipeline import _iter_chunks
        transcribe = pipeline.transcribe
        from decilo.translate import translate
        for language in languages:
            chunks = _iter_chunks(SAMPLES / f"{language}_tech_talk.wav", 5)
            path, _, _ = next(chunks)
            try:
                text = await asyncio.to_thread(transcribe, path, language)
                if language == "en":
                    await translate(text)
            finally:
                path.unlink(missing_ok=True)
                chunks.close()
    measured = await asyncio.gather(*(measure(language, keep_all) for language in languages))
    recordings = [item[0] for item in measured]
    report = {"measurement": "audio end to backend publication", "warmup": warmup, "beam_size": beam_size, "max_backlog_seconds": None if keep_all else 10.0,
              "source": "synthetic WAV", "languages": languages, "sessions": {}}
    for language, (observations, stages) in zip(languages, measured, strict=True):
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
        stage_summary = {}
        for stage in ("backlog", "asr", "translation", "discard"):
            values = [s["seconds"] for s in stages if s["stage"] == stage]
            if values:
                stage_summary[stage] = {"n": len(values), "p50": statistics.median(values),
                                        "max": max(values), "total": sum(values)}
        hypothesis = " ".join(item["event"]["data"]["text"] for item in observations
                              if item["event"]["type"] == "caption.upsert"
                              and item["event"]["data"]["kind"] == "transcript")
        quality = word_error_rate((SAMPLES / f"{language}_tech_talk.txt").read_text(), hypothesis)
        report["sessions"][language] = {"summary": summary, "transcript_wer": quality, "observations": observations,
                                         "stages": stages, "stage_summary": stage_summary,
                                         "omitted_audio_seconds": sum(s["audio_seconds"] for s in stages
                                                                       if s["stage"] == "discard")}
        print(language, "stages", json.dumps(stage_summary), flush=True)
        print(language, json.dumps(summary), flush=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    errors = [item for observations in recordings for item in observations
              if item["event"]["type"] in {"session.error", "session.gap"}]
    if errors:
        raise SystemExit(f"Medición incompleta: {len(errors)} errores/gaps; ver {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sessions", choices=("en", "es", "both"), default="both")
    parser.add_argument("--warmup", action="store_true")
    parser.add_argument("--keep-all", action="store_true", help="diagnóstico sin descarte por atraso")
    parser.add_argument("--beam-size", type=int, choices=(1, 5), default=5)
    args = parser.parse_args()
    languages = ["en", "es"] if args.sessions == "both" else [args.sessions]
    asyncio.run(main(args.output, languages, args.warmup, args.beam_size, args.keep_all))
