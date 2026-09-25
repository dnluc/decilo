import { applyEvent, beginConnection, initialState, ProtocolError, validateCatalog } from './state.js';

export async function loadSessions({ fetcher = fetch, signal } = {}) {
  const response = await fetcher('/api/v1/sessions', { cache: 'no-store', signal });
  if (!response.ok) throw new Error('No pudimos obtener las sesiones. Revisá la conexión e intentá de nuevo.');
  return validateCatalog(await response.json());
}

export class CaptionConnection {
  constructor({ onUpdate, socketFactory = url => new WebSocket(url), origin = globalThis.location?.origin,
    schedule = (fn, delay) => setTimeout(fn, delay), cancel = timer => clearTimeout(timer), random = Math.random }) {
    Object.assign(this, { onUpdate, socketFactory, origin, schedule, cancel, random });
    this.generation = 0;
    this.attempt = 0;
  }
  select(sessionId) {
    this.stop();
    this.state = initialState(sessionId);
    this.attempt = 0;
    this.connect();
  }
  stop() {
    this.generation++;
    this.cancel(this.retryTimer);
    this.cancel(this.snapshotTimer);
    this.socket?.close();
    this.socket = null;
  }
  publish(kind, message) {
    this.onUpdate(this.state, { kind, message });
  }
  connect() {
    const generation = ++this.generation;
    this.state = beginConnection(this.state);
    this.publish('connecting', this.attempt ? 'Reconectando…' : 'Conectando…');
    const url = new URL(`/api/v1/sessions/${encodeURIComponent(this.state.sessionId)}/events`, this.origin);
    url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
    let socket;
    const current = () => this.generation === generation;
    const recover = (message, incompatible = false) => {
      if (!current()) return;
      this.generation++; // Invalidates all callbacks before closing the old socket.
      this.cancel(this.snapshotTimer);
      socket?.close();
      this.socket = null;
      if (incompatible) {
        this.publish('incompatible', message);
        return;
      }
      if (this.state.session?.status === 'ended') {
        this.publish('ended', 'Charla finalizada. Historial disponible.');
        return;
      }
      this.publish('disconnected', message);
      const delay = Math.min(10000, 500 * 2 ** Math.min(this.attempt++, 5)) * (0.8 + this.random() * 0.2);
      this.retryTimer = this.schedule(() => this.connect(), delay);
    };
    try {
      socket = this.socketFactory(url.href);
      this.socket = socket;
    } catch {
      recover('Sin conexión. Vamos a reintentar automáticamente.');
      return;
    }
    this.snapshotTimer = this.schedule(() => recover('No llegó el historial. Reintentando…'), 10000);
    socket.onmessage = ({ data }) => {
      if (!current()) return;
      try {
        if (typeof data !== 'string' || new TextEncoder().encode(data).length > 1024 * 1024) {
          throw new ProtocolError('Mensaje de subtítulos inválido.');
        }
        const next = applyEvent(this.state, JSON.parse(data));
        if (next === this.state) return;
        this.state = next;
        if (!next.awaitingSnapshot) {
          this.cancel(this.snapshotTimer);
          this.publish('connected', 'Conectado');
        }
      } catch (error) {
        recover(error instanceof ProtocolError ? error.message : 'No se pudo leer el subtítulo.', error.incompatible);
      }
    };
    socket.onerror = () => recover('Sin conexión. Vamos a reintentar automáticamente.');
    socket.onclose = event => recover(event.code === 4008
      ? 'La conexión quedó atrás. Recuperando subtítulos recientes…'
      : 'Conexión interrumpida. Recuperando subtítulos…');
  }
}
