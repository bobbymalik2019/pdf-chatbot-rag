import React, { useState, useEffect, useRef } from 'react';
import UserMenu from './components/auth/UserMenu';

import {
            FileText,
            Plus,
            Search,
            ArrowUp,
            ArrowRight,
            PanelLeftClose,
            PanelLeftOpen,
            Upload,
            MessageSquare,
            ChevronRight,
            Check,
            Loader2,
            X,
            ExternalLink,
            Star,
            ShieldCheck,
            BookOpen,
            AlertCircle,
          } from 'lucide-react';
import { api, demoMode } from './api';
const prompts = [
                  'Summarize this document',
                  'What are the key takeaways?',
                  'Identify risks and recommendations',
                ];
const dateLabel = (s) =>
  new Date(s).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
function Feedback({ message, sessionId, onSave, onError }) {
  const [open, setOpen] = useState(false),
    [rating, setRating] = useState(message.feedback?.rating || 0),
    [comment, setComment] = useState(message.feedback?.comment || ''),
    [busy, setBusy] = useState(false);
  const required = rating > 0 && rating < 7;
  async function submit(e) {
    e.preventDefault();
    if (!rating || (required && !comment.trim())) return;
    setBusy(true);
    try {
      const f = await api.feedback(sessionId, message.id, rating, comment.trim());
      onSave(f);
      setOpen(false);
    } catch (e) {
      onError(e.message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="feedback">
      <button className="text-button" onClick={() => setOpen(!open)}>
        <Star size={14} />
        {message.feedback
          ? `Rated ${message.feedback.rating}/10 · Edit`
          : 'Rate this answer'}
      </button>
      {open && (
        <form className="rating-panel" onSubmit={submit}>
          <div className="row between">
            <strong>How helpful was this answer?</strong>
            <button
              type="button"
              className="icon"
              aria-label="Close feedback"
              onClick={() => setOpen(false)}
            >
              <X size={15} />
            </button>
          </div>
          <div
            className="scores"
            role="group"
            aria-label="Answer rating, 1 worst to 10 best"
          >
            {Array.from({ length: 10 }, (_, i) => i + 1).map((n) => (
              <button
                type="button"
                key={n}
                aria-label={`Rate ${n} out of 10`}
                aria-pressed={rating === n}
                className={rating === n ? 'selected' : ''}
                onClick={() => setRating(n)}
              >
                {n}
              </button>
            ))}
          </div>
          <div className="row between muted tiny">
            <span>1 — Worst</span>
            <span>10 — Best</span>
          </div>
          <label className="comment-label" htmlFor={`comment-${message.id}`}>
            {required
              ? 'What could be improved? (required)'
              : 'Additional comments (optional)'}
          </label>
          <textarea
            id={`comment-${message.id}`}
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            required={required}
            maxLength={2000}
            placeholder="Tell us what was missing, incorrect, or unclear…"
          />
          <p className="tiny muted">
            Your feedback is recorded for review and may be used to improve answer
            quality.
          </p>
          <button
            className="primary small"
            disabled={busy || !rating || (required && !comment.trim())}
          >
            {busy ? <Loader2 className="spin" size={14} /> : <Check size={14} />} Save
            feedback
          </button>
        </form>
      )}
    </div>
  );
}
export default function App() {
  const [sessions, setSessions] = useState([]),
    [active, setActive] = useState(null),
    [loading, setLoading] = useState(true),
    [uploading, setUploading] = useState(false),
    [sending, setSending] = useState(false),
    [error, setError] = useState(''),
    [query, setQuery] = useState(''),
    [question, setQuestion] = useState(''),
    [sidebar, setSidebar] = useState(true),
    [preview, setPreview] = useState(false),
    [pdfUrl, setPdfUrl] = useState(''),
    [drag, setDrag] = useState(false);

    // Knowledge Projects
    const [projects, setProjects] = useState([]);
    const [projectsLoading, setProjectsLoading] = useState(true);
    const [projectsError, setProjectsError] = useState('');

    const [selectedProjectId, setSelectedProjectId] = useState(null);
    const [creatingProject, setCreatingProject] = useState(false);
    const [newProjectName, setNewProjectName] = useState('');
    const [savingProject, setSavingProject] = useState(false);

    const [projectDocuments, setProjectDocuments] = useState([]);
    const [documentsLoading, setDocumentsLoading] = useState(false);
    const [documentsError, setDocumentsError] = useState('');
    const [documentsExpanded, setDocumentsExpanded] = useState(false);

    const [searchMode, setSearchMode] = useState(false);
    const [searchLoading, setSearchLoading] = useState(false);
    const [searchError, setSearchError] = useState('');
    const [searchResponse, setSearchResponse] = useState(null);

    const searchRequestId = useRef(0);

  const input = useRef(null),bottom = useRef(null),selection = useRef(0),busySend = useRef(false),busyUpload = useRef(false);

  // 1. Load Knowledge Projects
  useEffect(() => {
    let live = true;

    api
      .listProjects()
      .then((data) => {
        if (live) {
          console.log('Knowledge Projects:', data);
          setProjects(data);
        }
      })
      .catch((error) => {
        if (live) setProjectsError(error.message);
      })
      .finally(() => {
        if (live) setProjectsLoading(false);
      });

    return () => {
      live = false;
    };
  }, []);

  // 2. Load Project Documents when a project is selected
    useEffect(() => {
    if (!selectedProjectId) {
      setProjectDocuments([]);
      setDocumentsError('');
      setDocumentsLoading(false);
      return;
    }

    let live = true;

    setProjectDocuments([]);
    setDocumentsLoading(true);
    setDocumentsError('');

    api.listProjectDocuments(selectedProjectId)
      .then((documents) => {
        if (live) setProjectDocuments(documents);
      })
      .catch((error) => {
        if (live) setDocumentsError(error.message);
      })
      .finally(() => {
        if (live) setDocumentsLoading(false);
      });

    return () => {
      live = false;
    };
  }, [selectedProjectId]);

  useEffect(() => {
    let live = true;
    api
      .listSessions()
      .then(async (list) => {
        if (!live) return;
        setSessions(list);
        const last = localStorage.getItem('folio-active');
        const item = list.find((s) => s.id === last) || list[0];
        if (item) {
          const s = await api.getSession(item.id);
          if (live) setActive(s);
        }
      })
      .catch((e) => live && setError(e.message))
      .finally(() => live && setLoading(false));
    return () => {
      live = false;
    };
  }, []);


  useEffect(() => {
    if (active) localStorage.setItem('folio-active', active.id);
  }, [active?.id]);
  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: 'smooth' });
  }, [active?.messages.length, sending]);
  useEffect(() => {
    let disposed = false,
      url = '';
    setPdfUrl('');
    if (preview && active)
      api
        .documentUrl(active)
        .then((u) => {
          url = u;
          if (!disposed) setPdfUrl(u);
          else if (u.startsWith('blob:')) URL.revokeObjectURL(u);
        })
        .catch((e) => !disposed && setError(e.message));
    return () => {
      disposed = true;
      if (url.startsWith('blob:')) URL.revokeObjectURL(url);
    };
  }, [preview, active?.id]);


