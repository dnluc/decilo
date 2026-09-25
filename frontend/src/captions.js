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

// Una hipótesis provisional nueva puede reescribir el comienzo de la anterior
// (la traducción del parcial se rehace entera y cambia palabras ya leídas).
// Para que la barra no "tiemble", solo se avanza: si el texto nuevo extiende
// al mostrado, o trae bastante más contenido, se muestra; una reescritura
// temprana sin contenido nuevo se sostiene hasta que la final decida.
export function stabilized(previous, next) {
  if (!previous || next.startsWith(previous)) return next;
  const prevWords = previous.split(' ');
  const nextWords = next.split(' ');
  let common = 0;
  while (common < prevWords.length && common < nextWords.length
      && prevWords[common] === nextWords[common]) common++;
  const rewritesStart = common < prevWords.length - 2;
  const addsContent = nextWords.length > prevWords.length + 1;
  return rewritesStart && !addsContent ? previous : next;
}

export function createCaptionPacer({ onShow, now = () => Date.now(), schedule = setTimeout, cancel = clearTimeout }) {
  let pending = [];
  let showing = null; // { key, text, until }
  let timer = null;

  function display(entry) {
    showing = { ...entry, until: now() + holdTimeFor(entry.text) };
    onShow(entry.text, entry.state);
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
    push(key, text, state = 'final') {
      if (!text) return;
      if (showing?.key === key) {
        // Crece o se confirma en el lugar, sin reiniciar su tiempo de
        // lectura: así el texto aparece palabra por palabra sin saltos.
        // Entre provisionales, además, sin retroceder.
        const shown = state === 'provisional' && showing.state === 'provisional'
          ? stabilized(showing.text, text) : text;
        if (showing.text !== shown || showing.state !== state) {
          showing.text = shown;
          showing.state = state;
          onShow(shown, state);
        }
        return;
      }
      const queued = pending.findIndex(entry => entry.key === key);
      if (queued >= 0) {
        pending[queued] = { key, text, state };
        return;
      }
      if (!showing) {
        display({ key, text, state });
        arm();
        return;
      }
      pending.push({ key, text, state });
      arm();
    },
    // Al cambiar de sesión no debe quedar nada de la anterior en la barra.
    reset() {
      cancel(timer);
      timer = null;
      pending = [];
      showing = null;
      onShow('', 'final');
    },
  };
}
