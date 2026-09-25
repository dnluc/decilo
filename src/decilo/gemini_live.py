"""Transcripción en vivo vía Gemini Live (gemini-3.5-transcribe-live).

El navegador ya envía exactamente lo que la Live API espera —PCM16 mono a
16kHz en paquetes de ~100ms— así que en modo nube cada paquete se reenvía
tal cual llega, sin segmentador, sin WAVs temporales y sin esperar pausas.
Los `interimInputTranscription` se publican como revisiones provisionales
del segmento abierto y cada `inputTranscription` es la pasada final que lo
confirma y dispara la traducción. La credencial viaja en un header, nunca
en la URL.

`DECILO_GEMINI_LIVE=0` desactiva este camino y vuelve al envío por
segmento; si la conexión con Google falla al arrancar, la captura cae sola
a ese mismo camino.
"""

from __future__ import annotations

import asyncio
import base64
import json
import os

from decilo.models import CaptionData, GapData
from decilo.pipeline import translate_caption

RATE = 16000
LIVE_URL = ('wss://generativelanguage.googleapis.com/ws/'
            'google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent')
# La Live API corta la sesión a los 10 minutos: reconectar antes, sin drama.
RECONNECT_SECONDS = 9 * 60


def live_enabled() -> bool:
    return os.environ.get('DECILO_GEMINI_LIVE', '1') != '0'


def _offset_ms(value: str) -> int:
    """'1.120s' → 1120. Google manda duraciones como texto con sufijo s."""
    return round(float(value.rstrip('s')) * 1000)


