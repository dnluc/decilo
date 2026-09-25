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
import os
import re
import statistics
from functools import partial
from pathlib import Path

from decilo.gateway import SessionGateway
from decilo.models import Session
from decilo.ollama_runtime import ollama_lifespan
from decilo.pipeline import run_file_session
from decilo.segmentation import PauseConfig
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


def caption_summaries(observations):
    """One first/final observation per entry, never weight fast token streams more."""
    first, final = {}, {}
    for item in observations:
        event = item['event']
        if event['type'] != 'caption.upsert':
            continue
        data = event['data']
        key = (data['segment_id'], data['kind'], data['language'])
        first.setdefault(key, item)
        if data['status'] == 'final':
            final[key] = item

    def summarize(entries, anchor):
        groups = {}
        for item in entries.values():
            data = item['event']['data']
            key = f"{data['kind']}/{data['language']}"
            groups.setdefault(key, []).append(item['elapsed_seconds'] - data[anchor] / 1000)
        result = {}
        for key, values in groups.items():
            values.sort()
            result[key] = {'n': len(values), 'p50': statistics.median(values),
                           'p95': values[math.ceil(len(values) * .95) - 1], 'max': max(values)}
        return result
    return {'summary': summarize(final, 'end_ms'),
            'first_summary': summarize(first, 'end_ms'),
            'first_from_start': summarize(first, 'start_ms'),
            'final_from_start': summarize(final, 'start_ms'),
            'unfinished_captions': len(first.keys() - final.keys())}


async def measure(language, keep_all, overlap, segmentation, audio_path=None, timeout=300):
    stream = SessionStream(Session(
        id=f"measure-{language}", title=f"Medición {language}",
        source_language=language, translation_languages=["es"] if language == "en" else [],
        target_locale="es-AR", status="live",
    ))
    started_at = asyncio.get_running_loop().time()
    gateway = MeasuringGateway(stream, started_at)
    stages = []
    await asyncio.wait_for(run_file_session(
        stream, gateway, audio_path or SAMPLES / f"{language}_tech_talk.wav", started_at=started_at, observe=stages.append,
        max_backlog_seconds=None if keep_all else 10.0, overlap_translation=overlap,
        segmentation=PauseConfig() if segmentation == "pause" else None,
    ), timeout=timeout)
    return gateway.observations, stages


async def main(output, languages, warmup, beam_size, keep_all, overlap, segmentation,
               audio_paths=None, references=None, timeout=300):
    async with ollama_lifespan():
        return await _main(output, languages, warmup, beam_size, keep_all, overlap, segmentation,
                           audio_paths or {}, references or {}, timeout)


async def _main(output, languages, warmup, beam_size, keep_all, overlap, segmentation, audio_paths, references, timeout):
    from decilo import pipeline, stt
    pipeline.transcribe = partial(stt.transcribe, beam_size=beam_size)
    if warmup:
        from decilo.pipeline import _iter_chunks
        transcribe = pipeline.transcribe
        from decilo.translate import translate
        for language in languages:
            chunks = _iter_chunks(audio_paths.get(language) or SAMPLES / f"{language}_tech_talk.wav", 5)
            path, _, _ = next(chunks)
            try:
                text = await asyncio.to_thread(transcribe, path, language)
                if language == "en":
                    await translate(text)
            finally:
                path.unlink(missing_ok=True)
                chunks.close()
    measured = await asyncio.gather(*(measure(language, keep_all, overlap, segmentation, audio_paths.get(language), timeout) for language in languages))
    recordings = [item[0] for item in measured]
    report = {"measurement": "audio end to backend publication", "warmup": warmup, "overlap_translation": overlap, "segmentation": segmentation, "beam_size": beam_size, "max_backlog_seconds": None if keep_all else 10.0,
              "source": "provided WAV" if any(audio_paths.values()) else "synthetic WAV",
              "stream_translation": os.environ.get("DECILO_STREAM_TRANSLATION") == "1",
              "audio_paths": {k: str(v) for k, v in audio_paths.items() if v},
              "languages": languages, "sessions": {}}
    for language, (observations, stages) in zip(languages, measured, strict=True):
        summaries = caption_summaries(observations)
        summary = summaries["summary"]
        stage_summary = {}
        for stage in ("backlog", "asr", "translation", "discard", "translation_queue", "translation_backpressure", "translation_first_content"):
            values = [s["seconds"] for s in stages if s["stage"] == stage]
            if values:
                stage_summary[stage] = {"n": len(values), "p50": statistics.median(values),
                                        "max": max(values), "total": sum(values)}
        hypothesis = " ".join(item["event"]["data"]["text"] for item in observations
                              if item["event"]["type"] == "caption.upsert"
                              and item["event"]["data"]["kind"] == "transcript"
                              and item["event"]["data"]["status"] == "final")
        reference = references.get(language)
        if not reference and not audio_paths.get(language):
            reference = SAMPLES / f"{language}_tech_talk.txt"
        quality = word_error_rate(reference.read_text(), hypothesis) if reference else None
        report["sessions"][language] = {**summaries, "transcript_wer": quality, "observations": observations,
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
    parser.add_argument("--overlap-translation", action="store_true")
    parser.add_argument("--segmentation", choices=("fixed", "pause"), default="fixed")
    parser.add_argument('--audio-en', type=Path)
    parser.add_argument('--audio-es', type=Path)
    parser.add_argument('--reference-en', type=Path)
    parser.add_argument('--reference-es', type=Path)
    parser.add_argument('--timeout', type=float, default=300, help='límite por sesión, incluye drain')
    args = parser.parse_args()
    languages = ["en", "es"] if args.sessions == "both" else [args.sessions]
    asyncio.run(main(args.output, languages, args.warmup, args.beam_size, args.keep_all, args.overlap_translation, args.segmentation,
                     {"en": args.audio_en, "es": args.audio_es},
                     {"en": args.reference_en, "es": args.reference_es}, args.timeout))
