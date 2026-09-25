import asyncio

import pytest
from fastapi.testclient import TestClient

import decilo.app as module
from decilo.models import Session
from decilo.sessions import SessionRegistry


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("DECILO_DEMO_SESSIONS", "1")
    monkeypatch.setenv("DECILO_DEMO_AUTOSTART", "0")
    monkeypatch.setattr(module, "registry", SessionRegistry())
    monkeypatch.setattr(module, "gateways", {})
    monkeypatch.setattr(module, "audio_sources", {})
    monkeypatch.setattr(module, "file_tasks", {})
    monkeypatch.setattr(module, "_background_tasks", set())
    calls = []

    async def worker(stream, gateway, path, **kwargs):
        calls.append(stream.session.id)
        await asyncio.Event().wait()

    monkeypatch.setattr(module, "run_file_session", worker)
    with TestClient(module.app) as client:
        yield client, calls


def test_audio_range_missing_and_no_autostart(client):
    http, calls = client
    sid = http.get('/api/v1/sessions').json()['sessions'][0]['id']
    assert not calls
    full = http.get(f'/api/v1/sessions/{sid}/audio')
    assert full.status_code == 200
    part = http.get(f'/api/v1/sessions/{sid}/audio', headers={'Range': 'bytes=0-9'})
    assert part.status_code == 206
    assert part.content == full.content[:10]
    assert part.headers['content-range'].startswith('bytes 0-9/')
    assert http.get('/api/v1/sessions/missing/audio').status_code == 404
    module.registry.register(Session(id='no-audio', title='No audio', source_language='en',
                                     translation_languages=[], status='starting'))
    assert http.get('/api/v1/sessions/no-audio/audio').status_code == 404


def test_start_idempotent_and_capacity(client):
    http, calls = client
    sid = http.get('/api/v1/sessions').json()['sessions'][0]['id']
    ids = [http.post(f'/api/v1/sessions/{sid}/runs').json()['id'] for _ in range(3)]
    assert len(set(ids)) == 3
    for run in ids[:2]:
        assert http.post(f'/api/v1/sessions/{run}/start').status_code == 200
        assert http.post(f'/api/v1/sessions/{run}/start').status_code == 200
    assert http.post(f'/api/v1/sessions/{ids[2]}/start').status_code == 429
    assert sorted(calls) == sorted(ids[:2])
    assert module.registry.get(sid).session.status == 'starting'


def test_terminal_and_retention_limits(client):
    http, _ = client
    sid = http.get('/api/v1/sessions').json()['sessions'][0]['id']
    module.registry.get(sid).transition_to('ended')
    assert http.post(f'/api/v1/sessions/{sid}/start').status_code == 409
    for _ in range(18):
        assert http.post(f'/api/v1/sessions/{sid}/runs').status_code == 201
    assert http.post(f'/api/v1/sessions/{sid}/runs').status_code == 429


def test_control_disabled_outside_demo(client, monkeypatch):
    http, _ = client
    sid = http.get('/api/v1/sessions').json()['sessions'][0]['id']
    monkeypatch.setenv('DECILO_DEMO_SESSIONS', '0')
    assert http.post(f'/api/v1/sessions/{sid}/start').status_code == 404
    assert http.post(f'/api/v1/sessions/{sid}/runs').status_code == 404
