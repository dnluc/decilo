"""Cliente de traducción EN→ES vía Ollama.

Decisión de `mvp-pipeline` design.md: `gemma3n:e2b` (margen de latencia
suficiente para el objetivo de 3s p95 combinado con Whisper `small`).
"""

from __future__ import annotations

import httpx

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "gemma3n:e2b"
SYSTEM_PROMPT = (
    "Sos un traductor simultaneo de una charla tecnica de una conferencia "
    "de software. Traduci el texto del ingles al espanol de forma natural, "
    "como lo diria un orador en una charla tecnica en Argentina. Mantene "
    "terminos tecnicos de uso habitual en la industria en vez de forzar "
    "una traduccion literal rara. Responde SOLO con la traduccion, sin "
    "comentarios ni explicaciones."
)


async def translate(text: str, *, model: str = MODEL, timeout: float = 30.0) -> str:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
        "stream": False,
    }
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(OLLAMA_URL, json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data["message"]["content"].strip()
