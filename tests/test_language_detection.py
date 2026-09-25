"""Autodetección del idioma de entrada en la captura."""
import struct
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from decilo import stt
from decilo.app import app, audio_sources, gateways, registry

RATE = 16000


@pytest.fixture(autouse=True)
def clean_registry():
    yield
    registry._records.clear()
    gateways.clear()
    audio_sources.clear()


def fake_whisper(all_language_probs):
    info = SimpleNamespace(all_language_probs=all_language_probs)
    return Mock(transcribe=Mock(return_value=([], info)))


def test_detection_is_restricted_to_supported_languages(monkeypatch):
    """Aunque el modelo crea escuchar otro idioma, la sesión solo puede ser
    en/es: se elige el más probable de los dos, no el máximo global."""
    monkeypatch.setitem(stt._models, 'small', fake_whisper(
        [('pt', 0.6), ('es', 0.3), ('en', 0.1)],
    ))
    assert stt.detect_language(b'\x00\x00' * RATE) == 'es'

    monkeypatch.setitem(stt._models, 'small', fake_whisper(
        [('pt', 0.5), ('en', 0.3), ('es', 0.2)],
    ))
    assert stt.detect_language(b'\x00\x00' * RATE) == 'en'


def test_detection_survives_missing_probabilities(monkeypatch):
    monkeypatch.setitem(stt._models, 'small', fake_whisper(None))
    assert stt.detect_language(b'\x00\x00' * RATE) in {'en', 'es'}


def packet(offset_samples, seconds, amplitude=12000):
    samples = [amplitude] * int(RATE * seconds)
    return struct.pack('<I', offset_samples) + struct.pack(f'<{len(samples)}h', *samples)


def test_auto_capture_detects_then_creates_session(monkeypatch):
    monkeypatch.setenv('DECILO_DEMO_SESSIONS', '1')
    monkeypatch.setenv('DECILO_PARTIALS', '0')
    detect_inputs = []

    def fake_detect(pcm):
        detect_inputs.append(len(pcm) // 2)
        return 'es'

    monkeypatch.setattr(stt, 'detect_language', fake_detect)

    async def fake_process(stream, gateway, path, seq, start, end, **kwargs):
        return None

    import decilo.pipeline as pipeline
    monkeypatch.setattr(pipeline, 'process_chunk', fake_process)
    import decilo.capture as capture
    monkeypatch.setattr(capture, 'process_chunk', fake_process)

    with TestClient(app) as client:
        with client.websocket_connect('/api/v1/capture?language=auto&provider=local') as ws:
            assert ws.receive_json() == {'type': 'detecting'}
            # 3s con voz: supera el umbral de 2.5s y dispara la detección.
            offset = 0
            for _ in range(3):
                ws.send_bytes(packet(offset, 1.0))
                offset += RATE
            ready = ws.receive_json()
            assert ready['type'] == 'ready'
            assert ready['session']['source_language'] == 'es'
            assert ready['session']['translation_languages'] == []
            ws.send_text('stop')
    # Todo el audio de la fase de detección se conservó para transcribir.
    assert detect_inputs and detect_inputs[0] >= RATE * 2.5


def test_auto_capture_stop_before_detection_creates_nothing(monkeypatch):
    monkeypatch.setenv('DECILO_DEMO_SESSIONS', '1')
    with TestClient(app) as client:
        with client.websocket_connect('/api/v1/capture?language=auto') as ws:
            assert ws.receive_json() == {'type': 'detecting'}
            ws.send_text('stop')
            # El servidor cierra sin haber creado ninguna sesión de captura
            # (las de muestra del arranque no cuentan).
    assert not [s for s in registry.list_sessions() if s.id.startswith('capture-')]
