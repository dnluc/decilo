import test from 'node:test';
import assert from 'node:assert/strict';
import { createCaptionPacer, holdTimeFor, MIN_HOLD_MS, MAX_HOLD_MS, MAX_PENDING } from '../src/captions.js';

// Reloj y temporizador controlados: el ritmo se verifica avanzando el tiempo
// a mano, sin esperas reales.
function harness() {
  const shown = [];
  let time = 0;
  let scheduled = null;
  const pacer = createCaptionPacer({
    onShow: text => shown.push(text),
    now: () => time,
    schedule: (fn, delay) => { scheduled = { fn, at: time + delay }; return 1; },
    cancel: () => { scheduled = null; },
  });
  return {
    pacer, shown,
    advance(ms) {
      time += ms;
      // Correr los vencimientos como haría el navegador.
      for (let i = 0; i < 20 && scheduled && scheduled.at <= time; i++) {
        const due = scheduled;
        scheduled = null;
        due.fn();
      }
    },
  };
}

test('el primer subtítulo se muestra enseguida', () => {
  const h = harness();
  h.pacer.push('seg-1:es', 'Hola');
  assert.deepEqual(h.shown, ['Hola']);
});

test('un subtítulo no es reemplazado antes de poder leerlo', () => {
  const h = harness();
  h.pacer.push('seg-1:es', 'Primero');
  h.pacer.push('seg-2:es', 'Segundo');
  // Llegaron casi juntos: el segundo espera.
  assert.deepEqual(h.shown, ['Primero']);
  h.advance(MIN_HOLD_MS - 1);
  assert.deepEqual(h.shown, ['Primero']);
  h.advance(2);
  assert.deepEqual(h.shown, ['Primero', 'Segundo']);
});

test('un texto largo se sostiene más que uno corto', () => {
  assert.equal(holdTimeFor('Hola'), MIN_HOLD_MS);
  const largo = 'a'.repeat(120);
  assert.ok(holdTimeFor(largo) > MIN_HOLD_MS);
  assert.ok(holdTimeFor('a'.repeat(5000)) <= MAX_HOLD_MS);
});

test('una revisión del subtítulo en pantalla se actualiza sin reiniciar su tiempo', () => {
  const h = harness();
  h.pacer.push('seg-1:es', 'Necesitamos otra');
  h.pacer.push('seg-1:es', 'Necesitamos otra revisión de código.');
  assert.deepEqual(h.shown, ['Necesitamos otra', 'Necesitamos otra revisión de código.']);
  // El siguiente segmento sigue esperando su turno, no se adelanta.
  h.pacer.push('seg-2:es', 'Siguiente');
  assert.equal(h.shown.at(-1), 'Necesitamos otra revisión de código.');
});

test('ante una avalancha se salta a lo último en vez de quedar hablando del pasado', () => {
  const h = harness();
  h.pacer.push('seg-1:es', 'Uno');
  for (let i = 2; i <= MAX_PENDING + 3; i++) h.pacer.push(`seg-${i}:es`, `Texto ${i}`);
  h.advance(MAX_HOLD_MS);
  assert.equal(h.shown.at(-1), `Texto ${MAX_PENDING + 3}`);
  // No se mostraron todos los intermedios: quedan en el historial, no en la barra.
  assert.ok(h.shown.length < MAX_PENDING + 3);
});

test('cambiar de sesión limpia la barra y lo que estaba en cola', () => {
  const h = harness();
  h.pacer.push('seg-1:es', 'Vieja sesión');
  h.pacer.push('seg-2:es', 'En cola');
  h.pacer.reset();
  assert.equal(h.shown.at(-1), '');
  h.advance(MAX_HOLD_MS * 2);
  assert.equal(h.shown.at(-1), '', 'nada de la sesión anterior debe aparecer después');
});
