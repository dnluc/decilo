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
import re

from decilo.models import CaptionData, GapData
from decilo.partials import ends_sentence
from decilo.pipeline import translate_caption

RATE = 16000
# Un orador rápido puede no pausar nunca: los interim acumulan oraciones y
# la final (que dispara la traducción) no llega. Si el texto ya muestra un
# final de oración seguido de una nueva (mayúscula o apertura), la parte
# completa se confirma ahí mismo y la cola sigue como segmento nuevo.
SENTENCE_SPLIT = re.compile(r'[.!?…]["\')\]]*\s+(?=["(\[A-Z0-9ÁÉÍÓÚÑÜ¿¡])')
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
        # Prefijo del texto acumulado de Gemini ya confirmado (por cortes de
        # oración o por una final oficial): lo que siga se mide contra esto.
        # Tras una final, el buffer de interims a veces continúa con el texto
        # anterior y a veces arranca de cero; `committed_final` marca que un
        # interim que no coincida es un arranque nuevo, no una reescritura.
        self.committed = ''
        self.committed_final = False
        self._handle_errors = 0
        # Traducciones: las finales corren como tareas para no frenar al
        # lector (si esperara acá, un backlog de traducción congelaría los
        # subtítulos); las provisionales van con un worker aparte, una en
        # vuelo y gana la instantánea más nueva.
        self._translation_tasks: set[asyncio.Task] = set()
        self._pt_latest: tuple[int, str] | None = None
        self._pt_wake = asyncio.Event()
        self._pt_worker: asyncio.Task | None = None

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
        if self._pt_worker is None and self.stream.session.translation_languages:
            self._pt_worker = asyncio.create_task(self._provisional_translations())

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
        while True:
            try:
                raw = await self.ws.recv()
            except asyncio.CancelledError:
                raise
            except Exception:
                return  # feed() detecta el cierre y reconecta; no es fatal acá.
            try:
                await self.handle(json.loads(raw))
            except asyncio.CancelledError:
                raise
            except Exception as error:
                # Un mensaje que no se pudo procesar no puede matar el lector:
                # eso congelaba los subtítulos con el audio aún fluyendo.
                self._handle_errors += 1
                if self._handle_errors == 1:
                    self.gateway.publish_nowait(self.stream.record_error(
                        'inference_unavailable', f'Gemini Live: {error}', retryable=True))

    async def handle(self, msg: dict):
        activity = msg.get('voiceActivity') or {}
        if activity.get('type') == 'ACTIVITY_START' and 'audioOffset' in activity:
            self.start_ms = self.base_ms + _offset_ms(activity['audioOffset'])
        content = msg.get('serverContent') or {}
        interim = content.get('interimInputTranscription')
        if interim is not None:
            await self._interim(interim.get('text', ''))
        final = content.get('inputTranscription')
        if final is not None:
            await self._final(final.get('text', ''))

    def _after_committed(self, text: str) -> str | None:
        """Texto de la elocución sin el prefijo ya confirmado por cortes.

        None si Gemini reescribió lo confirmado (modo SMART): ese texto ya no
        se puede alinear y no debe volver a publicarse."""
        if not self.committed:
            return text
        if text.startswith(self.committed):
            return text[len(self.committed):]
        return None

    async def _interim(self, text: str):
        effective = self._after_committed(text)
        if effective is None:
            if not self.committed_final:
                return  # reescritura a mitad de elocución: no republicar
            # La elocución anterior cerró y el buffer arrancó de cero.
            self.committed = ''
            self.committed_final = False
            effective = text
        boundaries = list(SENTENCE_SPLIT.finditer(effective))
        if boundaries:
            cut = boundaries[-1].end()
            await self._finalize(effective[:cut])
            self.committed += effective[:cut]
            self.committed_final = False
            effective = effective[cut:]
        # La puntuación de Gemini es confiable: si el texto pendiente ya
        # termina la oración, se confirma ahí mismo, sin esperar a ver el
        # arranque de la siguiente ni la pausa del VAD.
        if ends_sentence(effective):
            await self._finalize(effective)
            self.committed += effective
            self.committed_final = False
            return
        caption = self._publish(effective, final=False)
        if caption is not None:
            self._queue_provisional_translation(caption)

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

    async def _finalize(self, text: str):
        """Confirma el segmento abierto con este texto y dispara su traducción."""
        caption = self._publish(text, final=True)
        if caption is not None and self.stream.session.translation_languages:
            # Como tarea: si el lector esperara acá un lugar en la cola de
            # traducción, un backlog congelaría los subtítulos entrantes.
            task = asyncio.create_task(self._translate_final(caption))
            self._translation_tasks.add(task)
            task.add_done_callback(self._translation_tasks.discard)
        self.open_seq = None
        self.revision = 0
        self.last_text = None
        self.start_ms = None

    async def _translate_final(self, caption):
        try:
            if self.submit_translation is not None:
                await self.submit_translation(caption)
            else:
                await translate_caption(self.stream, self.gateway, caption)
        except asyncio.CancelledError:
            raise
        except Exception as error:
            self.gateway.publish_nowait(self.stream.record_error(
                'inference_unavailable', f'Traducción: {error}', retryable=True))

    def _queue_provisional_translation(self, caption):
        """La traducción también va palabra por palabra: el espectador que lee
        en otro idioma no debería ver el original crecer en un idioma ajeno."""
        if not self.stream.session.translation_languages:
            return
        if os.environ.get('DECILO_PROVISIONAL_TRANSLATION', '1') == '0':
            return
        self._pt_latest = (caption.segment_seq, caption.text)
        self._pt_wake.set()

    async def _provisional_translations(self):
        from decilo.translate import translate

        while True:
            await self._pt_wake.wait()
            self._pt_wake.clear()
            while self._pt_latest is not None:
                seq, text = self._pt_latest
                self._pt_latest = None
                for language in self.stream.session.translation_languages:
                    try:
                        translated = (await translate(text)).strip()
                    except Exception:
                        break  # la traducción de la final va a llegar igual
                    # Sin await entre la consulta y la publicación: la
                    # traducción debe referir a la revisión vigente EXACTA
                    # del original, y una final ya no debe pisarse.
                    original = self.stream.latest_caption(f'seg-{seq}', 'transcript', self.language)
                    if original is None or original.status == 'final' or not translated:
                        continue
                    existing = self.stream.latest_caption(f'seg-{seq}', 'translation', language)
                    if existing is not None and existing.status == 'final':
                        continue
                    self.gateway.publish_nowait(self.stream.upsert_caption(CaptionData(
                        segment_id=f'seg-{seq}', segment_seq=seq,
                        kind='translation', language=language,
                        revision=self.stream.next_caption_revision(f'seg-{seq}', 'translation', language),
                        source_revision=original.revision, text=translated,
                        status='provisional', start_ms=original.start_ms,
                        end_ms=original.end_ms,
                    )))

    async def _final(self, text: str):
        effective = self._after_committed(text)
        if effective is None:
            # SMART reescribió texto que ya confirmamos: lo mejor disponible
            # para la cola es su última provisional.
            self._confirm_open_segment()
        elif not effective.strip():
            if self.open_seq is not None:
                if self.committed:
                    # Hubo cortes: la cola provisional es real, se confirma.
                    self._confirm_open_segment()
                else:
                    # Gemini retiró lo que creyó oír: las provisionales no
                    # pueden quedar como si alguien lo hubiera dicho.
                    self.gaps += 1
                    self.gateway.publish_nowait(self.stream.record_gap(GapData(
                        gap_id=f'gap-live-{self.gaps}', start_ms=self.start_ms or 0,
                        end_ms=self._stream_ms(), reason='processing_error',
                        discard_captions=[{'segment_id': f'seg-{self.open_seq}',
                                          'kind': 'transcript', 'language': self.language}],
                    )))
            self.open_seq = None
            self.revision = 0
            self.last_text = None
            self.start_ms = None
        else:
            await self._finalize(effective)
        # La final oficial define el contenido del buffer: si el interim
        # siguiente lo continúa, todo esto ya está publicado.
        self.committed = text
        self.committed_final = True

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
        self.committed = ''
        self.committed_final = False

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
        if self._pt_worker is not None:
            self._pt_worker.cancel()
            await asyncio.gather(self._pt_worker, return_exceptions=True)
            self._pt_worker = None
        # Terminar de encolar las traducciones finales pendientes antes de
        # cerrar: la cola de traducción de la sesión las drena después.
        if self._translation_tasks:
            await asyncio.gather(*self._translation_tasks, return_exceptions=True)
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
