"""Elección de proveedor por sesión (botón Local/Nube del frontend)."""
import asyncio

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from decilo import providers
from decilo.app import app, audio_sources, gateways, registry
from decilo.providers import provider, use_provider


@pytest.fixture(autouse=True)
def clean_registry():
    """El registro es global al módulo: sin limpiarlo, cada TestClient vuelve
    a registrar las sesiones de muestra y el siguiente test falla."""
    yield
    registry._records.clear()
    gateways.clear()
    audio_sources.clear()


def test_session_choice_overrides_environment(monkeypatch):
    monkeypatch.setenv('DECILO_AI_PROVIDER', 'local')
    token = use_provider('gemini')
    try:
        assert provider('stt') == 'gemini'
        assert provider('translation') == 'gemini'
    finally:
        providers._session_provider.reset(token)
    # Sin elección explícita vuelve a mandar el entorno.
    assert provider('stt') == 'local'


def test_invalid_choice_is_rejected():
    with pytest.raises(ValueError):
        use_provider('otro')


@pytest.mark.asyncio
async def test_choice_reaches_worker_threads(monkeypatch):
    """La elección tiene que sobrevivir a create_task y to_thread.

    Si no se propagara, el worker transcribiría con el proveedor equivocado
    sin que nadie lo note.
    """
    monkeypatch.setenv('DECILO_AI_PROVIDER', 'local')
    use_provider('gemini')
    seen = {}

    async def worker():
        seen['task'] = provider('stt')
        seen['thread'] = await asyncio.to_thread(provider, 'stt')

    await asyncio.create_task(worker())
    assert seen == {'task': 'gemini', 'thread': 'gemini'}


def test_two_sessions_can_use_different_providers():
    """Un ajuste global haría que una sesión pisara a la otra."""
    async def session(choice):
        use_provider(choice)
        await asyncio.sleep(0)  # deja correr a la otra en el medio
        return provider('translation')

    async def both():
        return await asyncio.gather(
            asyncio.create_task(session('local')),
            asyncio.create_task(session('gemini')),
        )

    assert asyncio.run(both()) == ['local', 'gemini']


def test_catalog_reports_cloud_availability(monkeypatch):
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    with TestClient(app) as client:
        body = client.get('/api/v1/providers').json()
    assert body['cloud_available'] is False
    monkeypatch.setenv('GEMINI_API_KEY', 'clave-de-prueba')
    with TestClient(app) as client:
        body = client.get('/api/v1/providers').json()
    assert body['cloud_available'] is True
    # Nunca debe viajar la clave al navegador.
    assert 'clave-de-prueba' not in str(body)


def test_capture_rejects_cloud_without_key(monkeypatch):
    monkeypatch.setenv('DECILO_DEMO_SESSIONS', '1')
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    with TestClient(app) as client:
        with pytest.raises(WebSocketDisconnect) as exc:
            with client.websocket_connect('/api/v1/capture?language=en&provider=gemini'):
                pass
        assert exc.value.code == 4403


def test_capture_rejects_unknown_provider(monkeypatch):
    monkeypatch.setenv('DECILO_DEMO_SESSIONS', '1')
    with TestClient(app) as client:
        with pytest.raises(WebSocketDisconnect) as exc:
            with client.websocket_connect('/api/v1/capture?language=en&provider=pirata'):
                pass
        assert exc.value.code == 4403


@pytest.mark.parametrize('choice,default,stt_override,expected', [
    (None, 'gemini', None, ['gemini', 'gemini']),
    ('local', 'gemini', None, ['local', 'local']),
    ('gemini', 'local', None, ['gemini', 'gemini']),
    (None, 'local', 'gemini', ['gemini', 'local']),
])
def test_capture_dispatch_preserves_explicit_and_legacy_choices(monkeypatch, choice, default, stt_override, expected):
    import decilo.capture as capture
    monkeypatch.setenv('DECILO_DEMO_SESSIONS', '1')
    monkeypatch.setenv('DECILO_AI_PROVIDER', default)
    monkeypatch.setenv('GEMINI_API_KEY', 'test-only')
    if stt_override:
        monkeypatch.setenv('DECILO_STT_PROVIDER', stt_override)

    async def receive(websocket, gateway, **kwargs):
        async def worker():
            stt_choice = await asyncio.to_thread(provider, 'stt')
            return [stt_choice, provider('translation')]
        await websocket.send_json(await asyncio.create_task(worker()))
        await websocket.close()

    monkeypatch.setattr(capture, 'receive_capture', receive)
    suffix = '' if choice is None else f'&provider={choice}'
    with TestClient(app) as client:
        with client.websocket_connect('/api/v1/capture?language=en' + suffix) as websocket:
            assert websocket.receive_json() == expected
        assert client.get('/api/v1/providers').json()['default'] == default


@pytest.mark.asyncio
async def test_capture_restores_context_on_failure(monkeypatch):
    from unittest.mock import AsyncMock
    import decilo.app as application
    import decilo.capture as capture
    monkeypatch.setenv('DECILO_DEMO_SESSIONS', '1')
    monkeypatch.setenv('GEMINI_API_KEY', 'test-only')
    monkeypatch.setattr(application, '_models_ready', lambda: True)
    monkeypatch.setattr(capture, 'receive_capture', AsyncMock(side_effect=RuntimeError('capture failed')))
    with pytest.raises(RuntimeError, match='capture failed'):
        await application.capture_audio(AsyncMock(), 'en', 'gemini')
    assert providers.provider('stt') == 'local'
    assert not application.file_tasks


@pytest.mark.parametrize('choice', ['local', 'gemini'])
def test_cloud_capture_independent_of_failed_local_preparation(monkeypatch, choice):
    import decilo.capture as capture
    monkeypatch.setenv('DECILO_DEMO_SESSIONS', '1')
    monkeypatch.setenv('GEMINI_API_KEY', 'test-only')
    async def receive(websocket, gateway, **kwargs):
        await websocket.send_json({'selected': provider('stt')})
        await websocket.close()
    monkeypatch.setattr(capture, 'receive_capture', receive)
    with TestClient(app) as client:
        monkeypatch.setattr(app.state, 'inference_readiness', 'error')
        if choice == 'local':
            with pytest.raises(WebSocketDisconnect) as exc:
                with client.websocket_connect('/api/v1/capture?provider=local'):
                    pass
            assert exc.value.code == 1013
        else:
            with client.websocket_connect('/api/v1/capture?provider=gemini') as websocket:
                assert websocket.receive_json() == {'selected': 'gemini'}


def test_cloud_file_can_start_when_local_preparation_failed(monkeypatch):
    from unittest.mock import AsyncMock
    import decilo.app as application
    monkeypatch.setenv('DECILO_DEMO_SESSIONS', '1')
    monkeypatch.setenv('DECILO_AI_PROVIDER', 'gemini')
    monkeypatch.setenv('GEMINI_API_KEY', 'test-only')
    worker = AsyncMock()
    monkeypatch.setattr(application, 'run_file_session', worker)
    with TestClient(app) as client:
        monkeypatch.setattr(app.state, 'inference_readiness', 'error')
        sid = client.get('/api/v1/sessions').json()['sessions'][0]['id']
        assert client.post(f'/api/v1/sessions/{sid}/start').status_code == 200
    worker.assert_awaited_once()
