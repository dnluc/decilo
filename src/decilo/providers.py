"""Provider selection; environment takes precedence over the local .env file."""
import os
from contextvars import ContextVar
from pathlib import Path

from dotenv import load_dotenv

# Elección por sesión. Se prefiere esto a un ajuste global mutable: dos
# capturas simultáneas pueden usar proveedores distintos, y apretar el botón
# en una pestaña no cambia en caliente una sesión ajena que ya está corriendo.
# `create_task` y `asyncio.to_thread` propagan el contexto, así que alcanza con
# fijarlo antes de arrancar el worker de la sesión.
_session_provider: ContextVar[str | None] = ContextVar('session_provider', default=None)


def use_provider(value: str | None):
    """Fija el proveedor de esta sesión. Devuelve el token para restaurarlo."""
    if value is not None and value not in ('local', 'gemini'):
        raise ValueError('Proveedor inválido: usar local o gemini')
    return _session_provider.set(value)


def cloud_available() -> bool:
    """Si no hay clave, ofrecer la nube en la interfaz sería una promesa falsa."""
    return bool(os.environ.get('GEMINI_API_KEY', '').strip())


def load_config():
    load_dotenv(Path(__file__).resolve().parents[2] / '.env', override=False)
    for stage in ('stt', 'translation'):
        if provider(stage) == 'gemini' and not os.environ.get('GEMINI_API_KEY', '').strip():
            raise ValueError('Falta GEMINI_API_KEY para usar Gemini')


def provider(stage):
    chosen = _session_provider.get()
    if chosen is not None:
        return chosen
    value = os.environ.get(f'DECILO_{stage.upper()}_PROVIDER',
                           os.environ.get('DECILO_AI_PROVIDER', 'local'))
    if value not in ('local', 'gemini'):
        raise ValueError('Proveedor inválido: usar local o gemini')
    return value
