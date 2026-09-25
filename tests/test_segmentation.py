import struct
import wave

import pytest

from decilo.capture import CaptureBuffer
from decilo.gateway import SessionGateway
from decilo.models import Session
from decilo.pipeline import _iter_pause_chunks
from decilo.segmentation import PauseConfig, PauseSegmenter
from decilo.stream import SessionStream

RATE = 16000


def pcm(seconds, amplitude=4000):
    return struct.pack('<h', amplitude) * round(seconds * RATE)


def segment(data, packet_samples, config=PauseConfig()):
    cutter = PauseSegmenter(config)
    result = []
    for offset in range(0, len(data), packet_samples * 2):
        result.extend(cutter.feed(data[offset:offset + packet_samples * 2]))
    result.extend(cutter.flush())
    return result


def test_pause_boundaries_independent_of_transport_and_preserve_samples():
    data = pcm(1.2) + pcm(.4, 0) + pcm(1.8) + pcm(.4, 0) + pcm(.233)
    small = segment(data, 317)
    large = segment(data, 80000)
    assert small == large
    assert [s.reason for s in small] == ['pause', 'pause', 'end_of_stream']
    assert [(s.end - s.start) / RATE for s in small] == [1.6, 2.2, .233]
    assert b''.join(s.pcm for s in small) == data
    assert all(a.end == b.start for a, b in zip(small, small[1:]))


def test_continuous_speech_forces_exact_maximum():
    config = PauseConfig(max_seconds=2.013)
    data = pcm(7.1)
    result = segment(data, 701, config)
    assert all(s.end - s.start <= round(config.max_seconds * RATE) for s in result)
    assert [s.reason for s in result] == ['deadline'] * 3 + ['end_of_stream']
    assert b''.join(s.pcm for s in result) == data


def test_short_pause_does_not_split_and_silence_has_no_voice():
    assert len(segment(pcm(1) + pcm(.2, 0) + pcm(1), 100)) == 1
    result = segment(pcm(15, 0), 2000)
    assert not any(s.has_voice for s in result)
    assert sum(s.end - s.start for s in result) == 15 * RATE


@pytest.mark.parametrize('kwargs', [{'max_seconds': float('inf')}, {'pause_seconds': 0},
    {'min_seconds': 7}, {'max_seconds': 16}, {'silence_rms': -1}])
def test_invalid_configuration(kwargs):
    with pytest.raises(ValueError):
        PauseConfig(**kwargs)


def buffer(config=PauseConfig()):
    stream = SessionStream(Session(id='seg', title='Seg', source_language='en', status='live'))
    return CaptureBuffer(SessionGateway(stream), segmentation=config)


def test_capture_disconnect_flushes_without_joining_across_gap():
    pending = buffer()
    pending.add(struct.pack('<I', 0) + pcm(1))
    assert pending.queue.empty()
    pending.add(struct.pack('<I', 2 * RATE) + pcm(.6) + pcm(.4, 0))
    pending.finish()
    first, second = pending.queue.get_nowait(), pending.queue.get_nowait()
    assert first[1:3] == (0, RATE)
    assert second[1:3] == (2 * RATE, 3 * RATE)
    assert pending.gateway.stream.gaps[0].reason == 'source_disconnect'


def test_capture_budget_is_audio_duration_not_two_small_segments():
    pending = buffer(PauseConfig(min_seconds=.5, pause_seconds=.1))
    block = (pcm(.4) + pcm(.1, 0)) * 10
    pending.add(struct.pack('<I', 0) + block)
    assert pending.queue.qsize() == 10
    assert not pending.gateway.stream.gaps
    pending.add(struct.pack('<I', 5 * RATE) + block)
    pending.add(struct.pack('<I', 10 * RATE) + block)
    assert pending.queued_samples <= 12 * RATE
    assert pending.queue.qsize() <= pending.queue.maxsize
    assert all(g.reason == 'overload' for g in pending.gateway.stream.gaps)
    assert pending.gateway.stream.gaps


def test_file_boundaries_match_capture_and_do_not_create_silent_wav(tmp_path):
    path = tmp_path / 'test.wav'
    data = pcm(1.2) + pcm(.4, 0) + pcm(7, 0)
    with wave.open(str(path), 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(RATE)
        wav.writeframes(data)
    chunks = list(_iter_pause_chunks(path, PauseConfig()))
    try:
        assert [(s, e, reason) for _, s, e, reason in chunks] == [
            (0, 1600, 'pause'), (1600, 7600, 'deadline'), (7600, 8600, 'end_of_stream')]
        assert chunks[0][0] is not None
        assert chunks[1][0] is chunks[2][0] is None
    finally:
        for generated, *_ in chunks:
            if generated:
                generated.unlink()
