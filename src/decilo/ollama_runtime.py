"""Clients owned by a lifespan and event loop, never shared across loops."""
import asyncio
from contextlib import asynccontextmanager

import httpx

_clients: dict[asyncio.AbstractEventLoop, httpx.AsyncClient] = {}


@asynccontextmanager
async def ollama_lifespan(client=None):
    loop = asyncio.get_running_loop()
    if loop in _clients:
        yield _clients[loop]
        return
    owned = client is None
    client = client or httpx.AsyncClient(timeout=30)
    _clients[loop] = client
    try:
        yield client
    finally:
        del _clients[loop]
        if owned:
            await client.aclose()


@asynccontextmanager
async def ollama_client():
    client = _clients.get(asyncio.get_running_loop())
    if client is not None:
        yield client
    else:
        # Standalone scripts remain supported; wrap their whole run to reuse.
        async with httpx.AsyncClient(timeout=30) as client:
            yield client
