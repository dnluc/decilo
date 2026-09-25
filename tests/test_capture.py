import struct

import pytest
from fastapi.testclient import TestClient

import decilo.app as app
import decilo.capture as capture
from decilo.gateway import SessionGateway
from decilo.models import Session
from decilo.sessions import SessionRegistry
from decilo.stream import SessionStream


def packet(start=0, samples=160):
    return struct.pack('<I', start) + b'\0\0' * samples


@pytest.mark.parametrize('data,previous', [(b'', 0), (b'12345', 0),
    (packet(samples=80001), 0), (packet(0), 1), (packet(16000 * 3600), 0)])
def test_invalid_packet(data, previous):
    with pytest.raises(ValueError):
        capture.decode_packet(data, previous)


def test_overload_discards_oldest_and_reports_gap():
    stream = SessionStream(Session(id='test', title='test', source_language='en', status='live'))
    buffer = capture.CaptureBuffer(SessionGateway(stream))
    for i in range(3):
        buffer.add(packet(i * 160))
    assert buffer.queue.qsize() == 2
    assert buffer.queue.get_nowait()[0] == 2
    assert stream.gaps[0].reason == 'overload'
    assert (stream.gaps[0].start_ms, stream.gaps[0].end_ms) == (0, 10)


def test_capture_end_to_end_and_disconnect(monkeypatch):
    monkeypatch.setenv('DECILO_DEMO_SESSIONS', '1')
    monkeypatch.setenv('DECILO_DEMO_AUTOSTART', '0')
    monkeypatch.setattr(app, 'registry', SessionRegistry())
    monkeypatch.setattr(app, 'gateways', {})
    monkeypatch.setattr(app, 'file_tasks', {})
    monkeypatch.setattr(app, 'audio_sources', {})
    received = []

    async def fake_process(stream, gateway, path, seq, start, end):
        received.append((path.read_bytes(), seq, start, end))

    monkeypatch.setattr(capture, 'process_chunk', fake_process)
    with TestClient(app.app) as client:
        with client.websocket_connect('/api/v1/capture?language=en') as ws:
            ready = ws.receive_json()
            sid = ready['session']['id']
            ws.send_bytes(packet())
            ws.send_text('stop')
            assert ws.receive()['type'] == 'websocket.close'
        assert received[0][0][:4] == b'RIFF'
        assert received[0][1:] == (1, 0, 10)
        assert client.get(f'/api/v1/sessions/{sid}').json()['status'] == 'ended'
        assert not app.file_tasks
        # Invalid order must terminate without sending that packet to inference.
        with client.websocket_connect('/api/v1/capture?language=en') as ws:
            sid = ws.receive_json()['session']['id']
            ws.send_bytes(b'invalid')
            assert ws.receive()['type'] == 'websocket.close'
        assert len(received) == 1
        assert app.gateways[sid].stream.gaps[0].reason == 'source_disconnect'
