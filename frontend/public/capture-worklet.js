class CapturePCM extends AudioWorkletProcessor {
  constructor() {
    super();
    this.samples = new Int16Array(80000);
    this.used = 0;
    this.offset = 0;
    this.waiting = false;
    this.port.onmessage = ({ data }) => {
      if (data === 'ack') this.waiting = false;
      if (data === 'stop') { this.emit(); this.port.postMessage({ stopped: true }); }
    };
  }
  emit() {
    if (!this.used) return;
    if (!this.waiting) {
      const packet = new ArrayBuffer(4 + this.used * 2);
      const view = new DataView(packet);
      view.setUint32(0, this.offset, true);
      for (let i = 0; i < this.used; i++) view.setInt16(4 + i * 2, this.samples[i], true);
      this.port.postMessage({ packet }, [packet]);
      this.waiting = true;
    }
    this.offset += this.used;
    this.used = 0;
  }
  process(inputs) {
    const channels = inputs[0];
    if (!channels?.length) return true;
    for (let i = 0; i < channels[0].length; i++) {
      let value = 0;
      for (const channel of channels) value += channel[i] / channels.length;
      value = Math.max(-1, Math.min(1, value));
      this.samples[this.used++] = Math.round(value * (value < 0 ? 32768 : 32767));
      if (this.used === this.samples.length) this.emit();
    }
    return true;
  }
}
registerProcessor('capture-pcm', CapturePCM);
