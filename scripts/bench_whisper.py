"""Benchmark de faster-whisper sobre los audios de samples/.

Mide tiempo de transcripcion vs. duracion de audio, y muestra el texto
para comparar a mano contra la referencia. Uso:

    uv run scripts/bench_whisper.py [modelo ...]

Por defecto corre "small" y "medium".
"""

import sys
import time
import wave
from pathlib import Path

from faster_whisper import WhisperModel

SAMPLES = Path(__file__).parent.parent / "samples"
AUDIOS = [
    ("en_tech_talk.wav", "en"),
    ("es_tech_talk.wav", "es"),
]


def audio_duration_seconds(path: Path) -> float:
    with wave.open(str(path), "rb") as f:
        return f.getnframes() / f.getframerate()


def run_model(model_size: str) -> None:
    print(f"\n=== Modelo: {model_size} ===")
    t0 = time.monotonic()
    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    load_s = time.monotonic() - t0
    print(f"Carga del modelo: {load_s:.2f}s")

    for filename, expected_lang in AUDIOS:
        audio_path = SAMPLES / filename
        duration = audio_duration_seconds(audio_path)

        t0 = time.monotonic()
        segments, info = model.transcribe(str(audio_path), language=expected_lang)
        segments = list(segments)
        elapsed = time.monotonic() - t0

        text = " ".join(s.text.strip() for s in segments)
        ratio = elapsed / duration
        print(f"\n--- {filename} (audio: {duration:.1f}s) ---")
        print(f"Idioma detectado/forzado: {expected_lang} (prob={info.language_probability:.2f})")
        print(f"Tiempo de proceso: {elapsed:.2f}s  (proceso/audio = {ratio:.2f}x)")
        print(f"Segmentos: {len(segments)}")
        print(f"Texto: {text}")


if __name__ == "__main__":
    models = sys.argv[1:] or ["small", "medium"]
    for m in models:
        run_model(m)
