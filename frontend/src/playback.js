// Audio playback is local; generation starts only after the first playing event.
export function setupPlayback({ selectRun, currentSession, highlight }) {
  const panel = document.getElementById('playback');
  const audio = document.getElementById('session-audio');
  const button = document.getElementById('start-test');
  const message = document.getElementById('playback-message');
  let generation = 0;
  let session;
  let started = false;
  let pending = false;
  let controller;
  const api = (id, action) => `/api/v1/sessions/${encodeURIComponent(id)}/${action}`;
  async function post(id, action) {
    const response = await fetch(api(id, action), { method: 'POST' });
    const body = await response.json();
    if (!response.ok) throw new Error(typeof body.detail === 'string' ? body.detail : 'No se pudo iniciar la prueba.');
    return body;
  }
  function choose(next, simulated = false) {
    generation++;
    controller?.abort();
    audio.pause();
    audio.removeAttribute('src');
    audio.load();
    session = next;
    started = false;
    pending = false;
    panel.hidden = true;
    button.disabled = false;
    if (!next || simulated) return;
    const token = generation;
    controller = new AbortController();
    fetch(api(next.id, 'audio'), { headers: { Range: 'bytes=0-0' }, signal: controller.signal })
      .then(response => {
        response.body?.cancel();
        if (!response.ok || token !== generation) return;
        panel.hidden = false;
        if (audio.getAttribute('src') === api(next.id, 'audio')) return;
        audio.src = api(next.id, 'audio');
        message.textContent = 'Archivo de prueba. Iniciar prueba genera subtítulos nuevos mientras escuchás. Los controles reproducen el historial; pausar o buscar no detiene el procesamiento.';
      }).catch(() => {});
  }
  button.onclick = async () => {
    if (!session || pending) return;
    const token = generation;
    pending = true;
    button.disabled = true;
    audio.pause();
    try {
      const run = await post(session.id, 'runs');
      if (token !== generation) return;
      selectRun(run);
      // selectRun calls choose; use that new generation to guard asynchronous playback.
      const runToken = generation;
      session = run;
      started = false;
      pending = true;
      button.disabled = true;
      panel.hidden = false;
      audio.src = api(run.id, 'audio');
      audio.currentTime = 0;
      message.textContent = 'Preparando audio…';
      try { await audio.play(); }
      catch {
        if (runToken === generation) {
          pending = false;
          button.disabled = false;
          message.textContent = 'Usá Play en el reproductor para iniciar esta prueba.';
        }
      }
    } catch (error) {
      if (token !== generation) return;
      pending = false;
      button.disabled = false;
      message.textContent = error.message;
    }
  };
  audio.addEventListener('playing', async () => {
    if (started || !session || currentSession()?.id !== session.id) return;
    // An ended/live session is a replay, not a new inference run.
    if (session.status !== 'starting') return;
    started = true;
    const token = generation;
    try {
      await post(session.id, 'start');
      if (token !== generation) return;
      message.textContent = 'Generando subtítulos con el audio en marcha. Pueden llegar con retraso. Pausar o buscar solo cambia la reproducción local.';
    } catch (error) {
      if (token !== generation) return;
      audio.pause();
      started = false;
      message.textContent = error.message;
    } finally {
      if (token === generation) {
        pending = false;
        button.disabled = false;
      }
    }
  });
  audio.addEventListener('error', () => {
    if (!panel.hidden) message.textContent = 'No se pudo reproducir el audio. Podés iniciar otra prueba.';
  });
  audio.addEventListener('timeupdate', () => highlight(audio.currentTime * 1000));
  return { choose, time: () => audio.currentTime * 1000 };
}
