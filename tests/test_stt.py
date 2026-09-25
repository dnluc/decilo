from concurrent.futures import ThreadPoolExecutor
from threading import Event
from unittest.mock import Mock

from decilo import stt


def test_concurrent_sessions_share_one_model(monkeypatch):
    entered = Event()
    release = Event()
    second_started = Event()
    model = object()

    def constructor(*args, **kwargs):
        entered.set()
        assert release.wait(2)
        return model

    factory = Mock(side_effect=constructor)
    monkeypatch.setattr(stt, '_models', {})
    monkeypatch.setattr(stt, 'WhisperModel', factory)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(stt._get_model, 'en')
        assert entered.wait(2)

        def second_session():
            second_started.set()
            return stt._get_model('en')

        second = pool.submit(second_session)
        assert second_started.wait(2)
        release.set()
        assert first.result() is second.result() is model
    factory.assert_called_once()


def test_silence_is_filtered_instead_of_hallucinated(monkeypatch):
    """Whisper inventa frases sobre audio sin habla ("¡SUSCRÍBETE!", muletillas).

    Se pide el VAD y se descartan los segmentos con alta probabilidad de
    no-habla; sin esto esas frases llegan a la pantalla como si alguien las
    hubiera dicho.
    """
    captured = {}

    class FakeSegment:
        def __init__(self, text, no_speech_prob, end=1.0):
            self.text = text
            self.no_speech_prob = no_speech_prob
            self.end = end

    def fake_transcribe(path, **kwargs):
        captured.update(kwargs)
        return [
            FakeSegment(' Hola, esto sí es voz.', 0.05),
            FakeSegment(' ¡SUSCRÍBETE!', 0.93),
        ], object()

    monkeypatch.setattr(stt, '_models', {'small': Mock(transcribe=fake_transcribe)})
    text = stt.transcribe('audio.wav', 'en')

    assert text == 'Hola, esto sí es voz.', 'la alucinación no debe llegar al texto'
    assert captured['vad_filter'] is True
    assert captured['condition_on_previous_text'] is False
    assert captured['no_speech_threshold'] == stt.NO_SPEECH_THRESHOLD
