"""Transcripción provisional del segmento abierto y su corrección final."""
import asyncio
import struct

import pytest

from decilo import partials as partials_module
from decilo.models import Session
from decilo.partials import RATE, PartialTranscriber
from decilo.stream import SessionStream


class FakeGateway:
    def __init__(self):
        self.events = []

    def publish_nowait(self, event):
        if event is not None:
            self.events.append(event)


def make_stream(language='en'):
    return SessionStream(Session(
        id='cap-1', title='Charla', source_language=language,
        translation_languages=['es'] if language == 'en' else [], status='live',
    ))


def voiced(seconds):
    """PCM con energía por encima del umbral de voz."""
    return struct.pack(f'<{int(RATE * seconds)}h', *([12000] * int(RATE * seconds)))


@pytest.fixture
def fake_transcribe(monkeypatch):
    calls = []

    def transcribe_pcm(pcm, language, *, beam_size):
        calls.append((len(pcm) // 2, beam_size))
        return f'hipotesis de {len(pcm) // 2} muestras'

    monkeypatch.setattr(partials_module, 'transcribe_pcm', transcribe_pcm)
    return calls


async def run_worker_once(partial):
    task = asyncio.create_task(partial.worker())
    # Dejar que el worker tome la instantánea, transcriba y publique.
    for _ in range(20):
        await asyncio.sleep(0.01)
        if partial._latest is None and not partial._wake.is_set():
            break
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)


@pytest.mark.asyncio
async def test_provisionals_grow_and_final_confirms(fake_transcribe):
    stream, gateway = make_stream(), FakeGateway()
    partial = PartialTranscriber(stream, gateway, seq_for=lambda start: 1, language='en')

    partial.observe(0, voiced(1.0), True)
    await run_worker_once(partial)
    partial.observe(0, voiced(1.6), True)
    await run_worker_once(partial)

    captions = [e.data for e in gateway.events if e.type == 'caption.upsert']
    assert [c.revision for c in captions] == [1, 2]
    assert all(c.status == 'provisional' and c.segment_id == 'seg-1' for c in captions)
    assert captions[1].end_ms > captions[0].end_ms
    # Las provisionales son el anticipo barato: beam 1, no el beam de la final.
    assert all(beam == 1 for _, beam in fake_transcribe)

    # El cierre reserva la revisión siguiente para la pasada final.
    assert partial.close(0) == 3


@pytest.mark.asyncio
async def test_small_or_barely_grown_audio_is_not_retranscribed(fake_transcribe):
    stream, gateway = make_stream(), FakeGateway()
    partial = PartialTranscriber(stream, gateway, seq_for=lambda start: 1, language='en')

    partial.observe(0, voiced(0.3), True)          # muy corto
    partial.observe(0, voiced(1.0), True)          # primera instantánea
    partial.observe(0, voiced(1.2), True)          # creció 0.2s: no alcanza
    await run_worker_once(partial)
    assert len(fake_transcribe) == 1

    partial.observe(0, voiced(1.8), True)          # creció 0.8s: sí
    await run_worker_once(partial)
    assert len(fake_transcribe) == 2


@pytest.mark.asyncio
async def test_latest_snapshot_wins_while_worker_is_busy(monkeypatch):
    stream, gateway = make_stream(), FakeGateway()
    sizes = []

    def slow_transcribe(pcm, language, *, beam_size):
        sizes.append(len(pcm) // 2)
        return 'texto'

    monkeypatch.setattr(partials_module, 'transcribe_pcm', slow_transcribe)
    partial = PartialTranscriber(stream, gateway, seq_for=lambda start: 1, language='en')

    # Tres instantáneas encoladas antes de que el worker corra: solo la última
    # tiene sentido, las del medio quedaron viejas antes de nacer.
    partial.observe(0, voiced(1.0), True)
    partial.observe(0, voiced(1.6), True)
    partial.observe(0, voiced(2.2), True)
    await run_worker_once(partial)

    assert sizes == [int(RATE * 2.2)]


@pytest.mark.asyncio
async def test_stale_provisional_after_close_is_dropped(monkeypatch):
    stream, gateway = make_stream(), FakeGateway()
    started = asyncio.Event()
    unblock = asyncio.Event()

    def blocking_transcribe(pcm, language, *, beam_size):
        started.set()
        # Simula una transcripción lenta: el segmento cierra mientras corre.
        import time
        while not unblock.is_set():
            time.sleep(0.01)
        return 'texto viejo'

    monkeypatch.setattr(partials_module, 'transcribe_pcm', blocking_transcribe)
    partial = PartialTranscriber(stream, gateway, seq_for=lambda start: 1, language='en')
    worker = asyncio.create_task(partial.worker())

    partial.observe(0, voiced(1.0), True)
    await asyncio.wait_for(started.wait(), 2)
    final_revision = partial.close(0)   # cierra mientras transcribe
    unblock.set()
    await asyncio.sleep(0.1)
    worker.cancel()
    await asyncio.gather(worker, return_exceptions=True)

    assert gateway.events == [], 'una provisional posterior al cierre no debe publicarse'
    assert final_revision == 1, 'ninguna provisional publicada: la final es la primera revisión'


def test_voiceless_or_closed_segments_are_ignored(fake_transcribe):
    stream, gateway = make_stream(), FakeGateway()
    partial = PartialTranscriber(stream, gateway, seq_for=lambda start: 1, language='en')
    partial.observe(0, voiced(2.0), False)  # sin voz
    partial.close(0)
    partial.observe(0, voiced(2.0), True)   # ya cerrado
    assert partial._latest is None
