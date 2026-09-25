import './style.css';
import { applyEvent, initialState, visibleCaptions } from './state.js';
import { CaptionConnection } from './connection.js';
import { setupReading } from './reading.js';
import { setupCapture } from './capture.js';
import { setupVideo } from './video.js';
import { createCaptionPacer } from './captions.js';

const $ = id => document.getElementById(id);
const languageLabel = code => ({ es: 'Español', en: 'English', pt: 'Português' })[code] || code;
let selected = null;
let state = null;
let connection = { kind: 'idle', message: 'Esperando el audio de la charla.' };
let announced = '';

// La barra sostiene cada subtítulo un tiempo mínimo de lectura: el pipeline
// puede entregar dos casi juntos y de otro modo alguno pasaría en milisegundos.
const pacer = createCaptionPacer({
  onShow(text) {
    const live = $('live-caption');
    live.textContent = text;
    live.dataset.empty = text ? 'false' : 'true';
  },
});

const client = new CaptionConnection({ onUpdate(next, nextConnection) {
  state = next;
  connection = nextConnection;
  if (state.session && state.session !== selected) {
    selected = state.session;
    updateLanguages();
  }
  render();
} });

function node(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined) element.textContent = text;
  return element;
}

function updateLanguages() {
  const languages = [selected.source_language, ...selected.translation_languages];
  const previous = $('language').value;
  $('language').replaceChildren(...languages.map(code => {
    const option = node('option', '', languageLabel(code));
    option.value = code;
    return option;
  }));
  $('language').value = languages.includes(previous) ? previous : languages.includes('es') ? 'es' : languages[0];
  $('language').disabled = false;
}

// Una sesión nueva empieza de cero: nada de la anterior debe quedar visible.
function useSession(session) {
  client.stop();
  pacer.reset();
  selected = session;
  state = initialState(session.id);
  announced = '';
  $('live-announcement').textContent = '';
  $('focus-reading').disabled = false;
  updateLanguages();
  client.select(session.id);
  render();
}

function timestamp(ms) {
  return `${Math.floor(ms / 60000).toString().padStart(2, '0')}:${Math.floor(ms / 1000 % 60).toString().padStart(2, '0')}`;
}

const gapReason = {
  overload: 'se omitió audio por sobrecarga.',
  source_disconnect: 'se perdió la fuente de audio.',
  processing_error: 'no se pudo procesar parte del audio.',
};

function render() {
  if (!state) return;
  $('connection').textContent = connection.message;
  $('connection').dataset.kind = connection.kind;

  const notices = [];
  if (state.restarted) notices.push('La transmisión se reinició. Parte del historial anterior puede no estar disponible.');
  if (state.historyTruncated) notices.push('Mostramos el historial reciente; el comienzo de la charla ya no está disponible.');
  if (state.error) notices.push(state.error.message);
  for (const gap of state.gaps) {
    notices.push(`Interrupción ${gap.start_ms === null ? 'en la charla' : `${timestamp(gap.start_ms)}–${timestamp(gap.end_ms)}`}: ${gapReason[gap.reason]}`);
  }
  $('notices').replaceChildren(...notices.map(text => node('p', '', text)));

  const language = $('language').value;
  const rows = visibleCaptions(state, language);
  const log = $('transcript');
  const scrollTop = log.scrollTop;
  log.lang = language;

  if (!rows.length) {
    log.replaceChildren(node('p', 'chat-empty', 'Todo lo que se diga va a quedar acá, de principio a fin.'));
  } else {
    log.replaceChildren(...rows.map(({ segmentId, original, caption }, index) => {
      const turn = node('div', `turn ${caption?.status || 'pending'}${index === rows.length - 1 ? ' current' : ''}`);
      turn.dataset.segment = segmentId;
      turn.append(node('span', 'turn-time', timestamp(original.start_ms)),
        node('p', '', caption?.text || 'Traduciendo…'));
      return turn;
    }));
  }
  log.scrollTop = $('follow').checked ? log.scrollHeight : scrollTop;
  $('chat-count').textContent = rows.length ? `${rows.length} ${rows.length === 1 ? 'intervención' : 'intervenciones'}` : '';

  // El último subtítulo va a la barra a través del marcador de ritmo, que
  // decide cuándo mostrarlo; acá no se escribe la barra directamente.
  const last = rows.at(-1);
  if (last?.caption) pacer.push(`${last.segmentId}:${last.caption.language}`, last.caption.text);

  const latest = rows.filter(row => row.caption?.status === 'final').at(-1)?.caption;
  const signature = latest ? `${latest.segment_id}:${latest.language}:${latest.revision}` : '';
  if (signature && signature !== announced) {
    $('live-announcement').textContent = latest.text;
    announced = signature;
  }
}

// `?session=<id>` reengancha una sesión ya existente: si se recarga la página
// en medio de una charla, el historial se recupera sin volver a capturar.
async function attachRequestedSession() {
  const id = new URLSearchParams(location.search).get('session');
  if (!id) return;
  try {
    const response = await fetch(`/api/v1/sessions/${encodeURIComponent(id)}`, { cache: 'no-store' });
    if (!response.ok) throw new Error('no disponible');
    useSession(await response.json());
  } catch {
    $('connection').textContent = 'No encontramos esa charla. Compartí el audio para empezar una nueva.';
  }
}

$('language').onchange = render;
$('follow').onchange = () => { if ($('follow').checked) render(); };
setupReading();
setupVideo();
setupCapture({ selectSession: useSession });
window.addEventListener('pagehide', () => client.stop());
await attachRequestedSession();
