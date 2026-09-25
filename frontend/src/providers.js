// Elección de dónde se procesa el audio: en esta máquina o en la nube.
//
// La elección viaja por sesión en el WebSocket de captura, no como un ajuste
// global del servidor: dos capturas simultáneas pueden usar proveedores
// distintos y cambiar acá no altera una sesión que ya está corriendo.

const NOTAS = {
  local: 'Whisper y Gemma corren en esta máquina: el audio no sale de acá, pero la velocidad depende de tu CPU.',
  gemini: 'El audio se envía a Google para transcribir y traducir. Requiere clave configurada en el servidor.',
};

export function setupProviders() {
  const select = document.getElementById('provider');
  const note = document.getElementById('provider-note');
  const cloudOption = select.querySelector('option[value="gemini"]');
  const preferencia = 'decilo.provider';

  const describe = () => { note.textContent = NOTAS[select.value] ?? ''; };

  let eligioAntes = false;
  try {
    const guardada = localStorage.getItem(preferencia);
    if (guardada && NOTAS[guardada]) {
      select.value = guardada;
      eligioAntes = true;
    }
  } catch { /* El almacenamiento puede no estar disponible; sigue funcionando. */ }

  select.addEventListener('change', () => {
    describe();
    try { localStorage.setItem(preferencia, select.value); } catch { /* opcional */ }
  });
  describe();

  // Si el servidor no tiene clave, ofrecer la nube sería una promesa falsa:
  // la captura fallaría recién al intentar conectarse.
  fetch('/api/v1/providers', { cache: 'no-store' })
    .then(response => (response.ok ? response.json() : null))
    .then(info => {
      if (!info) return;
      if (!info.cloud_available) {
        cloudOption.disabled = true;
        cloudOption.textContent = 'En la nube (sin credenciales)';
        if (select.value === 'gemini') {
          select.value = 'local';
          describe();
        }
        note.textContent += ' La nube está deshabilitada: el servidor no tiene GEMINI_API_KEY.';
        return;
      }
      // Sin preferencia propia, se adopta el default del servidor: si el
      // operador configuró la nube es porque es el camino rápido.
      if (!eligioAntes && NOTAS[info.default] && select.value !== info.default) {
        select.value = info.default;
        describe();
      }
    })
    .catch(() => { /* Sin catálogo de proveedores se sigue con el default local. */ });

  return { current: () => select.value };
}
