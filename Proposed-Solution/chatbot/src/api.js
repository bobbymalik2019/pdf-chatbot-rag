const DEMO = import.meta.env.VITE_API_MODE !== 'live';
const LIVE_INGESTION = import.meta.env.VITE_INGESTION_LIVE === 'true';
const BASE = (import.meta.env.VITE_API_BASE_URL || '/api').replace(/\/$/, '');
export const demoMode = DEMO;
const uid = () => crypto.randomUUID();
const now = () => new Date().toISOString();
const DB = 'folio-demo-v1';
const read = () => JSON.parse(localStorage.getItem(DB) || '[]');
const write = (data) => localStorage.setItem(DB, JSON.stringify(data));
const wait = () => new Promise((resolve) => setTimeout(resolve, 650));





async function request(path, options = {}) {
  const response = await fetch(`${BASE}${path}`, {
    credentials: 'include',
    ...options,
    headers: {
      ...(options.body && !(options.body instanceof FormData)
        ? { 'Content-Type': 'application/json' }
        : {}),
      ...options.headers,
    },
  });
  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const error = await response.json();
      message =error.message || (typeof error.detail === 'string' ? error.detail : null) || message;
    } catch {}
    throw new Error(message);
  }
  return response.status === 204 ? null : response.json();
}
function openDB() {
  return new Promise((resolve, reject) => {
    const r = indexedDB.open('folio-files', 1);
    r.onupgradeneeded = () => r.result.createObjectStore('pdfs');
    r.onsuccess = () => resolve(r.result);
    r.onerror = () => reject(r.error);
  });
}
async function fileStore(id, file) {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction('pdfs', file ? 'readwrite' : 'readonly');
    const r = file
      ? tx.objectStore('pdfs').put(file, id)
      : tx.objectStore('pdfs').get(id);
    let result;
    r.onsuccess = () => {
      result = r.result;
    };
    tx.oncomplete = () => {
      db.close();
      resolve(result);
    };
    tx.onerror = () => {
      db.close();
      reject(tx.error);
    };
  });
}
export const api = {
    async searchProject(projectId, query, topK = 5) {
    return request(
      `/v1/projects/${encodeURIComponent(projectId)}/search`,
      {
        method: 'POST',
        body: JSON.stringify({
          query,
          top_k: topK,
        }),
      }
    );
  },
  async createProject(name) {
    return request('/v1/projects', {
      method: 'POST',
      body: JSON.stringify({
        name,
        description: '',
        tags: []
      })
    });
  },
  async listProjects() {
  return request('/v1/projects');
  },
  async listSessions() {
    return DEMO
      ? read().sort((a, b) => b.updatedAt.localeCompare(a.updatedAt))
      : request('/sessions');
  },
  async listProjectDocuments(projectId) {
    return request(
      `/v1/projects/${encodeURIComponent(projectId)}/documents`
    );
  },
  async getSession(id) {
    const s = DEMO ? read().find((s) => s.id === id) : await request(`/sessions/${id}`);
    if (!s) throw new Error('Session not found');
    return s;
  },
  async upload(file, projectId) {
    
    // Full live mode will be enabled when
    // session APIs are implemented.
    if (!DEMO) {
      const data = new FormData();
      data.append('file', file);
      return request('/sessions', { method: 'POST', body: data });
    }
      let ingestionResult = null;

  // Call the actual Python ingestion service
  // through the Node.js BFF.
  if (LIVE_INGESTION) 
  {

      if (!projectId) 
      {
        throw new Error('Please select a Knowledge Project before uploading a PDF.');
      }

      const data = new FormData();
      data.append('file', file);
      data.append('projectId', projectId);

      ingestionResult = await request('/v1/ingestions', {
        method: 'POST',
        body: data,
      });

      if (ingestionResult.status !== 'EXTRACTED') 
      {
        throw new Error('PDF ingestion was unsuccessful.');
      }
  }else 
  {
    await wait();
  }

  // Keep existing local demo session functionality.
  const id = uid();
  await fileStore(id, file);

  const session = {
    id,
    title: file.name.replace(/\.pdf$/i, ''),
    createdAt: now(),
    updatedAt: now(),
    document: {
      id,
      name: file.name,
      size: file.size,
      status: 'ready',
      pageCount: ingestionResult?.page_count ?? null,
      chunkCount: ingestionResult?.chunks?.length ?? null,
      ingestionStatus: ingestionResult?.status ?? 'DEMO',
    },
    messages: [],
  };
    write([session, ...read()]);
    return session;
  },
  async documentUrl(session) {
    if (!DEMO) return `${BASE}/documents/${session.document.id}/file`;
    const file = await fileStore(session.id);
    if (!file) throw new Error('The locally saved PDF is unavailable. Upload it again.');
    return URL.createObjectURL(file);
  },
  async ask(id, content) {
    if (!DEMO)
      return request(`/sessions/${id}/messages`, {
        method: 'POST',
        body: JSON.stringify({ content }),
      });
    await wait();
    const data = read();
    const s = data.find((s) => s.id === id);
    if (!s) throw new Error('Session not found');
    const user = { id: uid(), role: 'user', content, createdAt: now() };
    const assistant = {
      id: uid(),
      role: 'assistant',
      content: `This is a demonstration response, not an answer extracted from your PDF.\n\nYour question: “${content}”\n\nThe interface has saved this question in your document session. Connect your backend to return a grounded answer and page references here. In live mode, this placeholder is never used.`,
      createdAt: now(),
      citations: [],
      feedback: null,
    };
    s.messages.push(user, assistant);
    s.updatedAt = now();
    write(data);
    return { messages: [user, assistant], updatedAt: s.updatedAt };
  },
  async feedback(sessionId, messageId, rating, comment) {
    if (!DEMO)
      return request(`/sessions/${sessionId}/messages/${messageId}/feedback`, {
        method: 'PUT',
        body: JSON.stringify({ rating, comment }),
      });
    if (rating < 7 && !comment.trim()) throw new Error('Please explain your rating.');
    const data = read();
    const s = data.find((s) => s.id === sessionId);
    const m = s?.messages.find((m) => m.id === messageId);
    if (!m) throw new Error('Answer not found');
    const feedback = { rating, comment: comment.trim(), updatedAt: now() };
    m.feedback = feedback;
    write(data);
    return feedback;
  },
};
