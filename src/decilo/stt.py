"""Transcripción con faster-whisper, un modelo por idioma de origen.

`small` para ambos idiomas por defecto (`arquitectura-base` proponía
`medium` para español, pero en CPU su latencia no sirve para subtítulos
en vivo; `DECILO_WHISPER_ES=medium` lo restaura). Las transcripciones
provisionales usan un modelo chico aparte (`base`): son un anticipo que
la pasada final corrige, y con el modelo grande cada anticipo tardaba
más que lo que anticipaba.
"""

from __future__ import annotations

import os
from pathlib import Path
from threading import Lock

from decilo.providers import provider

MODEL_BY_LANGUAGE = {"en": "small", "es": "small"}
_models: dict[str, object] = {}
_model_lock = Lock()
_load_locks: dict[str, Lock] = {}


def WhisperModel(*args, **kwargs):
    from faster_whisper import WhisperModel as Model
    return Model(*args, **kwargs)


def _size_for(language: str, fast: bool) -> str:
    if fast:
        return os.environ.get("DECILO_WHISPER_FAST", "base")
    if language == "es":
        return os.environ.get("DECILO_WHISPER_ES", MODEL_BY_LANGUAGE["es"])
    return MODEL_BY_LANGUAGE.get(language, "small")


def _get_model(language: str, fast: bool = False):
    size = _size_for(language, fast)
    # Two simultaneous sessions must not allocate the same cold model twice.
    with _model_lock:
        load_lock = _load_locks.setdefault(size, Lock())
    with load_lock:
        model = _models.get(size)
        if model is None:
            # La mitad de los hilos: la otra mitad queda para la pasada final
            # o la traducción, que corren a la vez que las provisionales.
            model = WhisperModel(size, device="cpu", compute_type="int8",
                                 cpu_threads=max(4, (os.cpu_count() or 8) // 2))
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


def transcribe(audio_path: Path, language: str, *, beam_size: int = 5,
               fast: bool = False) -> str:
    """Bloqueante y CPU-bound: correr con `asyncio.to_thread`.

    `fast=True` usa el modelo chico de anticipos provisionales."""
    return " ".join(text for text, _end in
                    transcribe_segments(audio_path, language, beam_size=beam_size, fast=fast))


def transcribe_segments(audio_path: Path, language: str, *, beam_size: int = 5,
                        fast: bool = False) -> list[tuple[str, float]]:
    """Como `transcribe`, pero conserva (texto, fin_en_segundos) por segmento
    de Whisper: los cortes por fin de oración necesitan saber DÓNDE terminó."""
    if provider('stt') == 'gemini':
        from decilo.gemini import transcribe as cloud_transcribe
        text = cloud_transcribe(audio_path, language)
        return [(text, 0.0)] if text else []
    model = _get_model(language, fast)
    segments, _info = model.transcribe(
        str(audio_path),
        language=language,
        beam_size=beam_size,
        vad_filter=True,
        condition_on_previous_text=False,
        no_speech_threshold=NO_SPEECH_THRESHOLD,
    )
    return [(s.text.strip(), s.end) for s in segments
            if s.no_speech_prob < NO_SPEECH_THRESHOLD]


def detect_language(pcm: bytes) -> str:
    """Detecta el idioma (en/es) sobre PCM crudo de 16kHz mono.

    Argmax restringido a los idiomas que la sesión puede tener: aunque el
    modelo crea escuchar portugués, elegir el más probable entre en/es es
    mejor que crear una sesión con un idioma que el contrato no admite.
    Usa `small` (el de inglés): para detectar alcanza y carga más rápido.
    """
    import tempfile
    import wave

    model = _get_model("en")
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as file:
        path = Path(file.name)
    try:
        with wave.open(str(path), "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(16000)
            wav.writeframes(pcm)
        _segments, info = model.transcribe(str(path), language=None, vad_filter=True)
        probs = dict(getattr(info, "all_language_probs", None) or [])
        return "en" if probs.get("en", 0.0) >= probs.get("es", 0.0) else "es"
    finally:
        path.unlink(missing_ok=True)
