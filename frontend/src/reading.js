// Reading preferences affect presentation only, never the session connection.
export function setupReading() {
  const size = document.getElementById('text-size');
  const focus = document.getElementById('focus-reading');
  const transcript = document.getElementById('transcript');
  const preferenceKey = 'decilo.text-size';
  const sizes = ['normal', 'large', 'extra'];
  try {
    const saved = localStorage.getItem(preferenceKey);
    if (sizes.includes(saved)) size.value = saved;
  } catch { /* Storage can be unavailable; controls still work for this visit. */ }

  const follow = () => {
    if (document.getElementById('follow').checked) transcript.scrollTop = transcript.scrollHeight;
  };
  const applySize = () => {
    document.body.dataset.textSize = size.value;
    follow();
  };
  applySize();
  size.addEventListener('change', () => {
    applySize();
    try { localStorage.setItem(preferenceKey, size.value); } catch { /* Optional persistence. */ }
  });

  function setFocus(enabled) {
    document.body.classList.toggle('reading-focus', enabled);
    focus.setAttribute('aria-pressed', String(enabled));
    focus.textContent = enabled ? 'Volver a las charlas' : 'Solo subtítulos';
    // Retain keyboard focus on a visible control; Escape always offers a way out.
    focus.focus({ preventScroll: true });
    follow();
    if (enabled) window.scrollTo({ top: 0, behavior: 'instant' });
  }
  focus.addEventListener('click', () => setFocus(focus.getAttribute('aria-pressed') !== 'true'));
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && focus.getAttribute('aria-pressed') === 'true') {
      event.preventDefault();
      setFocus(false);
    }
  });
}
