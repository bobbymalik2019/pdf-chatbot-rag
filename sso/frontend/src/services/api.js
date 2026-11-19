let csrfToken = '';
export async function refreshCsrf() {
  const result = await fetch('/api/v1/auth/csrf', {
    credentials: 'same-origin',
    cache: 'no-store',
  });
  if (!result.ok) throw new Error('Unable to initialize secure form');
  csrfToken = (await result.json()).csrf_token;
}
export async function api(path, { method = 'GET', body } = {}) {
  if (method !== 'GET' && !csrfToken) await refreshCsrf();
  const resp = await fetch(path, {
    method,
    credentials: 'same-origin',
    cache: 'no-store',
    headers: {
      ...(body ? { 'Content-Type': 'application/json' } : {}),
      ...(method !== 'GET' ? { 'X-CSRF-Token': csrfToken } : {}),
    },
    ...(body ? { body: JSON.stringify(body) } : {}),
  });
  if (!resp.ok) {
    const msg = await resp.json().catch(() => ({}));
    throw Object.assign(
      new Error(typeof msg.detail === 'string' ? msg.detail : `Request failed (${resp.status})`),
      { status: resp.status },
    );
  }
  return resp.json();
}
export const authApi = {
  login: (email, password) =>
    api('/api/v1/auth/login', { method: 'POST', body: { email, password } }),
  logout: () => api('/api/v1/auth/logout', { method: 'POST' }),
  me: () => api('/api/v1/auth/me'),
  users: () => api('/api/v1/admin/users'),
  createUser: (payload) => api('/api/v1/admin/users', { method: 'POST', body: payload }),
  changeRoles: (id, roles) =>
    api(`/api/v1/admin/users/${encodeURIComponent(id)}/roles`, { method: 'PUT', body: { roles } }),
};
