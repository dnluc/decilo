"""Transcripción con faster-whisper, un modelo por idioma de origen.

Decisión de `arquitectura-base`/`mvp-pipeline` design.md: `small` para
inglés (deja presupuesto de latencia a la traducción), `medium` para
español (sin traducción que sumar, mejor con préstamos técnicos).
"""

from __future__ import annotations

from pathlib import Path

from faster_whisper import WhisperModel

MODEL_BY_LANGUAGE = {"en": "small", "es": "medium"}
_models: dict[str, WhisperModel] = {}


def _get_model(language: str) -> WhisperModel:
    size = MODEL_BY_LANGUAGE.get(language, "small")
    model = _models.get(size)
    if model is None:
        model = WhisperModel(size, device="cpu", compute_type="int8")
        _models[size] = model
    return model


def transcribe(audio_path: Path, language: str) -> str:
    """Bloqueante y CPU-bound: correr con `asyncio.to_thread`."""
    model = _get_model(language)
    segments, _info = model.transcribe(str(audio_path), language=language)
    return " ".join(s.text.strip() for s in segments)
