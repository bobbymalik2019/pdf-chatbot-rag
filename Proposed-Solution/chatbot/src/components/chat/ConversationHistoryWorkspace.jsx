import React, { useCallback, useEffect, useRef, useState } from 'react';
import { chatHistoryApi } from '../../services/chatHistoryApi.js';
import '../../conversation-history.css';

function displayTime(value) {
  if (!value) return '';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? '' : date.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' });
}

function SourceLinks({ sources }) {
  if (!Array.isArray(sources) || sources.length === 0) return null;
  return <div className="history-sources" aria-label="Saved source citations">
    {sources.map((source, index) => {
      if (!source || typeof source !== 'object') return null;
      const file = source.filename || source.document_name || source.file_name || 'PDF source';
      const page = source.page_number ?? source.page ?? source.page_start;
      const marker = source.marker || source.citation_marker;
      return <span className="history-source" key={`${index}-${file}`}>
        {marker ? `${marker} · ` : ''}{file}{page != null ? ` · p. ${page}` : ''}
      </span>;
    })}
  </div>;
}

function Transcript({ messages, busy }) {
  if (busy) return <p className="history-muted" role="status">Loading saved messages…</p>;
  if (!messages.length) return <div className="history-empty"><strong>Ready for your first question</strong><p>Ask anything about documents in this Knowledge Project.</p></div>;
  return <div className="history-transcript" aria-live="polite">
    {messages.map((message) => <article key={message.id} className={`history-message ${message.role === 'user' ? 'history-message-user' : 'history-message-assistant'}`}>
      <span className="history-message-avatar" aria-hidden="true">{message.role === 'user' ? 'Y' : '✦'}</span>
      <div className="history-message-content">
        <div className="history-message-heading"><strong>{message.role === 'user' ? 'You' : 'Assistant'}</strong><time>{displayTime(message.created_at)}</time></div>
        <div className="history-message-text">{message.content}</div>
        {message.status === 'failed' && <span className="history-status">Generation failed</span>}
        <SourceLinks sources={message.sources} />
      </div>
    </article>)}
  </div>;
}

/**
 * Additive workspace wrapper: pass your *existing* chat JSX as children.
 * The existing chat remains untouched; History mode displays persisted messages.
 * projectId MUST be the selected Knowledge Project UUID, not its name.
 */
