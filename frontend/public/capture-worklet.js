// Captura PCM16 mono para el backend.
//
// Paquetes de 100ms (1600 muestras a 16kHz) en vez de 5s: el backend decide
// sus propias ventanas de ASR, y mandarle el audio antes le permite empezar a
// reconocer sin esperar a que se llene un bloque largo. Enviar paquetes
// chicos no implica pedir ASR por cada paquete.
//
// Formato por paquete: offset uint32 LE (posición en muestras desde el inicio
// de la captura) + muestras PCM16 LE. El offset permite al backend detectar
// exactamente qué audio falta si algo se perdió, en vez de suponer.
const FRAME_SAMPLES = 1600;
// Tope de paquetes en vuelo. A 10 paquetes por segundo el ida y vuelta del
// postMessage es despreciable, así que esto solo actúa si el hilo principal
// se traba de verdad. Al llenarse se descarta lo más viejo y se avisa: el
// backend ve el salto de offset y registra el hueco.
const MAX_PENDING = 16;

class CapturePCM extends AudioWorkletProcessor {
  constructor() {
    super();
    this.samples = new Int16Array(FRAME_SAMPLES);
    this.used = 0;
    this.offset = 0;
    this.pending = [];
    this.waiting = false;
    this.port.onmessage = ({ data }) => {
      if (data === 'ack') {
        this.waiting = false;
        this.flush();
      }
      if (data === 'stop') {
        this.pack();      // último fragmento parcial antes de cortar
        this.drain();     // y todo lo que quedó en cola
        this.port.postMessage({ stopped: true });
      }
    };
  }

  // Empaqueta lo acumulado. Nunca descarta en silencio: si no se puede enviar
  // todavía, queda en cola.
  pack() {
    if (!this.used) return;
    const packet = new ArrayBuffer(4 + this.used * 2);
    const view = new DataView(packet);
    view.setUint32(0, this.offset, true);
    for (let i = 0; i < this.used; i++) view.setInt16(4 + i * 2, this.samples[i], true);
    this.pending.push(packet);
    this.offset += this.used;
    this.used = 0;
    if (this.pending.length > MAX_PENDING) {
      // Se pierde audio, pero se dice: el offset del siguiente paquete deja el
      // hueco explícito para el backend.
      const lost = this.pending.shift();
      this.port.postMessage({ dropped: (lost.byteLength - 4) / 2 });
    }
    this.flush();
  }

  flush() {
    if (this.waiting || !this.pending.length) return;
    const packet = this.pending.shift();
    this.port.postMessage({ packet }, [packet]);
    this.waiting = true;
  }

  // Al detener se vacía la cola de una: son pocos paquetes chicos y perderlos
  // acá sería perder el final de la charla.
  drain() {
    for (const packet of this.pending) this.port.postMessage({ packet }, [packet]);
    this.pending = [];
  }

  process(inputs) {
    const channels = inputs[0];
    if (!channels?.length) return true;
    for (let i = 0; i < channels[0].length; i++) {
      let value = 0;
      for (const channel of channels) value += channel[i] / channels.length;
      value = Math.max(-1, Math.min(1, value));
      this.samples[this.used++] = Math.round(value * (value < 0 ? 32768 : 32767));
      if (this.used === FRAME_SAMPLES) this.pack();
    }
    return true;
  }
}
registerProcessor('capture-pcm', CapturePCM);
