import { test, expect, request } from '@playwright/test';
import { existsSync } from 'node:fs';
import { randomUUID } from 'node:crypto';

const projectId = process.env.TEST_KNOWLEDGE_PROJECT_ID;
const firstState = 'playwright/.auth/user-a.json';
const secondState = 'playwright/.auth/user-b.json';
const baseURL = process.env.TEST_GATEWAY_URL || 'https://chatbottest.charter26.com';

async function getContext(state) {
  return request.newContext({baseURL, storageState:state, ignoreHTTPSErrors:false});
}
async function readJson(response) {
  const text = await response.text();
  try { return JSON.parse(text); }
  catch { throw new Error(`Unexpected non-JSON response (${response.status()}): ${text.slice(0,250)}`); }
}
async function assertSession(api, label='A') {
  const r = await api.get('/auth/me');
  expect(r.status(), `Session ${label} expired; run npm run auth:${label.toLowerCase()}`).toBe(200);
}
async function createConversation(api, title) {
  const r = await api.post(`/api/v1/projects/${projectId}/conversations`, {
    data: {title}
  });
  const body = await readJson(r);
  expect(r.status(), `POST conversation: ${JSON.stringify(body)}`).toBe(201);
  expect(body.project_id).toBe(projectId);
  expect(body.title).toBe(title);
  expect(body.id).toMatch(/^[a-f0-9-]{36}$/i);
  return body;
}
test('unauthenticated and spoofed-Authorization requests are rejected by the Gateway', async () => {
  const anonymous = await request.newContext({baseURL});
  try {
    const missing = await anonymous.get(`/api/v1/projects/${randomUUID()}/conversations`);
    expect(missing.status()).toBe(401);
    const forged = await anonymous.get(`/api/v1/conversations/${randomUUID()}`, {
      headers:{authorization:'Bearer not-a-real-jwt', 'x-user-id':randomUUID()},
    });
    expect(forged.status()).toBe(401);
    const health = await anonymous.get('/healthz');
    expect(health.status()).toBe(200);
  } finally { await anonymous.dispose(); }
});

test('authenticated RAG routing still works', async () => {
  test.skip(!existsSync(firstState), 'Run npm run auth:a first');
  const a = await getContext(firstState);
  try {
    await assertSession(a);
    const r = await a.get('/api/v1/projects');
    expect(r.status()).toBe(200);
    const body = await readJson(r);
    expect(Array.isArray(body)).toBe(true);
    if (projectId) expect(body.some(p => p.id === projectId)).toBe(true);
  } finally { await a.dispose(); }
});

