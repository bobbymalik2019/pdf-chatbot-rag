# Folio — React PDF chat workspace

A responsive React + Vite frontend with a restrained sage-and-white design. Includes PDF upload, document session navigation, browser PDF preview, conversations, suggested questions, answer-level feedback, loading/error states, and responsive layouts.

## Run

Requires Node.js 20.19+ or 22.12+.

```sh
npm install
cp .env.example .env
npm run dev
```

Production bundle: `npm run build`. Serve `dist/` through your frontend host.

## Modes and persistence

Default: `VITE_API_MODE=demo`. Demo answers are explicitly labeled placeholders. No document extraction or LLM calls occur in the frontend. Sessions/questions/feedback are stored in localStorage and original PDFs in IndexedDB. Reopening the same browser/origin restores the most recently selected document. Browser data deletion/private browsing can remove demo data. Demo storage is not a secure multi-user database and is not suitable for sensitive production documents.

For your backend:

```env
VITE_API_MODE=live
VITE_API_BASE_URL=/api
```

Restart Vite after changing environment variables. All integration code is isolated in `src/api.js`; map its methods to your existing endpoints instead of changing the UI. Live mode expects synchronous upload completion with `document.status="ready"`. If your backend processes PDFs asynchronously, add polling or SSE in the adapter; currently non-ready documents have chat disabled and must be reopened after processing completes. The frontend does not implement processing-status polling.

## Expected API contract

Dates: ISO 8601. IDs: opaque strings. Error body: `{ "message": "Readable error" }`.

Session shape:

```json
{
  "id": "session-123",
  "title": "Annual report",
  "createdAt": "2026-11-12T00:00:00Z",
  "updatedAt": "2026-11-12T00:00:00Z",
  "document": {
    "id": "doc-123",
    "name": "Annual report.pdf",
    "size": 1048576,
    "status": "ready"
  },
  "messages": []
}
```

- `GET /sessions`: returns `Session[]`, newest updated first. Only authenticated user's sessions.
- `GET /sessions/:id`: returns full `Session`, including messages and saved feedback.
- `POST /sessions`: multipart field `file`; returns full newly created `Session` after the PDF is ready.
- `GET /documents/:id/file`: returns original PDF bytes with `Content-Type: application/pdf`, authorized for the requesting user. Preview uses an iframe; prefer same-origin deployment or a short-lived signed URL returned through a customized `documentUrl()` adapter. Standard iframe navigation cannot attach custom bearer-token headers.
- `POST /sessions/:id/messages`: JSON `{ "content": "Question" }`; persist both question and answer; return `{ "messages": [UserMessage, AssistantMessage], "updatedAt": "ISO date" }`.
- `PUT /sessions/:sessionId/messages/:messageId/feedback`: JSON `{ "rating": 6, "comment": "Missing the key exception." }`; returns `{ "rating": 6, "comment": "Missing the key exception.", "updatedAt": "ISO date" }`. Upsert one feedback record per answer per user.

Message shape:

```json
{
  "id": "message-123",
  "role": "assistant",
  "content": "Plain-text answer from your backend.",
  "createdAt": "2026-11-12T00:00:00Z",
  "citations": [{ "page": 4, "excerpt": "Relevant supporting passage" }],
  "feedback": null
}
```

Saved feedback is `{ "rating": 8, "comment": "", "updatedAt": "ISO date" }`. User messages use `role: "user"`; citations and feedback can be omitted for them. Citation buttons open the PDF preview; navigate manually to the displayed page. This starter uses the browser's native PDF viewer rather than a custom page navigator. Answers render as plain text, not Markdown or executable HTML.

## Feedback rules

The user rates each assistant answer from 1 (worst) through 10 (best). Ratings 1–6 require a non-whitespace comment. Ratings 7–10 allow an optional comment. The user can edit feedback. Both score and comment submit together; no feedback is recorded until Save feedback succeeds. The UI caps comments at 2,000 characters. Enforce all these rules again server-side, including integer bounds and answer ownership.

## Production integration checklist

- The frontend does not implement login. Connect your existing authentication flow. Fetch requests include cookies (`credentials: include`). The backend must derive user identity from its authenticated session, never trust a user ID supplied by the browser, and authorize every document/session/message/feedback access.
- Use an authenticated same-origin API or configure exact allowed origins, secure HttpOnly session cookies, CSRF protection for mutations, and appropriate cookie SameSite settings.
- The client checks extension, non-empty file, and a 25 MB limit for UX only. The backend must validate PDF contents, enforce size limits, scan files as appropriate, reject unsafe uploads, and handle encrypted/unreadable PDFs.
- Store documents in durable protected storage, conversations and feedback in a database, and recover the full session on return. Local demo persistence does not provide cross-device or cross-user recovery.
- Add request idempotency for message creation and uploads before deploying if retries/timeouts could create duplicate records. This starter displays request errors but cannot determine whether a failed network response followed a successful server commit.
- Configure model-response timeouts, rate limits, audit logging, retention/deletion/export controls and user-visible privacy notices. Do not put backend secrets in Vite environment variables.
- Feedback collection does not automatically improve or train an LLM. Your backend needs a separately governed review/evaluation/training pipeline, appropriate permission to reuse the data, and privacy filtering. Treat feedback and document content as untrusted inputs.
- Validate the build and run integration/accessibility/browser tests against your actual API. No backend or build execution was available in the generation environment. Streaming, OCR, authentication UI, custom PDF pagination, session renaming/deletion, automated tests, and automatic feedback training are intentionally not included.

## Project structure

- `src/App.jsx`: workspace, upload, session navigation, messages, feedback form.
- `src/api.js`: live API adapter and isolated local demo persistence.
- `src/styles.css`: responsive styles and reduced-motion support.
