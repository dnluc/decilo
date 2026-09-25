export function setupCapture({ selectSession }) {
  const start = document.getElementById('capture-start');
  const stop = document.getElementById('capture-stop');
  const message = document.getElementById('capture-message');
  let media, context, processor, socket;
  let finishing = false;
  let ready = false;
  let droppedSamples = 0;
  let flush;
  let closeTimer;
  let cleanup;

  function finish(text) {
    if (finishing) return cleanup;
    finishing = true;
    cleanup = (async () => {
    stop.disabled = true;
    if (processor) {
      await Promise.race([new Promise(resolve => { flush = resolve; processor.port.postMessage('stop'); }),
        new Promise(resolve => setTimeout(resolve, 500))]);
      processor.disconnect();
      processor = null;
    }
    media?.getTracks().forEach(track => track.stop());
    media = null;
    await context?.close().catch(() => {});
    context = null;
    if (socket?.readyState === WebSocket.OPEN && ready) {
      socket.send('stop');
      closeTimer = setTimeout(() => socket?.close(), 95000);
    } else socket?.close();
    message.textContent = text;
    if (!socket || socket.readyState === WebSocket.CLOSED) start.disabled = false;
    })();
    return cleanup;
  }

  function startProcessor() {
    if (processor || finishing) return;
    processor = new AudioWorkletNode(context, 'capture-pcm');
    processor.port.onmessage = ({ data }) => {
      if (data.stopped) { flush?.(); return; }
      if (data.dropped) {
        // El worklet tuvo que descartar audio. Decirlo: el backend ve el
        // salto de offset, pero acá se sabe que fue congestión local y no
        // que se cortó la fuente.
        droppedSamples += data.dropped;
        message.textContent = `Capturando audio. Se perdieron ${(droppedSamples / 16000).toFixed(1)}s por congestión; esos tramos quedan marcados como interrupción.`;
        return;
      }
      if (data.packet && socket?.readyState === WebSocket.OPEN) {
        // Con paquetes de 100ms el buffer del socket no debería crecer;
        // si crece, la red no acompaña y es mejor cortar que acumular.
        if (socket.bufferedAmount > 320008) {
          finish('La conexión no alcanza para enviar audio. Captura detenida.');
        } else socket.send(data.packet);
      }
      processor?.port.postMessage('ack');
    };
    const source = context.createMediaStreamSource(new MediaStream(media.getAudioTracks()));
    source.connect(processor);
    const mute = context.createGain();
    mute.gain.value = 0;
    processor.connect(mute).connect(context.destination);
    stop.disabled = false;
    message.textContent = 'Capturando audio. Dale Play al video; Detener libera la captura.';
  }

  function openSocket() {
    const language = document.getElementById('capture-language').value;
    const provider = document.getElementById('provider').value;
    socket = new WebSocket(`${location.protocol === 'https:' ? 'wss:' : 'ws:'}//${location.host}/api/v1/capture?language=${language}&provider=${provider}`);
    // Con idioma automático el backend pide audio ANTES de crear la sesión
    // (necesita escuchar para detectar): el worklet arranca en 'detecting'
    // y la sesión llega después con 'ready'. Con idioma fijo, 'ready' es el
    // primer mensaje y arranca todo junto.
    socket.onmessage = async ({ data }) => {
      try {
        const event = JSON.parse(data);
        if (finishing) return;
        if (event.type === 'detecting') { startProcessor(); return; }
        if (event.type !== 'ready') return;
        ready = true;
        selectSession(event.session);
        startProcessor();
      } catch (error) { await finish(error.message); }
    };
    socket.onclose = async (event) => {
      clearTimeout(closeTimer);
      const failure = event.code === 4408
        ? 'No llegó voz para identificar el idioma. Probá de nuevo o elegilo a mano.'
        : 'No se pudo abrir la captura: revisá el modo demo y el límite de dos sesiones.';
      await finish(ready ? 'Captura terminada. Los subtítulos quedan en la sesión.' : failure);
      if (ready) message.textContent = 'Captura terminada. Los subtítulos quedan en la sesión.';
      start.disabled = false;
    };
    socket.onerror = () => finish('No se pudo conectar la captura al servidor.');
  }

  // Cambiar proveedor o idioma con la captura andando reconecta la sesión
  // sin soltar la pestaña compartida ni pedir permisos de nuevo: se cierra
  // la sesión vieja (drena lo pendiente por su lado) y se abre una nueva
  // con la elección actual. Antes había que recargar la página.
  function restartLive() {
    if (!media || finishing || !socket) return;
    const old = socket;
    socket = null;
    ready = false;
    old.onmessage = null;
    old.onclose = () => clearTimeout(closeTimer);
    old.onerror = null;
    try { if (old.readyState === WebSocket.OPEN) old.send('stop'); else old.close(); } catch { /* ya cerrado */ }
    message.textContent = 'Aplicando el cambio sin cortar la captura…';
    openSocket();
  }
  document.getElementById('provider').addEventListener('change', restartLive);
  document.getElementById('capture-language').addEventListener('change', restartLive);

  start.onclick = async () => {
    start.disabled = true;
    finishing = false;
    droppedSamples = 0;
    ready = false;
    socket = null;
    cleanup = null;
    clearTimeout(closeTimer);
    message.textContent = 'Elegí la pestaña del video y activá Compartir audio.';
    try {
      // Must be invoked directly from the click; permissions cannot be pre-granted.
      media = await navigator.mediaDevices.getDisplayMedia({
        video: { displaySurface: 'browser' }, audio: { suppressLocalAudioPlayback: false },
        preferCurrentTab: true, selfBrowserSurface: 'include', systemAudio: 'exclude',
      });
      if (!media.getAudioTracks().length) throw new Error('No se compartió audio. Elegí una pestaña y activá Compartir audio.');
      context = new AudioContext({ sampleRate: 16000 });
      await context.resume();
      if (context.sampleRate !== 16000) throw new Error('Este navegador no pudo preparar audio a 16 kHz.');
      await context.audioWorklet.addModule('/capture-worklet.js');
      openSocket();
      media.getTracks().forEach(track => track.addEventListener('ended', () => finish('Dejaste de compartir. Terminando el audio pendiente…')));
    } catch (error) {
      await finish(error.name === 'NotAllowedError' ? 'No se autorizó compartir la pestaña.' : error.message);
    }
  };
  stop.onclick = () => finish('Captura detenida. Procesando los últimos segundos…');
  window.addEventListener('pagehide', () => {
    media?.getTracks().forEach(track => track.stop());
    socket?.close();
    context?.close();
  });
}
