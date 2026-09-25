// Ritmo de lectura de la barra de subtítulos.
//
// El pipeline puede entregar dos segmentos casi juntos (o una tanda al
// reconectar). Mostrarlos al ritmo en que llegan hace que algunos pasen en
// milisegundos y no se lleguen a leer. Acá cada subtítulo se sostiene un
// tiempo mínimo proporcional a su largo antes de ceder al siguiente.
//
// El historial conserva todo; esta cola solo decide qué se ve en la barra.

export const MIN_HOLD_MS = 1600;
export const MAX_HOLD_MS = 7000;
// ~18 caracteres por segundo es una velocidad de lectura cómoda para
// subtítulos (las guías de la industria usan valores parecidos).
export const MS_PER_CHAR = 1000 / 18;
// Si se acumulan más que esto, la barra se atrasaría demasiado respecto del
// audio: se saltean los intermedios y se va al último. Nada se pierde, todo
// queda en el historial.
export const MAX_PENDING = 3;

export function holdTimeFor(text) {
  return Math.min(MAX_HOLD_MS, Math.max(MIN_HOLD_MS, Math.round(text.length * MS_PER_CHAR)));
}

export function createCaptionPacer({ onShow, now = () => Date.now(), schedule = setTimeout, cancel = clearTimeout }) {
  let pending = [];
  let showing = null; // { key, text, until }
  let timer = null;

  function display(entry) {
    showing = { ...entry, until: now() + holdTimeFor(entry.text) };
    onShow(entry.text);
  }

  function drain() {
    timer = null;
    if (!pending.length) return;
    // Si se acumuló una tanda, saltar a lo último: sostener cada uno haría
    // que la barra quedara hablando del pasado.
    if (pending.length > MAX_PENDING) pending = pending.slice(-1);
    display(pending.shift());
    arm();
  }

  function arm() {
    if (timer || !showing) return;
    const wait = showing.until - now();
    timer = schedule(drain, Math.max(0, wait));
  }

  return {
    // `key` identifica al subtítulo (segmento + idioma). Una revisión del que
    // ya se está mostrando se actualiza en el lugar, sin reiniciar su tiempo:
    // el texto corregido aparece enseguida y no se lo vuelve a encolar.
    push(key, text) {
      if (!text) return;
      if (showing?.key === key) {
        if (showing.text !== text) {
          showing.text = text;
          onShow(text);
        }
        return;
      }
      const queued = pending.findIndex(entry => entry.key === key);
      if (queued >= 0) {
        pending[queued] = { key, text };
        return;
      }
      if (!showing) {
        display({ key, text });
        arm();
        return;
      }
      pending.push({ key, text });
      arm();
    },
    // Al cambiar de sesión no debe quedar nada de la anterior en la barra.
    reset() {
      cancel(timer);
      timer = null;
      pending = [];
      showing = null;
      onShow('');
    },
  };
}
