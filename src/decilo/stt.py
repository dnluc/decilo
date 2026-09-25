"""Transcripción con faster-whisper, un modelo por idioma de origen.

Decisión de `arquitectura-base`/`mvp-pipeline` design.md: `small` para
inglés (deja presupuesto de latencia a la traducción), `medium` para
español (sin traducción que sumar, mejor con préstamos técnicos).
"""

from __future__ import annotations

from pathlib import Path
from threading import Lock

from decilo.providers import provider

MODEL_BY_LANGUAGE = {"en": "small", "es": "medium"}
_models: dict[str, object] = {}
_model_lock = Lock()
_load_locks: dict[str, Lock] = {}


def WhisperModel(*args, **kwargs):
    from faster_whisper import WhisperModel as Model
    return Model(*args, **kwargs)


def _get_model(language: str):
    size = MODEL_BY_LANGUAGE.get(language, "small")
    # Two simultaneous sessions must not allocate the same cold model twice.
    with _model_lock:
        load_lock = _load_locks.setdefault(size, Lock())
    with load_lock:
        model = _models.get(size)
        if model is None:
            model = WhisperModel(size, device="cpu", compute_type="int8")
            _models[size] = model
        return model


def transcribe(audio_path: Path, language: str, *, beam_size: int = 5) -> str:
    """Bloqueante y CPU-bound: correr con `asyncio.to_thread`."""
    if provider('stt') == 'gemini':
        from decilo.gemini import transcribe as cloud_transcribe
        return cloud_transcribe(audio_path, language)
    model = _get_model(language)
    segments, _info = model.transcribe(str(audio_path), language=language, beam_size=beam_size)
    return " ".join(s.text.strip() for s in segments)
