import asyncio
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

import decilo.app as application
from decilo import stt


@pytest.mark.asyncio
async def test_preparation_keeps_start_blocked_until_both_providers_ready(monkeypatch):
    release = asyncio.Event()
    entered = asyncio.Event()
    languages = []
    monkeypatch.setattr(stt, '_get_model', lambda lang: languages.append(lang))
    monkeypatch.setenv('DECILO_DEMO_AUTOSTART', '0')
    async def prepare():
        entered.set()
        await release.wait()
        return {}
    monkeypatch.setattr(application, 'prepare_ollama', prepare)
    monkeypatch.setattr(application.app.state, 'inference_readiness', 'starting', raising=False)
    task = asyncio.create_task(application._prepare_models(application.app))
    try:
        await asyncio.wait_for(entered.wait(), 1)
        assert not application._models_ready()
        with pytest.raises(HTTPException) as exc:
            await application.inference_ready()
        assert exc.value.status_code == 503
        release.set()
        await asyncio.wait_for(task, 1)
        assert application._models_ready()
        assert languages == ['en', 'es']
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)


@pytest.mark.asyncio
async def test_failed_preparation_never_claims_ready(monkeypatch):
    monkeypatch.setattr(stt, '_get_model', lambda lang: None)
    monkeypatch.setattr(application, 'prepare_ollama', AsyncMock(side_effect=RuntimeError('private')))
    monkeypatch.setattr(application.app.state, 'inference_readiness', 'starting', raising=False)
    await application._prepare_models(application.app)
    assert application.app.state.inference_readiness == 'error'
    assert not application._models_ready()
