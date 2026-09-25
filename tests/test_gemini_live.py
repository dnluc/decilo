"""Transcripción en vivo contra Gemini Live: manejo de mensajes y ruteo."""
import asyncio

import pytest

from decilo.gemini_live import GeminiLiveTranscriber, _offset_ms
from decilo.models import Session
from decilo.stream import SessionStream


class FakeGateway:
    def __init__(self, stream):
        self.stream = stream
        self.events = []

    def publish_nowait(self, event):
        if event is not None:
            self.events.append(event)


def make_live(translations=('es',), submit=None):
    stream = SessionStream(Session(
        id='cap-1', title='Charla', source_language='en',
        translation_languages=list(translations), status='live',
    ))
    gateway = FakeGateway(stream)
    return GeminiLiveTranscriber(gateway, submit, 'en'), gateway


def captions(gateway):
    return [e.data for e in gateway.events if e.type == 'caption.upsert']


def test_offset_parsing():
    assert _offset_ms('1.120s') == 1120
    assert _offset_ms('0.160s') == 160


@pytest.mark.asyncio
async def test_interims_grow_and_final_confirms_same_segment():
    live, gateway = make_live(translations=())
    live.fed_samples = 16000  # 1s de audio ya enviado
    await live.handle({'voiceActivity': {'type': 'ACTIVITY_START', 'audioOffset': '0.200s'}})
    await live.handle({'serverContent': {'interimInputTranscription': {'text': 'Welcome'}}})
    await live.handle({'serverContent': {'interimInputTranscription': {'text': 'Welcome to this'}}})
    await live.handle({'serverContent': {'inputTranscription': {'text': 'Welcome to this talk.'}}})

    got = captions(gateway)
    assert [(c.revision, c.status) for c in got] == [
        (1, 'provisional'), (2, 'provisional'), (3, 'final')]
    assert all(c.segment_id == 'seg-1' for c in got)
    assert got[0].start_ms == 200  # del voiceActivity, no del contador
    assert got[-1].boundary_reason == 'pause'


@pytest.mark.asyncio
async def test_next_utterance_is_a_new_segment():
    live, gateway = make_live(translations=())
    await live.handle({'serverContent': {'inputTranscription': {'text': 'First sentence.'}}})
    await live.handle({'serverContent': {'interimInputTranscription': {'text': 'Second'}}})
    got = captions(gateway)
    assert [(c.segment_id, c.revision) for c in got] == [('seg-1', 1), ('seg-2', 1)]


@pytest.mark.asyncio
async def test_repeated_interim_text_is_not_republished():
    live, gateway = make_live(translations=())
    await live.handle({'serverContent': {'interimInputTranscription': {'text': 'Hola'}}})
    await live.handle({'serverContent': {'interimInputTranscription': {'text': 'Hola'}}})
    assert len(captions(gateway)) == 1


@pytest.mark.asyncio
async def test_final_submits_translation():
    submitted = []

    async def submit(caption):
        submitted.append(caption)

    live, gateway = make_live(translations=('es',), submit=submit)
    await live.handle({'serverContent': {'interimInputTranscription': {'text': 'Hello'}}})
    await live.handle({'serverContent': {'inputTranscription': {'text': 'Hello world.'}}})
    assert [c.status for c in submitted] == ['final']
    assert submitted[0].text == 'Hello world.'


@pytest.mark.asyncio
async def test_empty_final_retires_provisionals_with_gap():
    live, gateway = make_live(translations=())
    await live.handle({'serverContent': {'interimInputTranscription': {'text': 'mmm'}}})
    await live.handle({'serverContent': {'inputTranscription': {'text': '  '}}})
    gaps = [e.data for e in gateway.events if e.type == 'session.gap']
    assert len(gaps) == 1
    discarded = gaps[0].discard_captions[0]
    assert (discarded.segment_id, discarded.kind, discarded.language) == ('seg-1', 'transcript', 'en')


@pytest.mark.asyncio
async def test_stream_end_confirms_last_provisional():
    """Si el audio se corta sin pausa, la última hipótesis no queda gris."""
    live, gateway = make_live(translations=())
    await live.handle({'serverContent': {'interimInputTranscription': {'text': 'Goodbye every'}}})
    live._confirm_open_segment()
    got = captions(gateway)
    assert got[-1].status == 'final'
    assert got[-1].text == 'Goodbye every'
    assert got[-1].boundary_reason == 'end_of_stream'
    assert got[-1].revision == 2


@pytest.mark.asyncio
async def test_capture_falls_back_when_live_connection_fails(monkeypatch):
    """Si Google no contesta, la captura sigue viva por el camino de segmentos."""
    from decilo import capture, gemini_live, providers

    monkeypatch.setattr(gemini_live.GeminiLiveTranscriber, 'connect',
                        lambda self: (_ for _ in ()).throw(RuntimeError('sin red')))
    token = providers.use_provider('gemini')
    try:
        stream = SessionStream(Session(id='cap-1', title='t', source_language='en',
                                       translation_languages=[], status='live'))
        gateway = FakeGateway(stream)
        live = await capture._start_live(gateway, None)
    finally:
        providers.reset_provider(token)
    assert live is None
    errors = [e for e in gateway.events if e.type == 'session.error']
    assert errors and 'segmentos' in errors[0].data.message


@pytest.mark.asyncio
async def test_local_provider_never_touches_live(monkeypatch):
    from decilo import capture, gemini_live, providers

    monkeypatch.setattr(gemini_live.GeminiLiveTranscriber, 'connect',
                        lambda self: pytest.fail('No debería conectar con Gemini'))
    token = providers.use_provider('local')
    try:
        stream = SessionStream(Session(id='cap-1', title='t', source_language='en',
                                       translation_languages=[], status='live'))
        assert await capture._start_live(FakeGateway(stream), None) is None
    finally:
        providers.reset_provider(token)
