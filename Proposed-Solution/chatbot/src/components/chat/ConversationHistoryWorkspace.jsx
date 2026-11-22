import React, { useEffect, useState } from 'react';
import { chatHistoryApi } from '../../services/chatHistoryApi.js';
import '../../conversation-history.css';

function displayTime(value) {
  const date = new Date(value);
  return value && !Number.isNaN(date.getTime())
    ? date.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
    : '';
}

// Conversation navigation stays inside the main workspace.
// The parent App owns the active conversation and the single live chat composer.
export default function ConversationHistoryWorkspace({
  projectId,
  activeConversationId,
  revision = 0,
  busy = false,
  onNewChat,
  onSelectConversation,
  children,
}) {
  const [open, setOpen] = useState(false);
  const [conversations, setConversations] = useState([]);
  const [loading, setLoading] = useState(false);
  const [changing, setChanging] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    setConversations([]);
    setError('');
  }, [projectId]);

  useEffect(() => {
    if (!projectId || !open) return;
    const controller = new AbortController();
    setLoading(true);
    chatHistoryApi.list(projectId, controller.signal)
      .then((data) => {
        if (!controller.signal.aborted) {
          if (!Array.isArray(data)) throw new Error('Unexpected conversations response');
          setConversations(data);
        }
      })
      .catch((err) => { if (!controller.signal.aborted) setError(err.message); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [projectId, open, revision]);

  async function rename(conversation) {
    const title = window.prompt('Rename conversation', conversation.title);
    if (title === null) return;
    if (!title.trim()) { setError('Title cannot be empty.'); return; }
    setChanging(true);
    try {
      const updated = await chatHistoryApi.rename(conversation.id, title.trim());
      setConversations((items) => items.map((item) => item.id === conversation.id ? updated : item));
    } catch (err) { setError(err.message); }
    finally { setChanging(false); }
  }

  async function remove(conversation) {
    if (!window.confirm(`Delete “${conversation.title}” and all its messages?`)) return;
    setChanging(true);
    try {
      await chatHistoryApi.delete(conversation.id);
      setConversations((items) => items.filter((item) => item.id !== conversation.id));
      if (conversation.id === activeConversationId) onNewChat();
    } catch (err) { setError(err.message); }
    finally { setChanging(false); }
  }

  return (
    <section className="history-integration" aria-label="Project chat history">
      <div className="history-modebar">
        <button
          type="button"
          className="history-toggle"
          onClick={() => setOpen((value) => !value)}
          aria-expanded={open}
        >
          <span aria-hidden="true">▤</span> {open ? 'Close history' : 'Conversation history'}
        </button>
        <button
          type="button"
          className="history-create"
          onClick={() => { onNewChat(); setError(''); }}
          disabled={!projectId || changing || busy}
        >
          ＋ New Chat
        </button>
      </div>
      <div className={`history-content ${open ? 'history-layout' : ''}`}>
        {open && (
          <aside className="history-list-pane" aria-label="Conversations">
            <div className="history-list-heading">
              <strong>CONVERSATIONS</strong><span>{conversations.length}</span>
            </div>
            {!projectId && <p className="history-muted">Select a Knowledge Project first.</p>}
            {loading && <p role="status" className="history-muted">Loading conversations…</p>}
            {error && <p role="alert" className="history-error">{error}</p>}
            {!loading && projectId && !conversations.length &&
              <p className="history-muted">No saved conversations yet.</p>}
            <div className="history-list-scroll">
              {conversations.map((conversation) => (
                <div className={`history-item ${activeConversationId === conversation.id ? 'history-item-active' : ''}`} key={conversation.id}>
                  <button
                    type="button"
                    className="history-select"
                    aria-current={activeConversationId === conversation.id ? 'true' : undefined}
                    disabled={busy || changing}
                    onClick={() => onSelectConversation(conversation.id)}
                  >
                    {activeConversationId === conversation.id ? '◉' : '◯'}
                    <span className="history-item-copy">
                      <strong>{conversation.title}</strong>
                      <small>{displayTime(conversation.updated_at || conversation.created_at)}</small>
                    </span>
                  </button>
                  <div className="history-item-actions">
                    <button type="button" disabled={busy || changing} aria-label={`Rename ${conversation.title}`} onClick={() => rename(conversation)}>✎</button>
                    <button type="button" disabled={busy || changing} aria-label={`Delete ${conversation.title}`} onClick={() => remove(conversation)}>×</button>
                  </div>
                </div>
              ))}
            </div>
          </aside>
        )}
        <section className="history-chat-pane" aria-label="Active chat">
          {children}
        </section>
      </div>
    </section>
  );
}
