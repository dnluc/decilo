import './style.css';
import { applyEvent, initialState, visibleCaptions } from './state.js';
import { CaptionConnection, loadSessions } from './connection.js';
import { setupReading } from './reading.js';
import { setupPlayer } from './player.js';

const $ = id => document.getElementById(id);
const demo = new URLSearchParams(location.search).get('demo') === '1';
const statusLabels = { starting: 'Preparando la charla', live: 'En vivo', degraded: 'Con interrupciones', error: 'Sesión no disponible', ended: 'Charla finalizada' };
const languageLabel = code => ({ es: 'Español', en: 'English', pt: 'Português' })[code] || code;
let sessions = [];
let selected = null;
let state = null;
let connection = { kind: 'connecting', message: 'Conectando…' };
let catalogController;
let demoTimers = [];
let demoModule;
let announced = '';
const client = new CaptionConnection({ onUpdate(next, nextConnection) {
  state = next;
  connection = nextConnection;
  if (state.session && state.session !== selected) {
    selected = state.session;
    sessions = sessions.map(s => s.id === selected.id ? selected : s);
    renderSessions();
    updateLanguages();
  }
  render();
} });
// El resaltado se aplica sin volver a dibujar la transcripción: `timeupdate`
// dispara varias veces por segundo y un render completo pelearía con el scroll.
const player = setupPlayer({ onTime: highlightPlaying });
function highlightPlaying() {
  const ms = player.currentMs();
  for (const article of $('transcript').children) {
    const { start, end } = article.dataset;
    if (start === undefined) continue;
    article.classList.toggle('now-playing', ms !== null && ms >= Number(start) && ms < Number(end));
  }
}
function node(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined) element.textContent = text;
  return element;
}
function renderSessions() {
  const focusedIndex = [...$('sessions').children].indexOf(document.activeElement);
  $('sessions').replaceChildren(...sessions.map((session, index) => {
    const button = node('button', `session-card${selected?.id === session.id ? ' selected' : ''}`);
    button.type = 'button';
    button.setAttribute('aria-pressed', String(selected?.id === session.id));
    button.append(node('span', 'session-number', String(index + 1).padStart(2, '0')),
      node('strong', '', session.title), node('span', 'session-meta',
        `${statusLabels[session.status]} · ${languageLabel(session.source_language)}`));
    button.onclick = () => select(session);
    return button;
  }));
  if (focusedIndex >= 0) $('sessions').children[focusedIndex]?.focus({ preventScroll: true });
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
function select(session) {
  demoTimers.forEach(clearTimeout);
  demoTimers = [];
  client.stop();
  selected = session;
  $('focus-reading').disabled = false;
  state = initialState(session.id);
  announced = '';
  $('live-announcement').textContent = '';
  updateLanguages();
  renderSessions();
  // La muestra no tiene audio real: mostrar un reproductor vacío haría creer
  // que se puede escuchar algo que no existe.
  player.load(demo ? null : session.id);
  if (demo) {
    connection = { kind: 'demo', message: 'Muestra · subtítulos simulados' };
    demoModule.demoEvents(session).forEach((event, index) => {
      demoTimers.push(setTimeout(() => {
        state = applyEvent(state, event);
        render();
      }, index * 950));
    });
    render();
  } else client.select(session.id);
}
function timestamp(ms) {
  return `${Math.floor(ms / 60000).toString().padStart(2, '0')}:${Math.floor(ms / 1000 % 60).toString().padStart(2, '0')}`;
}
function render() {
  if (!selected) return;
  $('session-title').textContent = selected.title;
  $('session-status').textContent = `${demo ? 'MUESTRA · ' : ''}${statusLabels[state.session?.status || selected.status]}`;
  $('connection').textContent = connection.message;
  $('connection').dataset.kind = connection.kind;
  const notices = [];
  if (state.restarted) notices.push('La transmisión se reinició. Parte del historial anterior puede no estar disponible.');
  if (state.historyTruncated) notices.push('Mostramos el historial reciente; el comienzo de la charla ya no está disponible.');
  if (state.error) notices.push(state.error.message);
  for (const gap of state.gaps) notices.push(`Interrupción ${gap.start_ms === null ? 'en la charla' : `${timestamp(gap.start_ms)}–${timestamp(gap.end_ms)}`}: ${
    { overload: 'se omitió audio por sobrecarga.', source_disconnect: 'se perdió la fuente de audio.', processing_error: 'no se pudo procesar parte del audio.' }[gap.reason]}`);
  $('notices').replaceChildren(...notices.map(text => node('p', '', text)));
  const language = $('language').value;
  const rows = visibleCaptions(state, language);
  const transcript = $('transcript');
  const scrollTop = transcript.scrollTop;
  transcript.lang = language;
  if (!rows.length) {
    const empty = node('div', 'empty');
    empty.append(node('span', '', '“'), node('p', '', state.session?.status === 'ended' ? 'Esta charla terminó.' : 'Esperando las primeras palabras…'),
      node('small', '', state.awaitingSnapshot ? 'Recuperando los subtítulos de esta sesión.' : 'Los subtítulos aparecerán cuando haya voz.'));
    transcript.replaceChildren(empty);
  } else transcript.replaceChildren(...rows.map(({ segmentId, original, caption }) => {
    const article = node('article', `caption ${caption?.status || 'pending'}`);
    article.dataset.segment = segmentId;
    // Tiempos del original: una traducción conserva los de su original, y el
    // audio que se reproduce es siempre el de la fuente.
    article.dataset.start = String(original.start_ms);
    article.dataset.end = String(original.end_ms);
    const meta = node('div', 'caption-meta', timestamp(original.start_ms));
    if (caption?.speaker_id) meta.append(node('span', '', `Voz ${caption.speaker_id}`));
    meta.append(node('span', '', !caption ? 'Traducción pendiente' : caption.status === 'provisional' ? 'En curso' : 'Confirmado'));
    article.append(meta, node('p', '', caption?.text || 'Esperando traducción…'));
    return article;
  }));
  highlightPlaying(); // el render reemplaza los nodos y con ellos el resaltado
  transcript.scrollTop = $('follow').checked ? transcript.scrollHeight : scrollTop;
  const latest = rows.filter(row => row.caption?.status === 'final').at(-1)?.caption;
  const signature = latest ? `${latest.segment_id}:${latest.language}:${latest.revision}` : '';
  if (signature && signature !== announced) {
    $('live-announcement').textContent = latest.text;
    announced = signature;
  }
}
async function refresh() {
  catalogController?.abort();
  const controller = new AbortController();
  catalogController = controller;
  $('refresh').disabled = true;
  $('catalog-message').textContent = 'Buscando sesiones…';
  const timeout = setTimeout(() => controller.abort(), 10000);
  try {
    sessions = demo ? demoModule.demoSessions : await loadSessions({ signal: controller.signal });
    if (catalogController !== controller) return;
    $('catalog-message').textContent = sessions.length ? `${sessions.length} sesiones disponibles` : 'Todavía no hay sesiones. Volvé a actualizar en un momento.';
    // Do not select silently or replace an active stream on a catalog refresh.
    renderSessions();
  } catch {
    if (catalogController === controller) $('catalog-message').textContent = 'No pudimos cargar las sesiones. Usá Actualizar para reintentar.';
  } finally {
    clearTimeout(timeout);
    if (catalogController === controller) $('refresh').disabled = false;
  }
}
$('language').onchange = render;
$('follow').onchange = () => { if ($('follow').checked) render(); };
$('refresh').onclick = refresh;
$('demo-banner').hidden = !demo;
$('demo-link').hidden = demo;
setupReading();
if (demo) demoModule = await import('./demo.js');
await refresh();
window.addEventListener('pagehide', () => {
  client.stop();
  catalogController?.abort();
  demoTimers.forEach(clearTimeout);
});
