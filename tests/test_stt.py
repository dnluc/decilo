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