useEffect(() => {
  ++searchRequestId.current;

  setSearchMode(false);
  setSearchLoading(false);
  setSearchError('');
  setSearchResponse(null);
  setQuery('');
}, [selectedProjectId]);

  async function select(id) {
    const token = ++selection.current;
    setLoading(true);
    setError('');
    setQuestion('');
    setPreview(false);
    try {
      const s = await api.getSession(id);
      if (token === selection.current) setActive(s);
    } catch (e) {
      if (token === selection.current) setError(e.message);
    } finally {
      if (token === selection.current) setLoading(false);
    }
  }



async function performSearch() {
  const searchText = query.trim();

  setSearchMode(true);
  setSearchError('');
  setSearchResponse(null);

  const requestId = ++searchRequestId.current;

  if (!selectedProjectId) {
    setSearchError('Please select a Knowledge Project first.');
    setSearchLoading(false);
    return;
  }

  if (!searchText) {
    setSearchError('Please enter a question.');
    setSearchLoading(false);
    return;
  }

  setSearchLoading(true);

  try {
    const response = await api.answerProject(
      selectedProjectId,
      searchText,
      5
    );

    // Ignore responses from older requests.
    if (requestId !== searchRequestId.current) return;

    setSearchResponse(response);

  } catch (error) {
    if (requestId !== searchRequestId.current) return;

    setSearchError(error.message);

  } finally {
    if (requestId === searchRequestId.current) {
      setSearchLoading(false);
    }
  }
}



 async function createProject() 
 {
    const name = newProjectName.trim();

    if (!name || savingProject) 
      return;

    setSavingProject(true);
    setProjectsError('');

    try 
    {
      const project = await api.createProject(name);
      setProjects(prev => [project, ...prev]);
      setSelectedProjectId(project.id);
      setNewProjectName('');
      setCreatingProject(false);
    } 
    catch (error) 
    {
      setProjectsError(error.message);
    } 
    finally 
    {
      setSavingProject(false);
    }
  } 


  async function upload(file, projectId) 
  {
      if (!file || busyUpload.current) 
        return;
      setError('');
      if (!/\.pdf$/i.test(file.name)) 
      {
        setError('Please choose a PDF document.');
        return;
      }
      if (file.size > 20 * 1024 * 1024) 
      {
        setError('Please choose a PDF smaller than 25 MB.');
        return;
      }
      if (!file.size) 
      {
        setError('This file is empty. Please choose another PDF.');
        return;
      }

      if (!selectedProjectId) 
      {
        setError('Please select a Knowledge Project first.');
        return;
      }


      busyUpload.current = true;
      setUploading(true);
      ++selection.current;
    try {
      const s = await api.upload(file, selectedProjectId); //'97ea2bf0-54fc-4a91-a623-5f6bc987d6c9'
      //const s = await api.upload(file, '97ea2bf0-54fc-4a91-a623-5f6bc987d6c9'); //
      setSessions((prev) => [s, ...prev]);
      setActive(s);
      setQuestion('');
      setPreview(false);
      setLoading(false);
    } catch (e) {
      setError(e.message);
    } finally {
      busyUpload.current = false;
      setUploading(false);
      if (input.current) input.current.value = '';
    }
  }
  async function ask(text = question) {
    if (!active || !text.trim() || busySend.current || active.document.status !== 'ready')
      return;
    busySend.current = true;
    setSending(true);
    setError('');
    const id = active.id;
    const content = text.trim();
    setQuestion('');
    try {
      const result = await api.ask(id, content);
      setActive((s) =>
        s?.id === id
          ? {
              ...s,
              messages: [...s.messages, ...result.messages],
              updatedAt: result.updatedAt,
            }
          : s,
      );
      setSessions((prev) =>
        prev
          .map((s) => (s.id === id ? { ...s, updatedAt: result.updatedAt } : s))
          .sort((a, b) => b.updatedAt.localeCompare(a.updatedAt)),
      );
    } catch (e) {
      setError(e.message);
      setQuestion(content);
    } finally {
      busySend.current = false;
      setSending(false);
    }
  }
  function saveFeedback(id, f) {
    setActive((s) => ({
      ...s,
      messages: s.messages.map((m) => (m.id === id ? { ...m, feedback: f } : m)),
    }));
  }
  return (
    <div className="app">
      <input
        ref={input}
        type="file"
        accept="application/pdf,.pdf"
        hidden
        onChange={(e) => upload(e.target.files?.[0])}
      />
      {sidebar && (
        <aside className="sidebar">
          <a className="brand" href="#" onClick={(e) => e.preventDefault()}>
            <span className="brand-mark">
              <BookOpen size={21} />
            </span>
            chatbot<span className="brand-dot">.</span>
          </a>
          <div className="workspace-label">DOCUMENT WORKSPACE</div>
          <div className="row between section-label">
              <span>KNOWLEDGE PROJECTS</span>
              <button type="button"className="icon"aria-label="Create Knowledge Project" onClick={() => setCreatingProject(true)}><Plus size={17} /></button>
              <span>{projects.length}</span>
          </div>

          {creatingProject && (
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  createProject();
                }}
                style={{ padding: '8px' }}
              >
                <input
                  autoFocus
                  aria-label="New project name"
                  placeholder="Knowledge Project name"
                  value={newProjectName}
                  onChange={(e) => setNewProjectName(e.target.value)}
                  maxLength={150}
                  style={{ width: '100%', padding: '9px' }}
                />

                <div className="row" style={{ marginTop: '8px' }}>
                  <button
                    className="primary small"
                    disabled={!newProjectName.trim() || savingProject}
                  >
                    {savingProject ? 'Creating...' : 'Create'}
                  </button>

                  <button
                    type="button"
                    className="secondary"
                    onClick={() => setCreatingProject(false)}
                  >
                    Cancel
                  </button>
                </div>
              </form>
            )}

            {projectsError && (
              <p className="empty-sidebar" role="alert">
                {projectsError}
              </p>
            )}

          <nav
            className="documents"
            aria-label="Knowledge Projects"
            style={{ flex: '0 1 auto', maxHeight: '35vh' }}
          >
            {projectsLoading && (
              <p className="empty-sidebar">Loading projects...</p>
            )}

            {!projectsLoading && !projectsError && projects.length === 0 && (
              <p className="empty-sidebar">No projects found.</p>
            )}

            {projects.map(project => (
              <button
                type="button"
                key={project.id}
                className={`document ${
                  selectedProjectId === project.id ? 'active' : ''
                }`}
                onClick={() => setSelectedProjectId(project.id)}
                aria-pressed={selectedProjectId === project.id}
              >
                <BookOpen size={19} />

                <span>
                  <strong>{project.name}</strong>
                  <small>{project.description}</small>
                </span>

                {selectedProjectId === project.id && (
                  <Check size={16} />
                )}
              </button>
            ))}
          </nav>
          <button
            className="primary new-doc"
            onClick={() => input.current.click()}
            disabled={uploading}
          >
            <Plus size={17} /> New document{' '}
            {uploading && <Loader2 size={15} className="spin" />}
          </button>
          <form
            className="search"
            onSubmit={(e) => {
              e.preventDefault();
              performSearch();
            }}
            role="search"
          >
            <Search size={16} />

            <input
              type="search"
              aria-label="Search documents"
              placeholder="Search within project…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />

            <button
              type="submit"
              className="search-submit"
              disabled={searchLoading}
              aria-label="Run semantic search"
            >
              {searchLoading ? (
                <Loader2 size={15} className="spin" />
              ) : (
                <ArrowRight size={16} />
              )}
            </button>
          </form>
          <button
            type="button"
            className="row between section-label collapsible-heading"
            onClick={() => setDocumentsExpanded(prev => !prev)}
            aria-expanded={documentsExpanded}
            aria-controls="project-documents-list"
          >
            <span className="row">
              <ChevronRight
                size={16}
                className={documentsExpanded ? 'chevron-expanded' : ''}
              />
              YOUR DOCUMENTS
            </span>

            <span className="document-count">
              {projectDocuments.length}
            </span>
          </button>
          {documentsExpanded && (
           <nav
              id="project-documents-list"
              className="documents project-documents"
              aria-label="Project Documents"
            >
              {!selectedProjectId && (
                <p className="empty-sidebar">
                  Select a Knowledge Project to view its documents.
                </p>
              )}

              {selectedProjectId && documentsLoading && (
                <p className="empty-sidebar">Loading documents...</p>
              )}

              {selectedProjectId && documentsError && (
                <p className="empty-sidebar" role="alert">
                  {documentsError}
                </p>
              )}

              {selectedProjectId &&
                !documentsLoading &&
                !documentsError &&
                projectDocuments.length === 0 && (
                  <p className="empty-sidebar">
                    No documents uploaded yet.
                  </p>
                )}

              {selectedProjectId &&
                !documentsLoading &&
                !documentsError &&
                projectDocuments.map((doc) => (
                  <div className="document" key={doc.id}>
                    <FileText size={19} />

                    <span>
                      <strong>{doc.filename}</strong>
                      <small>
                        {doc.page_count} pages · {doc.status}
                      </small>
                    </span>
                  </div>
                ))}
            </nav>)}


          <div className="sidebar-bottom">
            <div className="row">
              <ShieldCheck size={18} />
              <div>
                <strong>Pick up where you left off</strong>
                <p>{demoMode ? 'Saved in this browser' : 'Document-linked sessions'}</p>
              </div>
            </div>
            <div className="profile">
              <span className="avatar">{demoMode ? 'D' : 'U'}</span>
              <div>
                <strong>{demoMode ? 'Demo workspace' : 'My workspace'}</strong>
                <small>
                  {demoMode ? 'Local preview mode' : 'Connected to your backend'}
                </small>
              </div>
              <span className="online" />
            </div>
          </div>
        </aside>
      )}
      <main className="main">
        <header className="topbar">
          <div className="row">
            <button
              className="icon"
              onClick={() => setSidebar(!sidebar)}
              aria-label={sidebar ? 'Hide sidebar' : 'Show sidebar'}
            >
              {sidebar ? <PanelLeftClose size={19} /> : <PanelLeftOpen size={19} />}
            </button>
            <span className="breadcrumb">Workspace</span>
            <ChevronRight size={14} />
            <span className="current">{active?.title || 'New document'}</span>
          </div>
          <span className="mode-pill">
            <span />
            <UserMenu />
          </span>
        </header>
        {error && (
          <div className="error" role="alert">
            <AlertCircle size={17} />
            <span>{error}</span>
            <button
              className="icon"
              aria-label="Dismiss error"
              onClick={() => setError('')}
            >
              <X size={16} />
            </button>
          </div>
        )}
        {demoMode && (
          <div className="demo-notice">
            Interactive UI demo · Answers are placeholders, not PDF analysis · Data stays
            in this browser.
          </div>
        )}
        <div className="work-area">
          <section className="workspace">
                {searchMode ? (
      <div className="semantic-search-results">
            <div className="search-results-header">
            <div>
              <h1>AI Answer</h1>
              <p>
                {searchResponse
                  ? `Based on ${searchResponse.included_chunks} document passages`
                  : 'Searching your Knowledge Project'}
              </p>
            </div>

            <button
              type="button"
              className="secondary"
              onClick={() => {
                ++searchRequestId.current;
                setSearchMode(false);
                setSearchLoading(false);
                setSearchError('');
                setSearchResponse(null);
              }}
            >
              <X size={15} />
              Back to workspace
            </button>
          </div>

          {searchLoading && (
            <div className="search-status" role="status">
              <Loader2 size={19} className="spin" />
              Retrieving documents and generating your answer...
            </div>
          )}

          {searchError && (
            <p className="search-error" role="alert">
              {searchError}
            </p>
          )}

          {!searchLoading && !searchError && searchResponse && (
            <>
              <article className="search-result-card">
                <div className="search-result-meta">
                  <strong>{searchResponse.question}</strong>
                </div>

                <p
                  className="search-result-text"
                  style={{ whiteSpace: 'pre-wrap' }}
                >
                  {searchResponse.answer}
                </p>
              </article>

              {searchResponse.sources?.length > 0 && (
                <div className="rag-sources">

                  <h2>Sources</h2>

        {searchResponse.sources.map((source) => {
                      const pdfUrl =
                        `/api/v1/projects/${encodeURIComponent(selectedProjectId)}` +
                        `/documents/${encodeURIComponent(source.document_id)}/file` +
                        `#page=${Math.max(1, Number(source.page_number) || 1)}`;

                      return (
                        <a
                          key={source.marker}
                          href={pdfUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="search-result-card citation-link"
                          title={`Open ${source.filename} at page ${source.page_number || 1}`}
                        >
                          <div className="search-result-meta">
                            <div className="search-result-source">
                              <FileText size={17} />
                              <strong>
                                [{source.marker}] {source.filename}
                              </strong>
                            </div>

                            <span>
                              {source.page_number != null
                                ? `Page ${source.page_number}`
                                : 'Page unavailable'}
                            </span>

                            <ExternalLink size={15} />
                          </div>
                        </a>
                      );
                    })}
                  </div>
                )}

              <p className="tiny muted">
                Model: {searchResponse.model || 'Unknown'}
                {' · '}
                {searchResponse.duration_seconds.toFixed(2)} seconds
              </p>
            </>
          )}

        </div>
      ) : loading ? (
              <div className="center-loading">
                <Loader2 className="spin" /> Loading workspace…
              </div>
            ) : !active ? (
              <div className="welcome">
                <span className="eyebrow">LESS SEARCHING. MORE UNDERSTANDING.</span>
                <h1>
                  Your documents.
                  <br />
                  <span>A clearer conversation.</span>
                </h1>
                <p>
                  Turn a PDF into a focused workspace.
                  <br />
                  Ask questions, explore ideas, and keep everything together.
                </p>
                <div
                  className={`dropzone ${drag ? 'drag' : ''}`}
                  onDragOver={(e) => {
                    e.preventDefault();
                    setDrag(true);
                  }}
                  onDragLeave={() => setDrag(false)}
                  onDrop={(e) => {
                    e.preventDefault();
                    setDrag(false);
                    upload(e.dataTransfer.files[0]);
                  }}
                >
                  <span className="upload-icon">
                    {uploading ? <Loader2 className="spin" /> : <Upload />}
                  </span>
                  <h2>{uploading ? 'Creating your workspace…' : 'Drop your PDF here'}</h2>
                  <p>or choose a file to get started</p>
                  <button
                    className="primary"
                    disabled={uploading}
                    onClick={() => input.current.click()}
                  >
                    Choose PDF <ArrowRight size={16} />
                  </button>
                  <small>PDF documents only · Up to 25 MB</small>
                </div>
                <div className="feature-row">
                  <span>
                    <MessageSquare size={15} /> Ask naturally
                  </span>
                  <span>
                    <FileText size={15} /> Document-linked history
                  </span>
                  <span>
                    <Star size={15} /> Share feedback
                  </span>
                </div>
              </div>
            ) : (
              <>
                <div className="document-header">
                  <div className="row">
                    <span className="pdf-badge">
                      <FileText size={23} />
                    </span>
                    <div>
                      <h1>{active.title}</h1>
                      <p>
                        {active.document.name} <span>·</span>{' '}
                        {(active.document.size / 1024 / 1024).toFixed(1)} MB{' '}
                        <span>·</span>{' '}
                        <span className="ready">
                          {active.document.status === 'ready'
                            ? 'Ready to explore'
                            : active.document.status}
                        </span>
                      </p>
                    </div>
                  </div>
                  <button className="secondary" onClick={() => setPreview(!preview)}>
                    <BookOpen size={16} />
                    {preview ? 'Hide PDF' : 'View PDF'}
                  </button>
                </div>
                <div className="chat" aria-live="polite" aria-busy={sending}>
                  {!active.messages.length ? (
                    <div className="chat-intro">
                      <div className="assistant-symbol">
                        <BookOpen size={25} />
                      </div>
                      <h2>A fresh perspective starts with a question.</h2>
                      <p>
                        Ask about the details, get a summary, or explore what matters
                        most.
                      </p>
                      <div className="prompt-grid">
                        {prompts.map((p) => (
                          <button
                            key={p}
                            disabled={sending || active.document.status !== 'ready'}
                            onClick={() => ask(p)}
                          >
                            <MessageSquare size={16} />
                            {p}
                            <ArrowRight size={15} />
                          </button>
                        ))}
                      </div>
                    </div>
                  ) : (
                    active.messages.map((m) => (
                      <article key={m.id} className={`message ${m.role}`}>
                        <div className={`message-avatar ${m.role}`}>
                          {m.role === 'assistant' ? <BookOpen size={17} /> : 'Y'}
                        </div>
                        <div className="message-body">
                          <div className="message-meta">
                            <strong>{m.role === 'assistant' ? 'Foliommm' : 'You'}</strong>
                            <time>
                              {new Date(m.createdAt).toLocaleTimeString([], {
                                hour: '2-digit',
                                minute: '2-digit',
                              })}
                            </time>
                            {m.role === 'assistant' && demoMode && (
                              <span className="demo-tag">Demo answer</span>
                            )}
                          </div>
                          <div className="message-text">{m.content}</div>
                          {m.citations?.length > 0 && (
                            <div className="citations">
                              {m.citations.map((c, i) => (
                                <button
                                  key={i}
                                  className="citation"
                                  onClick={() => {
                                    setPreview(true);
                                  }}
                                  title={
                                    c.excerpt ||
                                    'Open the PDF; navigate to the cited page'
                                  }
                                >
                                  <FileText size={13} /> Page {c.page}
                                </button>
                              ))}
                            </div>
                          )}
                          {m.role === 'assistant' && (
                            <Feedback
                              message={m}
                              sessionId={active.id}
                              onSave={(f) => saveFeedback(m.id, f)}
                              onError={setError}
                            />
                          )}
                        </div>
                      </article>
                    ))
                  )}
                  {sending && (
                    <div className="thinking">
                      <Loader2 size={17} className="spin" /> Looking through your
                      document…
                    </div>
                  )}
                  <div ref={bottom} />
                </div>
                <div className="composer-wrap">
                  <form
                    className="composer"
                    onSubmit={(e) => {
                      e.preventDefault();
                      ask();
                    }}
                  >
                    <textarea
                      aria-label="Question about your document"
                      value={question}
                      onChange={(e) => setQuestion(e.target.value)}
                      onKeyDown={(e) => {
                        if (
                          e.key === 'Enter' &&
                          !e.shiftKey &&
                          !e.nativeEvent.isComposing
                        ) {
                          e.preventDefault();
                          ask();
                        }
                      }}
                      placeholder="Ask anything about this document…"
                      rows={2}
                      maxLength={8000}
                      disabled={sending || active.document.status !== 'ready'}
                    />
                    <div className="row between">
                      <span>
                        <FileText size={13} /> {active.document.name}
                      </span>
                      <button
                        className="send"
                        aria-label="Send question"
                        disabled={
                          sending ||
                          !question.trim() ||
                          active.document.status !== 'ready'
                        }
                      >
                        {sending ? (
                          <Loader2 size={18} className="spin" />
                        ) : (
                          <ArrowUp size={19} />
                        )}
                      </button>
                    </div>
                  </form>
                  <p className="composer-note">
                    {demoMode
                      ? 'Demo answers are illustrative only.'
                      : 'AI-generated answers can be inaccurate. Verify important details against the PDF.'}{' '}
                    <span>Enter to send · Shift + Enter for a new line</span>
                  </p>
                </div>
              </>
            )}
          </section>
          {preview && active && (
            <aside className="pdf-panel">
              <div className="row between">
                <strong>Document preview</strong>
                <div className="row">
                  {pdfUrl && (
                    <a
                      className="icon"
                      href={pdfUrl}
                      target="_blank"
                      rel="noreferrer"
                      aria-label="Open PDF in new tab"
                    >
                      <ExternalLink size={16} />
                    </a>
                  )}
                  <button
                    className="icon"
                    aria-label="Close preview"
                    onClick={() => setPreview(false)}
                  >
                    <X size={18} />
                  </button>
                </div>
              </div>
              {pdfUrl ? (
                <iframe title={`PDF preview: ${active.document.name}`} src={pdfUrl} />
              ) : (
                <div className="center-loading">
                  <Loader2 className="spin" /> Loading PDF…
                </div>
              )}
            </aside>
          )}
        </div>
      </main>
    </div>
  );
}
