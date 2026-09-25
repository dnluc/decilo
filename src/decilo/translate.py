"""Ollama translation, with optional real streaming and scoped connections.

Latency and technical terminology remain subject to measurement; stream tokens
are provisional until the provider explicitly completes generation.
"""

from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass

import httpx

from decilo.ollama_runtime import ollama_client
from decilo.providers import provider

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "gemma3n:e2b"
SYSTEM_PROMPT = (
    "Sos un traductor simultaneo de una charla tecnica de una conferencia "
    "de software. Traduci el texto del ingles al espanol de forma natural, "
    "como lo diria un orador en una charla tecnica en Argentina. Mantene "
    "terminos tecnicos de uso habitual en la industria en vez de forzar "
    "una traduccion literal rara. El texto puede llegar incompleto, a mitad "
    "de una frase: traduci lo que hay sin inventar el final. Si una palabra "
    "es ambigua o parece mal transcripta, elegi la interpretacion mas "
    "natural segun el contexto de la charla, sin marcadores de duda ni "
    "alternativas. Responde SOLO con la traduccion, sin comentarios ni "
    "explicaciones."
)

# Contexto corto: los subtitulos son frases sueltas y en CPU el costo de
# procesar el prompt crece con el contexto reservado.
OLLAMA_OPTIONS = {"temperature": 0, "num_ctx": 1024}


async def translate(text: str, *, model: str = MODEL, timeout: float = 30.0) -> str:
    if provider('translation') == 'gemini':
        from decilo.gemini import translate as cloud_translate
        return await cloud_translate(text, SYSTEM_PROMPT, timeout)
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
        "stream": False,
        "options": OLLAMA_OPTIONS,
    }
    async with ollama_client() as client:
        resp = await client.post(OLLAMA_URL, json=payload, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        text = data["message"]["content"].strip()
        # Con entradas truncadas, Gemma a veces agrega el texto original u
        # otra variante tras una línea en blanco: un subtítulo es un bloque.
        return text.split("\n\n")[0].strip()


@dataclass(frozen=True)
class TranslationUpdate:
    text: str
    final: bool
    metrics: dict | None = None


def ollama_metrics(data):
    """Ollama durations are nanoseconds; counts are not durations."""
    metrics = {}
    for name in ('total_duration', 'load_duration', 'prompt_eval_duration', 'eval_duration'):
        value = data.get(name)
        if isinstance(value, (int, float)) and value >= 0:
            metrics[name.removesuffix('_duration') + '_seconds'] = value / 1e9
    for name in ('prompt_eval_count', 'eval_count'):
        value = data.get(name)
        if isinstance(value, int) and value >= 0:
            metrics[name] = value
    return metrics


async def _ndjson(response):
    # Bound even a malformed server that never sends a newline.
    pending = bytearray()
    total = 0
    async for chunk in response.aiter_bytes():
        total += len(chunk)
        if total > 1_048_576:
            raise RuntimeError('Respuesta de Ollama demasiado grande')
        pending.extend(chunk)
        while b'\n' in pending:
            line, _, rest = pending.partition(b'\n')
            pending = bytearray(rest)
            if len(line) > 65536:
                raise RuntimeError('Fragmento de Ollama demasiado grande')
            if line.strip():
                yield json.loads(line)
        if len(pending) > 65536:
            raise RuntimeError('Fragmento de Ollama demasiado grande')
    if pending.strip():
        yield json.loads(pending)


async def translate_stream(text, *, model=MODEL, timeout=30):
    """Real cumulative content, final only on an explicit successful done."""
    # El selector de proveedor manda también acá: sin esto, activar streaming
    # con DECILO_AI_PROVIDER=gemini iría igual a Ollama e ignoraría la elección.
    # Un proveedor sin streaming publica una única actualización final; no se
    # simulan parciales que el proveedor no entregó.
    if provider('translation') != 'local':
        yield TranslationUpdate(await translate(text, timeout=timeout), True)
        return
    payload = {
        'model': model,
        'messages': [{'role': 'system', 'content': SYSTEM_PROMPT},
                     {'role': 'user', 'content': text}],
        'stream': True,
        'options': OLLAMA_OPTIONS,
        'keep_alive': os.environ.get('DECILO_OLLAMA_KEEP_ALIVE', '5m'),
    }
    accumulated = ''
    try:
        async with asyncio.timeout(timeout):
            async with ollama_client() as client:
                async with client.stream('POST', OLLAMA_URL, json=payload, timeout=timeout) as response:
                    if response.status_code != 200:
                        raise RuntimeError(f'Ollama HTTP {response.status_code}')
                    async for data in _ndjson(response):
                        if not isinstance(data, dict) or data.get('error'):
                            raise RuntimeError('Ollama informó un error de generación')
                        message = data.get('message', {})
                        content = message.get('content', '')
                        if not isinstance(content, str) or message.get('tool_calls'):
                            raise RuntimeError('Respuesta de traducción inválida')
                        accumulated += content  # Never publish message.thinking.
                        if len(accumulated.encode('utf-8')) > 8192:
                            raise RuntimeError('La traducción supera el límite del contrato')
                        if data.get('done') is True:
                            if data.get('done_reason') != 'stop' or not accumulated.strip():
                                raise RuntimeError('Ollama no completó la traducción')
                            yield TranslationUpdate(accumulated.strip(), True, ollama_metrics(data))
                            return
                        if content and accumulated.strip():
                            yield TranslationUpdate(accumulated.strip(), False)
        raise RuntimeError('Ollama cerró sin confirmar la traducción')
    except (httpx.RequestError, TimeoutError):
        raise RuntimeError('Se interrumpió la conexión o venció el tiempo de Ollama') from None
    except (ValueError, TypeError, AttributeError):
        raise RuntimeError('Ollama devolvió un flujo inválido') from None


async def prepare_ollama():
    async with ollama_client() as client:
        response = await client.post(OLLAMA_URL, json={
            'model': MODEL, 'messages': [], 'stream': False,
            'keep_alive': os.environ.get('DECILO_OLLAMA_KEEP_ALIVE', '5m'),
        }, timeout=60)
        if response.status_code != 200 or response.json().get('done') is not True:
            raise RuntimeError('No se pudo preparar Ollama')
        return ollama_metrics(response.json())