export default function ConversationHistoryWorkspace({ projectId, children }) {
  const [open, setOpen] = useState(false);
  const [conversations, setConversations] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [busyList, setBusyList] = useState(false);
  const [busyMessages, setBusyMessages] = useState(false);
  const [mutating, setMutating] = useState(false);
  const [error, setError] = useState('');
  const [messageRevision, setMessageRevision] = useState(0);
  const [draft, setDraft] = useState('');
  const [sending, setSending] = useState(false);
  const context = useRef({ projectId, selectedId });
  context.current = { projectId, selectedId };

  useEffect(() => {
    setSelectedId(null);
    setMessages([]);
    setConversations([]);
    setDraft('');
    setError('');
  }, [projectId]);

  useEffect(() => {
    if (!projectId || !open) return;
    const controller = new AbortController();
    setBusyList(true);
    chatHistoryApi.list(projectId, controller.signal)
      .then((data) => { if (!controller.signal.aborted) {
        if (!Array.isArray(data)) throw new Error('Unexpected conversation list response');
        setConversations(data);
      }})
      .catch((err) => { if (!controller.signal.aborted) setError(err.message); })
      .finally(() => { if (!controller.signal.aborted) setBusyList(false); });
    return () => controller.abort();
  }, [projectId, open]);

  useEffect(() => {
    setMessages([]);
    if (!open || !selectedId) return;
    const controller = new AbortController();
    setBusyMessages(true);
    chatHistoryApi.messages(selectedId, controller.signal)
      .then((data) => { if (!controller.signal.aborted) {
        if (!Array.isArray(data)) throw new Error('Unexpected message list response');
        setMessages(data);
      }})
      .catch((err) => { if (!controller.signal.aborted) setError(err.message); })
      .finally(() => { if (!controller.signal.aborted) setBusyMessages(false); });
    return () => controller.abort();
  }, [selectedId, open, messageRevision]);

  async function perform(task) {
    setMutating(true); setError('');
    try { await task(); }
    catch (err) { setError(err.message || 'Action failed'); }
    finally { setMutating(false); }
  }

  function create() {
    if (!projectId) return;
    const title = 'New chat';
    perform(async () => {
      const created = await chatHistoryApi.create(projectId, title.trim());
      if (context.current.projectId !== projectId) return;
      setConversations((prev) => [created, ...prev]);
      setSelectedId(created.id);
    });
  }
  async function sendQuestion(event) {
    event.preventDefault();
    const text = draft.trim();
    if (!projectId || !selectedId || !text || sending) return;
    const projectAtStart = projectId;
    const conversationAtStart = selectedId;
    setSending(true);
    setError('');
    try {
      const exchange = await chatHistoryApi.ask(conversationAtStart, text);
      if (context.current.projectId !== projectAtStart || context.current.selectedId !== conversationAtStart) return;
      setMessages((prev) => [...prev, exchange.user_message, exchange.assistant_message]);
      setDraft('');
      // Refresh title/order from PostgreSQL without overriding user edits.
      chatHistoryApi.list(projectAtStart).then((data) => {
        if (context.current.projectId === projectAtStart && Array.isArray(data)) setConversations(data);
      }).catch(() => {});
    } catch (err) {
      if (context.current.projectId === projectAtStart && context.current.selectedId === conversationAtStart) {
        setError(`${err.message || 'Answer generation failed'}. Refresh messages to see any saved question.`);
        setMessageRevision((n) => n + 1);
        // Keep input text for a deliberate retry; automatic retries could duplicate questions.
      }
    } finally { setSending(false); }
  }

  function rename(conversation) {
    const nextTitle = window.prompt('Rename conversation', conversation.title);
    if (nextTitle === null || nextTitle === conversation.title) return;
    if (!nextTitle.trim()) { setError('Conversation title cannot be blank.'); return; }
    perform(async () => {
      const updated = await chatHistoryApi.rename(conversation.id, nextTitle.trim());
      if (context.current.projectId !== projectId) return;
      setConversations((prev) => prev.map((c) => c.id === conversation.id ? updated : c));
    });
  }
  function remove(conversation) {
    if (!window.confirm(`Delete “${conversation.title}” and its saved messages? This cannot be undone.`)) return;
    perform(async () => {
      await chatHistoryApi.delete(conversation.id);
      if (context.current.projectId !== projectId) return;
      setConversations((prev) => prev.filter((c) => c.id !== conversation.id));
      if (context.current.selectedId === conversation.id) { setSelectedId(null); setMessages([]); }
    });
  }

  const selected = conversations.find((c) => c.id === selectedId);
  const toggle = useCallback(() => setOpen((value) => !value), []);
  return <section className="history-integration" aria-label="Project chat history">
    <div className="history-modebar">
      <button type="button" onClick={toggle} className="history-toggle" aria-expanded={open}>
        <span aria-hidden="true">▤</span> {open ? 'Close history' : 'Conversation history'}
      </button>
      {open && <span className="history-mode-hint">Saved per Knowledge Project</span>}
    </div>
    {!open ? children : <div className="history-layout">
      <aside className="history-list-pane" aria-label="Conversations">
        <div className="history-list-heading"><strong>CONVERSATIONS</strong><span>{conversations.length}</span></div>
        <button type="button" className="history-create" onClick={create} disabled={!projectId || mutating}>＋ New Chat</button>
        {!projectId && <p className="history-muted">Select a Knowledge Project to see its conversations.</p>}
        {busyList && <p className="history-muted" role="status">Loading conversations…</p>}
        {!busyList && projectId && conversations.length === 0 && <p className="history-muted">No conversations for this project yet.</p>}
        <div className="history-list-scroll">
          {conversations.map((conversation) => <div className={`history-item ${selectedId === conversation.id ? 'history-item-active' : ''}`} key={conversation.id}>
            <button className="history-select" type="button" aria-current={selectedId === conversation.id ? 'true' : undefined} onClick={() => { setError(''); setSelectedId(conversation.id); }}>
              <span aria-hidden="true">◯</span>
              <span className="history-item-copy"><strong>{conversation.title}</strong><small>{displayTime(conversation.updated_at || conversation.created_at)}</small></span>
            </button>
            <div className="history-item-actions">
              <button title="Rename" aria-label={`Rename ${conversation.title}`} disabled={mutating} onClick={() => rename(conversation)}>✎</button>
              <button title="Delete" aria-label={`Delete ${conversation.title}`} disabled={mutating} onClick={() => remove(conversation)}>×</button>
            </div>
          </div>)}
        </div>
      </aside>
      <section className="history-reader" aria-label="Saved conversation">
        <header className="history-reader-header">
          <div><strong>{selected?.title || 'Select a conversation'}</strong><small>{selected ? 'Saved conversation history' : 'Choose a conversation on the left'}</small></div>
          {selected && <button type="button" className="history-refresh" onClick={() => setMessageRevision((n) => n + 1)}>Refresh</button>}
        </header>
        {error && <div className="history-error" role="alert">{error} <button onClick={() => setError('')}>Dismiss</button></div>}
        <div className="history-reader-body">
          {selected ? <Transcript messages={messages} busy={busyMessages}/> : <div className="history-empty"><strong>Your conversations, organized by project</strong><p>Select a conversation to view messages saved in PostgreSQL.</p></div>}
        </div>
        <footer className="history-reader-footer">
          {selected ? <form className="history-composer" onSubmit={sendQuestion}>
            <textarea aria-label="Ask about this Knowledge Project" placeholder="Ask a question about documents in this project…" rows={2} maxLength={8000}
              value={draft} onChange={(e) => setDraft(e.target.value)} disabled={sending}
              onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) { e.preventDefault(); e.currentTarget.form.requestSubmit(); } }} />
            <button className="history-create" type="submit" disabled={sending || !draft.trim()}>{sending ? 'Generating…' : 'Send question'}</button>
          </form> : <span>Create or select a conversation to ask questions.</span>}
          <button type="button" onClick={() => setOpen(false)}>Return to chat</button>
        </footer>
      </section>
    </div>}
  </section>;
}
