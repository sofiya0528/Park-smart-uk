/**
 * main.js — Park Smart UK shared utilities
 */

// ── Debounce ──────────────────────────────────────────────────────────────────
function debounce(fn, delay = 300) {
  let t;
  return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), delay); };
}

// ── Fetch wrapper with error handling ─────────────────────────────────────────
async function apiFetch(url) {
  try {
    const res = await fetch(url);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error('apiFetch error:', url, err);
    return null;
  }
}

// ── Toast notification ────────────────────────────────────────────────────────
function showToast(message, type = 'success', duration = 3500) {
  let container = document.getElementById('toastContainer');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toastContainer';
    Object.assign(container.style, {
      position: 'fixed', bottom: '20px', right: '20px', zIndex: '9999',
      display: 'flex', flexDirection: 'column', gap: '8px',
    });
    document.body.appendChild(container);
  }
  const toast = document.createElement('div');
  const colours = { success: '#27ae60', error: '#e74c3c', info: '#3498db' };
  Object.assign(toast.style, {
    background: colours[type] || colours.info, color: '#fff',
    padding: '12px 18px', borderRadius: '8px', fontSize: '14px',
    boxShadow: '0 4px 12px rgba(0,0,0,.2)', opacity: '0',
    transition: 'opacity .3s', maxWidth: '300px',
  });
  toast.textContent = message;
  container.appendChild(toast);
  requestAnimationFrame(() => { toast.style.opacity = '1'; });
  setTimeout(() => {
    toast.style.opacity = '0';
    setTimeout(() => toast.remove(), 300);
  }, duration);
}
