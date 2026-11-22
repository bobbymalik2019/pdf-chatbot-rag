import test from 'node:test';
import assert from 'node:assert/strict';
import { selectApiUpstream } from '../../src/api-routing.js';
const rag = 'http://127.0.0.1:8000';
const chat = 'http://127.0.0.1:8001';
const id = '96689dbf-2a1a-47ed-8e13-803ead363335';

for (const path of [
  `/api/v1/projects/${id}/conversations`,
  `/api/v1/projects/${id}/conversations?limit=20`,
  `/api/v1/conversations/${id}`,
  `/api/v1/conversations/${id}/`,
  `/api/v1/conversations/${id}/messages`,
  `/api/v1/conversations/${id}/messages?limit=5`,
]) {
  test(`Chat History upstream: ${path}`, () => {
    assert.equal(selectApiUpstream(path, rag, chat), chat);
  });
}
for (const path of [
  '/api/v1/projects', `/api/v1/projects/${id}`,
  '/api/v1/ingestions', '/api/v1/answers',
  `/api/v1/projects/${id}/documents`,
  `/api/v1/projects/${id}/conversations/extra`,
  '/api/v1/conversations',
  `/api/v1/conversations/${id}/messages/extra`,
  '/api/v2/conversations/anything',
]) {
  test(`RAG upstream: ${path}`, () => {
    assert.equal(selectApiUpstream(path, rag, chat), rag);
  });
}
