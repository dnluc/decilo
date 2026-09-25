// Reproduce el audio original de la sesión. La sincronización con los
// subtítulos usa el tiempo del audio (start_ms/end_ms del contrato), no el
// momento en que llegó el evento: un subtítulo puede publicarse bastante
// después del audio que representa.
export function setupPlayer({ onTime }) {
  const panel = document.getElementById('audio-player');
  const audio = document.getElementById('audio');
  const note = document.getElementById('audio-note');
  let sessionId = null;
  let failed = false;

  for (const event of ['timeupdate', 'seeked', 'play', 'pause']) {
    audio.addEventListener(event, () => onTime());
  }
  audio.addEventListener('error', () => {
    if (!sessionId) return; // limpiar el src dispara error; no es una falla real
    failed = true;
    note.textContent = 'No pudimos cargar el audio de esta charla. Los subtítulos siguen disponibles.';
    onTime();
  });

  return {
    // `null` oculta el reproductor (modo muestra, o ninguna sesión elegida).
    load(nextSessionId) {
      audio.pause();
      sessionId = nextSessionId;
      failed = false;
      if (!nextSessionId) {
        audio.removeAttribute('src');
        audio.load();
        panel.hidden = true;
        return;
      }
      note.textContent = 'Escuchá el audio original mientras leés.';
      audio.src = `/api/v1/sessions/${encodeURIComponent(nextSessionId)}/audio`;
      panel.hidden = false;
    },
    // Posición actual en ms, o null si todavía no se reprodujo nada: sin
    // esto, una sesión recién abierta resaltaría el primer subtítulo como
    // si estuviera sonando.
    currentMs() {
      if (!sessionId || failed) return null;
      if (audio.paused && audio.currentTime === 0) return null;
      return audio.currentTime * 1000;
    },
  };
}
