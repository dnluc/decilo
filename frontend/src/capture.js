export function setupCapture({ selectSession }) {
  document.getElementById('youtube-load').onclick = event => {
    document.querySelector('#youtube-test iframe').src = 'https://www.youtube-nocookie.com/embed/IW0unWVDnrI';
    // `currentTarget` y no `target`: el botón tiene contenido y un click puede
    // originarse en un hijo, que es lo que se ocultaría con `target`.
    event.currentTarget.hidden = true;
  };
  const start = document.getElementById('capture-start');
  const stop = document.getElementById('capture-stop');
  const message = document.getElementById('capture-message');
  let media, context, processor, socket;
  let finishing = false;
  let ready = false;
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
  start.onclick = async () => {
    start.disabled = true;
    finishing = false;
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
      const language = document.getElementById('capture-language').value;
      socket = new WebSocket(`${location.protocol === 'https:' ? 'wss:' : 'ws:'}//${location.host}/api/v1/capture?language=${language}`);
      socket.onmessage = async ({ data }) => {
        try {
          const event = JSON.parse(data);
          if (event.type !== 'ready' || finishing) return;
          ready = true;
          selectSession(event.session);
          processor = new AudioWorkletNode(context, 'capture-pcm');
          processor.port.onmessage = ({ data }) => {
            if (data.stopped) { flush?.(); return; }
            if (data.packet && socket.readyState === WebSocket.OPEN) {
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
          message.textContent = 'Capturando audio. Dale Play al video. Los subtítulos pueden llegar con retraso; Detener libera la captura.';
        } catch (error) { await finish(error.message); }
      };
      socket.onclose = async () => {
        clearTimeout(closeTimer);
        await finish(ready ? 'Captura terminada. Los subtítulos quedan en la sesión.' : 'No se pudo abrir la captura: revisá el modo demo y el límite de dos sesiones.');
        if (ready) message.textContent = 'Captura terminada. Los subtítulos quedan en la sesión.';
        start.disabled = false;
      };
      socket.onerror = () => finish('No se pudo conectar la captura al servidor.');
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