test('owner creates, lists, renames, adds message, retrieves, deletes', async () => {
  test.skip(!projectId, 'Set TEST_KNOWLEDGE_PROJECT_ID');
  test.skip(!existsSync(firstState), 'Run npm run auth:a first');
  const a = await getContext(firstState);
  let id;
  try {
    await assertSession(a);
    const title = `Gateway E2E ${randomUUID()}`;
    const created = await createConversation(a, title);
    id = created.id;
    const details = await a.get(`/api/v1/conversations/${id}`);
    expect(details.status()).toBe(200);
    expect((await readJson(details)).id).toBe(id);

    const listed = await a.get(`/api/v1/projects/${projectId}/conversations?limit=100`);
    expect(listed.status()).toBe(200);
    expect((await readJson(listed)).some(c=>c.id===id)).toBe(true);

    const renamed = await a.patch(`/api/v1/conversations/${id}`, {
      data:{title:`${title} - Renamed`}
    });
    expect(renamed.status()).toBe(200);
    expect((await readJson(renamed)).title).toBe(`${title} - Renamed`);

    const content = `Test question ${randomUUID()}`;
    const added = await a.post(`/api/v1/conversations/${id}/messages`, {data:{content}});
    const message = await readJson(added);
    expect(added.status(), JSON.stringify(message)).toBe(201);
    expect(message.conversation_id).toBe(id);
    expect(message.role).toBe('user');
    expect(message.content).toBe(content);

    const messages = await a.get(`/api/v1/conversations/${id}/messages`);
    expect(messages.status()).toBe(200);
    const history = await readJson(messages);
    expect(Array.isArray(history)).toBe(true);
    expect(history.some(m => m.id === message.id && m.content === content)).toBe(true);

    const invalid = await a.patch(`/api/v1/conversations/${id}`, {data:{title:'   '}});
    expect(invalid.status()).toBe(422);

    const forgedAssistant = await a.post(`/api/v1/conversations/${id}/messages`, {
      data:{content:'forged', role:'assistant', sources:[{fake:true}]}
    });
    expect(forgedAssistant.status()).toBe(422);

    const deleted = await a.delete(`/api/v1/conversations/${id}`);
    expect(deleted.status()).toBe(204);
    id = null;
    const gone = await a.get(`/api/v1/conversations/${created.id}`);
    expect(gone.status()).toBe(404);
    const goneMessages = await a.get(`/api/v1/conversations/${created.id}/messages`);
    expect(goneMessages.status()).toBe(404);
  } finally {
    if (id) {
      const cleanup = await a.delete(`/api/v1/conversations/${id}`);
      if (cleanup.status() !== 204 && cleanup.status() !== 404) {
        console.error(`Cleanup failed (${cleanup.status()}) for test conversation ${id}`);
      }
    }
    await a.dispose();
  }
});

test('invalid UUID and unauthorized/nonexistent project', async () => {
  test.skip(!existsSync(firstState), 'Run npm run auth:a first');
  const a = await getContext(firstState);
  try {
    await assertSession(a);
    const invalid = await a.get('/api/v1/conversations/not-a-uuid');
    expect(invalid.status()).toBe(422);
    const unavailable = await a.post(`/api/v1/projects/${randomUUID()}/conversations`, {
      data:{title:'Should not exist'}
    });
    expect([403,404]).toContain(unavailable.status());
  } finally { await a.dispose(); }
});

test('second authenticated user cannot read, mutate or delete the first user conversation', async () => {
  test.skip(!projectId, 'Set TEST_KNOWLEDGE_PROJECT_ID');
  test.skip(!existsSync(firstState) || !existsSync(secondState),
    'Capture two different SSO accounts: npm run auth:a and npm run auth:b');
  const a = await getContext(firstState);
  const b = await getContext(secondState);
  let id;
  try {
    await assertSession(a, 'A');
    await assertSession(b, 'B');
    const userA = await readJson(await a.get('/auth/me'));
    const userB = await readJson(await b.get('/auth/me'));
    expect(userA.user.id, 'Use two DIFFERENT SSO user accounts').not.toBe(userB.user.id);

    const conv = await createConversation(a, `Isolation ${randomUUID()}`);
    id = conv.id;
    for (const [method, path, data] of [
      ['get', `/api/v1/conversations/${id}`, undefined],
      ['get', `/api/v1/conversations/${id}/messages`, undefined],
      ['patch', `/api/v1/conversations/${id}`, {title:'Hijacked'}],
      ['post', `/api/v1/conversations/${id}/messages`, {content:'Hijacked'}],
      ['delete', `/api/v1/conversations/${id}`, undefined],
    ]) {
      const result = await b[method](path, data === undefined ? {} : {data});
      expect([403,404], `${method.toUpperCase()} ${path}: cross-user access`).toContain(result.status());
    }
    const stillThere = await a.get(`/api/v1/conversations/${id}`);
    expect(stillThere.status()).toBe(200);
  } finally {
    if (id) {
      const cleanup = await a.delete(`/api/v1/conversations/${id}`);
      if (cleanup.status() !== 204 && cleanup.status() !== 404)
        console.error(`Cleanup failed (${cleanup.status()}) for test conversation ${id}`);
    }
    await a.dispose();
    await b.dispose();
  }
});
