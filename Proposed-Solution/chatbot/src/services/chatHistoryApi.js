// Uses the existing same-origin BFF and its HttpOnly session cookie.
const API = '/api/v1';
async function request(path, options = {}) {
  const response = await fetch(`${API}${path}`, {
    credentials: 'same-origin',
    cache: 'no-store',
    ...options,
    headers: {
      ...(options.body ? { 'Content-Type': 'application/json' } : {}),
      ...options.headers,
    },
  });
  if (response.status === 204) return null;
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    const message = typeof body?.detail === 'string' ? body.detail : `Request failed (${response.status})`;
    const error = new Error(message);
    error.status = response.status;
    throw error;
  }
  return body;
}
const segment = (value) => encodeURIComponent(String(value));
export const chatHistoryApi = {
  list: (projectId, signal) => request(`/projects/${segment(projectId)}/conversations`, { signal }),
  create: (projectId, title) => request(`/projects/${segment(projectId)}/conversations`, {
    method: 'POST', body: JSON.stringify({ title }),
  }),
  ask: (conversationId, content, topK = 5) => request(`/conversations/${segment(conversationId)}/messages`, {
    method: 'POST', body: JSON.stringify({ content, generate_answer: true, top_k: topK }),
  }),
  messages: (conversationId, signal) => request(`/conversations/${segment(conversationId)}/messages`, { signal }),
  rename: (conversationId, title) => request(`/conversations/${segment(conversationId)}`, {
    method: 'PATCH', body: JSON.stringify({ title }),
  }),
  delete: (conversationId) => request(`/conversations/${segment(conversationId)}`, { method: 'DELETE' }),
};
