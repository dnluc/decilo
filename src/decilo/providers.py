"""Provider selection; environment takes precedence over the local .env file."""
import os
from pathlib import Path

from dotenv import load_dotenv


def load_config():
    load_dotenv(Path(__file__).resolve().parents[2] / '.env', override=False)
    for stage in ('stt', 'translation'):
        if provider(stage) == 'gemini' and not os.environ.get('GEMINI_API_KEY', '').strip():
            raise ValueError('Falta GEMINI_API_KEY para usar Gemini')


def provider(stage):
    value = os.environ.get(f'DECILO_{stage.upper()}_PROVIDER',
                           os.environ.get('DECILO_AI_PROVIDER', 'local'))
    if value not in ('local', 'gemini'):
        raise ValueError('Proveedor inválido: usar local o gemini')
    return value
