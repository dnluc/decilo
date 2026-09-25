"""Transcripción con faster-whisper, un modelo por idioma de origen.

Decisión de `arquitectura-base`/`mvp-pipeline` design.md: `small` para
inglés (deja presupuesto de latencia a la traducción), `medium` para
español (sin traducción que sumar, mejor con préstamos técnicos).
"""

from __future__ import annotations

from pathlib import Path
from threading import Lock

from faster_whisper import WhisperModel

MODEL_BY_LANGUAGE = {"en": "small", "es": "medium"}
_models: dict[str, WhisperModel] = {}
_model_lock = Lock()
_load_locks: dict[str, Lock] = {}


def _get_model(language: str) -> WhisperModel:
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


# Whisper fue entrenado con subtítulos de YouTube: sobre audio sin habla
# (música, aplausos, ruido de sala) no devuelve vacío, inventa frases de ese
# corpus — "¡SUSCRÍBETE!", muletillas, "Gracias por ver el video". Reproducido
# con un tono y con aplausos sintéticos, ambos daban '¡SUSCRÍBETE!'.
#
# El VAD descarta lo que no es voz antes de transcribir; `no_speech_prob`
# filtra lo que igual se cuele. `condition_on_previous_text=False` evita que
# una alucinación se arrastre y se repita en los segmentos siguientes.
#
# No alcanza con el filtro por energía de `segmentation.py`: su umbral solo
# atrapa silencio digital puro (música da RMS 0.088 y aplausos 0.110, muy por
# encima de 0.01), así que ese audio llega igual a la inferencia.
NO_SPEECH_THRESHOLD = 0.6


def transcribe(audio_path: Path, language: str, *, beam_size: int = 5) -> str:
    """Bloqueante y CPU-bound: correr con `asyncio.to_thread`."""
    model = _get_model(language)
    segments, _info = model.transcribe(
        str(audio_path),
        language=language,
        beam_size=beam_size,
        vad_filter=True,
        condition_on_previous_text=False,
        no_speech_threshold=NO_SPEECH_THRESHOLD,
    )
    return " ".join(
        s.text.strip() for s in segments if s.no_speech_prob < NO_SPEECH_THRESHOLD
    )
