// Carga del video de YouTube a partir de un link pegado por la persona.

// Acepta las formas habituales: watch?v=, youtu.be/, /embed/, /live/ y
// /shorts/, con o sin parámetros extra. Devuelve null si no hay un id válido
// en vez de adivinar: cargar un video equivocado es peor que no cargar nada.
export function parseYouTubeId(input) {
  if (typeof input !== 'string') return null;
  const value = input.trim();
  if (!value) return null;
  // Un id suelto, pegado sin la URL alrededor.
  if (/^[A-Za-z0-9_-]{11}$/.test(value)) return value;
  let url;
  try {
    url = new URL(value.includes('://') ? value : `https://${value}`);
  } catch {
    return null;
  }
  if (!/(^|\.)(youtube\.com|youtube-nocookie\.com|youtu\.be)$/.test(url.hostname)) return null;
  const fromQuery = url.searchParams.get('v');
  if (fromQuery && /^[A-Za-z0-9_-]{11}$/.test(fromQuery)) return fromQuery;
  const match = url.pathname.match(/^\/(?:embed|live|shorts|v)?\/?([A-Za-z0-9_-]{11})$/);
  return match ? match[1] : null;
}

export function embedUrl(id) {
  return `https://www.youtube-nocookie.com/embed/${id}`;
}

export function setupVideo() {
  const form = document.getElementById('video-form');
  const input = document.getElementById('video-url');
  const frame = document.getElementById('video-frame');
  const iframe = frame.querySelector('iframe');
  const error = document.getElementById('video-error');

  form.addEventListener('submit', event => {
    event.preventDefault();
    const id = parseYouTubeId(input.value);
    if (!id) {
      error.textContent = 'Ese link no parece de YouTube. Pegá la dirección completa del video.';
      input.focus();
      return;
    }
    error.textContent = '';
    iframe.src = embedUrl(id);
    frame.dataset.loaded = 'true';
  });
}
