import test from 'node:test';
import assert from 'node:assert/strict';
import { parseYouTubeId, embedUrl } from '../src/video.js';

test('acepta las formas habituales de link de YouTube', () => {
  const id = 'IW0unWVDnrI';
  for (const value of [
    `https://www.youtube.com/watch?v=${id}`,
    `https://youtube.com/watch?v=${id}&t=42s`,
    `https://youtu.be/${id}`,
    `https://youtu.be/${id}?si=abc123`,
    `https://www.youtube.com/embed/${id}`,
    `https://www.youtube.com/live/${id}`,
    `https://www.youtube.com/shorts/${id}`,
    `www.youtube.com/watch?v=${id}`,
    `  https://www.youtube.com/watch?v=${id}  `,
    id,
  ]) {
    assert.equal(parseYouTubeId(value), id, `debería reconocer ${value}`);
  }
});

test('rechaza lo que no es un video de YouTube en vez de adivinar', () => {
  for (const value of [
    '', '   ', null, undefined, 42,
    'https://example.com/watch?v=IW0unWVDnrI',
    'https://vimeo.com/123456789',
    'https://www.youtube.com/',
    'https://www.youtube.com/watch?v=corto',
    'no es un link',
    // Un host que apenas contiene el nombre no alcanza: cargarlo sería
    // pedirle un embed a un sitio ajeno.
    'https://youtube.com.attacker.test/watch?v=IW0unWVDnrI',
  ]) {
    assert.equal(parseYouTubeId(value), null, `no debería aceptar ${String(value)}`);
  }
});

test('el embed usa el dominio sin cookies', () => {
  assert.equal(embedUrl('IW0unWVDnrI'), 'https://www.youtube-nocookie.com/embed/IW0unWVDnrI');
});
