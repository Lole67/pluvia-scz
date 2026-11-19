'use strict';
// The API owns authentication. Browser state never determines access rights.
window.PluviaSession = {
  async request(url, options = {}) {
    const token = sessionStorage.getItem('pluvia-token');
    let response;
    try { response = await fetch(url, {...options, headers: {
      ...options.headers, ...(token ? {Authorization: `Bearer ${token}`} : {})
    }}); } catch (_) { throw Error('No se pudo conectar con el servidor local. Comprueba que siga abierto.'); }
    let data = null;
    if (response.status !== 204) {
      try { data = await response.json(); } catch (_) { data = {error: 'Respuesta no válida del servidor.'}; }
    }
    if (response.status === 401 && url !== '/api/auth/login') {
      sessionStorage.removeItem('pluvia-token');
      location.replace('/login');
    }
    if (!response.ok) throw Error(data?.error || `Error HTTP ${response.status}`);
    return data;
  },
  async requireUser() {
    if (!sessionStorage.getItem('pluvia-token')) { location.replace('/login'); throw Error('Inicia sesión.'); }
    const user = await this.request('/api/auth/me');
    const identity = document.getElementById('identity');
    if (identity) identity.textContent = `${user.name} · ${user.role === 'admin' ? 'Administrador' : 'Cliente'}`;
    const admin = document.getElementById('admin-link');
    if (admin) admin.hidden = user.role !== 'admin';
    const history = document.getElementById('history-label');
    if (history) history.textContent = 'Consultar resultados';
    return user;
  },
  async logout() {
    try { await this.request('/api/auth/logout', {method:'POST'}); }
    finally { sessionStorage.removeItem('pluvia-token'); location.replace('/login'); }
  }
};
document.getElementById('logout')?.addEventListener('click', () => PluviaSession.logout());
