"""Unit tests must not load a developer's paid credentials or call real services."""
import os

import httpx
import pytest

from decilo import providers


@pytest.fixture(autouse=True)
def isolated_inference(monkeypatch, tmp_path, request):
    if request.node.get_closest_marker('model'):
        yield
        return
    for name in list(os.environ):
        if name.startswith('DECILO_') or name == 'GEMINI_API_KEY':
            monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv('DECILO_ENV_FILE', str(tmp_path / 'absent.env'))
    monkeypatch.setenv('DECILO_DEMO_AUTOSTART', '0')
    token = providers.use_provider(None)

    def no_network(*args, **kwargs):
        pytest.fail('Real HTTP is forbidden in unit tests; use MockTransport')

    async def no_async_network(*args, **kwargs):
        no_network()

    monkeypatch.setattr(httpx.HTTPTransport, 'handle_request', no_network)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, 'handle_async_request', no_async_network)
    try:
        yield
    finally:
        providers.reset_provider(token)