class GeminiLiveTranscriber:
    def __init__(self, gateway, submit_translation, language):
        self.gateway = gateway
        self.stream = gateway.stream
        self.submit_translation = submit_translation
        self.language = language
        self.ws = None
        self._reader = None
        self.seq = 0
        self.open_seq = None       # segmento con provisionales publicadas
        self.revision = 0
        self.last_text = None
        self.start_ms = None       # inicio del habla según voiceActivity
        self.base_ms = 0           # audio enviado en conexiones anteriores
        self.fed_samples = 0       # muestras enviadas en la conexión actual
        self.connected_at = 0.0
        self.gaps = 0

    async def connect(self):
        import websockets

        key = os.environ.get('GEMINI_API_KEY', '').strip()
        if not key:
            raise ValueError('Falta GEMINI_API_KEY para usar Gemini')
        model = os.environ.get('DECILO_GEMINI_LIVE_MODEL', 'gemini-3.5-transcribe-live')
        self.ws = await websockets.connect(LIVE_URL, additional_headers={'x-goog-api-key': key})
        await self.ws.send(json.dumps({'setup': {
            'model': f'models/{model}',
            'generationConfig': {'responseModalities': ['TEXT']},
            # SMART limpia muletillas y autocorrecciones: mejor para leer.
            'inputAudioTranscription': {'languageCodes': [self.language], 'mode': 'SMART'},
        }}))
        first = json.loads(await asyncio.wait_for(self.ws.recv(), 10))
        if 'setupComplete' not in first:
            raise RuntimeError('Gemini Live no aceptó la configuración')
        self.connected_at = asyncio.get_running_loop().time()
        self._reader = asyncio.create_task(self._read())

    async def feed(self, pcm: bytes):
        """Un paquete PCM crudo del navegador → un mensaje a Gemini."""
        loop = asyncio.get_running_loop()
        if loop.time() - self.connected_at > RECONNECT_SECONDS:
            await self._reconnect()
        message = json.dumps({'realtimeInput': {'audio': {
            'data': base64.b64encode(pcm).decode('ascii'),
            'mimeType': f'audio/pcm;rate={RATE}',
        }}})
        try:
            await self.ws.send(message)
        except Exception:
            await self._reconnect()
            await self.ws.send(message)
        self.fed_samples += len(pcm) // 2

    async def _reconnect(self):
        """La sesión anterior murió o venció: seguir en una nueva sin perder
        la numeración. Los offsets de Google arrancan de cero en cada
        conexión, así que lo ya enviado pasa a ser la base."""
        await self._close_ws()
        self._confirm_open_segment()
        self.base_ms += self.fed_samples * 1000 // RATE
        self.fed_samples = 0
        self.start_ms = None
        await self.connect()

    async def _read(self):
        try:
            while True:
                await self.handle(json.loads(await self.ws.recv()))
        except asyncio.CancelledError:
            raise
        except Exception:
            return  # feed() detecta el cierre y reconecta; no es fatal acá.

    async def handle(self, msg: dict):
        activity = msg.get('voiceActivity') or {}
        if activity.get('type') == 'ACTIVITY_START' and 'audioOffset' in activity:
            self.start_ms = self.base_ms + _offset_ms(activity['audioOffset'])
        content = msg.get('serverContent') or {}
        interim = content.get('interimInputTranscription')
        if interim is not None:
            self._publish(interim.get('text', ''), final=False)
        final = content.get('inputTranscription')
        if final is not None:
            await self._final(final.get('text', ''))

    def _stream_ms(self) -> int:
        return self.base_ms + self.fed_samples * 1000 // RATE

    def _publish(self, text: str, *, final: bool) -> CaptionData | None:
        text = text.strip()
        if not text or (not final and text == self.last_text):
            return None
        if self.open_seq is None:
            self.seq += 1
            self.open_seq = self.seq
            self.revision = 0
            if self.start_ms is None:
                self.start_ms = self._stream_ms()
        self.revision += 1
        caption = CaptionData(
            segment_id=f'seg-{self.open_seq}', segment_seq=self.open_seq,
            kind='transcript', language=self.language, revision=self.revision,
            source_revision=None, text=text,
            status='final' if final else 'provisional',
            start_ms=self.start_ms, end_ms=max(self._stream_ms(), self.start_ms + 1),
            boundary_reason='pause' if final else None,
        )
        self.gateway.publish_nowait(self.stream.upsert_caption(caption))
        self.last_text = text
        return caption

    async def _final(self, text: str):
        if not text.strip():
            # Gemini retiró lo que creyó oír: las provisionales no pueden
            # quedar como si alguien lo hubiera dicho.
            if self.open_seq is not None:
                self.gaps += 1
                self.gateway.publish_nowait(self.stream.record_gap(GapData(
                    gap_id=f'gap-live-{self.gaps}', start_ms=self.start_ms or 0,
                    end_ms=self._stream_ms(), reason='processing_error',
                    discard_captions=[{'segment_id': f'seg-{self.open_seq}',
                                      'kind': 'transcript', 'language': self.language}],
                )))
        else:
            caption = self._publish(text, final=True)
            if caption is not None and self.stream.session.translation_languages:
                if self.submit_translation is not None:
                    await self.submit_translation(caption)
                else:
                    await translate_caption(self.stream, self.gateway, caption)
        self.open_seq = None
        self.revision = 0
        self.last_text = None
        self.start_ms = None

    def _confirm_open_segment(self):
        """Sin más audio no va a llegar la pasada final: la última provisional
        es lo mejor que se oyó y queda confirmada en vez de gris para siempre."""
        if self.open_seq is not None and self.last_text:
            self.revision += 1
            self.gateway.publish_nowait(self.stream.upsert_caption(CaptionData(
                segment_id=f'seg-{self.open_seq}', segment_seq=self.open_seq,
                kind='transcript', language=self.language, revision=self.revision,
                source_revision=None, text=self.last_text, status='final',
                start_ms=self.start_ms or 0, end_ms=max(self._stream_ms(), (self.start_ms or 0) + 1),
                boundary_reason='end_of_stream',
            )))
        self.open_seq = None
        self.revision = 0
        self.last_text = None

    async def finish(self):
        """Fin de la captura: avisar a Gemini y esperar la final que falte."""
        try:
            await self.ws.send(json.dumps({'realtimeInput': {'audioStreamEnd': True}}))
            for _ in range(30):
                if self.open_seq is None:
                    break
                await asyncio.sleep(0.1)
        except Exception:
            pass
        self._confirm_open_segment()
        await self._close_ws()

    async def _close_ws(self):
        if self._reader is not None:
            self._reader.cancel()
            await asyncio.gather(self._reader, return_exceptions=True)
            self._reader = None
        if self.ws is not None:
            try:
                await self.ws.close()
            except Exception:
                pass
            self.ws = None
