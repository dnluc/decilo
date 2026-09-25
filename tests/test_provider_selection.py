"""Elección de proveedor por sesión (botón Local/Nube del frontend)."""
import asyncio
import os

import pytest
from fastapi.testclient import TestClient

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
        with pytest.raises(Exception):
            with client.websocket_connect('/api/v1/capture?language=en&provider=gemini'):
                pass


def test_capture_rejects_unknown_provider(monkeypatch):
    monkeypatch.setenv('DECILO_DEMO_SESSIONS', '1')
    with TestClient(app) as client:
        with pytest.raises(Exception):
            with client.websocket_connect('/api/v1/capture?language=en&provider=pirata'):
                pass
