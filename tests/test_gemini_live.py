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


# Corte por fin de oración: sin esperar la pausa del VAD.

@pytest.mark.asyncio
async def test_interim_with_sentence_boundary_splits_and_translates():
    submitted = []

    async def submit(caption):
        submitted.append(caption)

    live, gateway = make_live(translations=('es',), submit=submit)
    await live.handle({'serverContent': {'interimInputTranscription':
        {'text': 'First sentence is done. And then it'}}})

    got = captions(gateway)
    assert [(c.segment_id, c.status, c.text) for c in got] == [
        ('seg-1', 'final', 'First sentence is done.'),
        ('seg-2', 'provisional', 'And then it'),
    ]
    assert [c.text for c in submitted] == ['First sentence is done.']


@pytest.mark.asyncio
async def test_official_final_confirms_only_the_uncommitted_tail():
    live, gateway = make_live(translations=())
    await live.handle({'serverContent': {'interimInputTranscription':
        {'text': 'First sentence is done. And then it'}}})
    await live.handle({'serverContent': {'inputTranscription':
        {'text': 'First sentence is done. And then it continued.'}}})

    got = captions(gateway)
    assert got[-1].segment_id == 'seg-2'
    assert got[-1].status == 'final'
    assert got[-1].text == 'And then it continued.'
    # La final oficial pasa a ser el prefijo confirmado del buffer.
    assert live.committed == 'First sentence is done. And then it continued.'


@pytest.mark.asyncio
async def test_smart_rewrite_of_committed_prefix_confirms_last_tail():
    live, gateway = make_live(translations=())
    await live.handle({'serverContent': {'interimInputTranscription':
        {'text': 'First sentence is done. And then it'}}})
    await live.handle({'serverContent': {'inputTranscription':
        {'text': 'Something entirely rewritten.'}}})

    got = captions(gateway)
    assert got[-1].status == 'final'
    assert got[-1].text == 'And then it'  # la última provisional, confirmada


def test_decimals_and_lowercase_do_not_split():
    from decilo.gemini_live import SENTENCE_SPLIT
    assert not SENTENCE_SPLIT.search('the version 3.5 shipped today')
    assert not SENTENCE_SPLIT.search('wait... let me think')
    assert SENTENCE_SPLIT.search('It works. Now the next part')
    assert SENTENCE_SPLIT.search('¿Funciona? Sí, claro')


@pytest.mark.asyncio
async def test_stale_interim_replaying_the_final_is_not_republished():
    """Tras la final oficial, un interim con el mismo texto no duplica nada."""
    live, gateway = make_live(translations=())
    await live.handle({'serverContent': {'inputTranscription':
        {'text': 'First sentence is done. And then it continued.'}}})
    before = len(captions(gateway))
    await live.handle({'serverContent': {'interimInputTranscription':
        {'text': 'First sentence is done. And then it continued.'}}})
    assert len(captions(gateway)) == before


@pytest.mark.asyncio
async def test_interim_buffer_continuing_past_the_final_publishes_only_the_tail():
    live, gateway = make_live(translations=())
    await live.handle({'serverContent': {'inputTranscription':
        {'text': 'First sentence is done.'}}})
    await live.handle({'serverContent': {'interimInputTranscription':
        {'text': 'First sentence is done. Second part'}}})
    got = captions(gateway)
    assert (got[-1].segment_id, got[-1].status, got[-1].text) == ('seg-2', 'provisional', 'Second part')


@pytest.mark.asyncio
async def test_interim_buffer_restarting_after_the_final_is_a_new_utterance():
    live, gateway = make_live(translations=())
    await live.handle({'serverContent': {'inputTranscription':
        {'text': 'First sentence is done.'}}})
    await live.handle({'serverContent': {'interimInputTranscription':
        {'text': 'Fresh start'}}})
    got = captions(gateway)
    assert (got[-1].segment_id, got[-1].status, got[-1].text) == ('seg-2', 'provisional', 'Fresh start')
