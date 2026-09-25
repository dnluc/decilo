"""Benchmark de traduccion EN->ES con un modelo de texto via Ollama.

Uso:
    uv run scripts/bench_translate.py [modelo]

Traduce el texto de referencia en ingles (samples/en_tech_talk.txt) y mide
tiempo de respuesta. Requiere Ollama corriendo en localhost:11434.
"""

import sys
import time
from pathlib import Path

import httpx

SAMPLES = Path(__file__).parent.parent / "samples"
OLLAMA_URL = "http://localhost:11434/api/chat"

SYSTEM_PROMPT = (
    "Sos un traductor simultaneo de una charla tecnica de una conferencia "
    "de software. Traduci el texto del ingles al espanol de forma natural, "
    "como lo diria un orador en una charla tecnica en Argentina. Mantene "
    "terminos tecnicos de uso habitual en la industria (nombres propios de "
    "herramientas, terminos como 'pull request' o 'commit' si asi se usan "
    "normalmente) en vez de forzar una traduccion literal rara. Responde "
    "SOLO con la traduccion, sin comentarios ni explicaciones."
)


def translate(model: str, text: str) -> tuple[str, float]:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
        "stream": False,
    }
    t0 = time.monotonic()
    resp = httpx.post(OLLAMA_URL, json=payload, timeout=120)
    resp.raise_for_status()
    elapsed = time.monotonic() - t0
    data = resp.json()
    return data["message"]["content"], elapsed


if __name__ == "__main__":
    model = sys.argv[1] if len(sys.argv) > 1 else "gemma3n:e4b"
    en_text = (SAMPLES / "en_tech_talk.txt").read_text().strip()

    print(f"=== Traduccion EN->ES con {model} ===\n")
    print(f"Original (EN):\n{en_text}\n")

    translated, elapsed = translate(model, en_text)
    print(f"Traduccion (ES):\n{translated}\n")
    print(f"Tiempo de respuesta: {elapsed:.2f}s")
