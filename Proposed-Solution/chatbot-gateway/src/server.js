import express from 'express';
import { createProxyMiddleware } from 'http-proxy-middleware';
import { randomUUID } from 'node:crypto';
import { existsSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { sessionMiddleware } from './session.js';
import { oidcLogin } from './oidc.js';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const port = Number(process.env.PORT || 3000);
const host = process.env.HOST || '127.0.0.1';
const timeout = Number(process.env.UPSTREAM_TIMEOUT_MS || 180000);
const upstream = new URL(process.env.PYTHON_API_BASE_URL || 'http://127.0.0.1:8000');
if (
  !['http:', 'https:'].includes(upstream.protocol) ||
  upstream.username ||
  upstream.password ||
  upstream.pathname !== '/' ||
  upstream.search ||
  upstream.hash
) {
  throw new Error(
    'PYTHON_API_BASE_URL must be an HTTP(S) origin only; use PYTHON_API_PREFIX for its path.',
  );
}
if (
  !Number.isInteger(port) ||
  port < 1 ||
  port > 65535 ||
  !Number.isInteger(timeout) ||
  timeout < 1000
)
  throw new Error('Invalid PORT or UPSTREAM_TIMEOUT_MS');
const rawPrefix = (process.env.PYTHON_API_PREFIX || '').trim();
if (rawPrefix && !/^\/[A-Za-z0-9_\-/]*$/.test(rawPrefix))
  throw new Error('Invalid PYTHON_API_PREFIX');
const prefix = rawPrefix.replace(/\/+$/, '');
const dist = path.resolve(root, process.env.FRONTEND_DIST || '../chatbot/dist');
const index = path.join(dist, 'index.html');
const app = express();
app.disable('x-powered-by');
app.set('trust proxy', process.env.TRUST_PROXY === 'true' ? 1 : false);

app.use((req, res, next) => {
  req.requestId = randomUUID();
  res.setHeader('X-Request-ID', req.requestId);
  res.setHeader('X-Content-Type-Options', 'nosniff');
  res.setHeader('Referrer-Policy', 'same-origin');
  res.setHeader('X-Frame-Options', 'SAMEORIGIN');
  const start = performance.now();
  res.on('finish', () =>
    console.log(
      JSON.stringify({
        requestId: req.requestId,
        method: req.method,
        status: res.statusCode,
        durationMs: Math.round(performance.now() - start),
      }),
    ),
  );
  next();
});

app.use(sessionMiddleware);

app.get('/healthz', (_req, res) =>
  res.json({ status: 'ok', service: 'chatbot-gateway' }),
);

app.get('/auth/login', oidcLogin);

if (process.env.NODE_ENV === 'development') {
  app.get('/auth/session-test', (req, res) => {
    req.session.testCounter = (req.session.testCounter || 0) + 1;

    res.setHeader('Cache-Control', 'no-store');

    res.json({
      message: 'Session persistence test',
      counter: req.session.testCounter,
    });
  });
}


// No express.json(), multer, or body-reading middleware before this proxy.
// Stream JSON, multipart uploads, PDF bytes and upstream event streams unchanged.
app.use(
  '/api',
  (req, res, next) => {
    res.setHeader('Cache-Control', 'no-store');
    // This gateway does NOT create identities or implement authentication.
    // Python must authenticate every request and authorize every resource.
    next();
  },
  createProxyMiddleware({
    target: upstream.origin,
    changeOrigin: true,
    xfwd: false,
    pathRewrite: (requestPath, req) => {
      console.log('PROXY DEBUG:', {
        originalUrl: req.originalUrl,
        requestPath,
      });

      return `${prefix}${req.originalUrl}`;
    },
    proxyTimeout: timeout,
    timeout,
    on: {
      proxyReq(proxyReq, req) {
        proxyReq.setHeader('X-Request-ID', req.requestId);
        // Never let browser-supplied identity headers impersonate a user.
        for (const name of [
          'x-user-id',
          'x-user-email',
          'x-user-role',
          'x-authenticated-user',
          'x-forwarded-user',
          'x-internal-api-key',
          'forwarded',
          'x-forwarded-for',
          'x-forwarded-host',
          'x-forwarded-proto',
        ])
          proxyReq.removeHeader(name);
        // Authorization and Cookie headers pass through to Python.
        // Do not insert an unscoped shared service key as a substitute for user auth.
      },
      proxyRes(proxyRes) {
        // Prevent upstream responses from enabling shared caches for private PDFs/chat.
        proxyRes.headers['cache-control'] = 'no-store';
      },
      error(error, req, res) {
        console.error(
          JSON.stringify({
            requestId: req.requestId,
            event: 'upstream_error',
            code: error.code || 'UNKNOWN',
          }),
        );
        if (res.headersSent) {
          res.destroy();
          return;
        }
        const timedOut = ['ETIMEDOUT', 'ESOCKETTIMEDOUT'].includes(error.code);
        res.writeHead(timedOut ? 504 : 502, {
          'Content-Type': 'application/json',
          'Cache-Control': 'no-store',
          'X-Request-ID': req.requestId,
        });
        res.end(
          JSON.stringify({
            message: timedOut
              ? 'The Python service took too long to respond. Please check your saved session before retrying.'
              : 'The Python service is unavailable. Please try again later.',
            requestId: req.requestId,
          }),
        );
      },
    },
  }),
);

app.use(
  express.static(dist, {
    index: false,
    dotfiles: 'deny',
    setHeaders(res, filePath) {
      res.setHeader(
        'Cache-Control',
        filePath.includes(`${path.sep}assets${path.sep}`)
          ? 'public, max-age=31536000, immutable'
          : 'no-cache',
      );
    },
  }),
);
// RegExp route works without Express wildcard syntax assumptions.
app.get(/.*/, (req, res, next) => {
  if (path.extname(req.path) || !req.accepts('html')) return next();
  if (!existsSync(index))
    return res
      .status(503)
      .json({
        message:
          'Frontend build not found. Run npm run build in the React project and check FRONTEND_DIST.',
      });
  res.setHeader('Cache-Control', 'no-cache');
  res.sendFile(index);
});
app.use((_req, res) => res.status(404).json({ message: 'Not found' }));
app.use((error, req, res, next) => {
  console.error(
    JSON.stringify({
      event: 'server_error',
      requestId: req.requestId,
      message: error.message,
    }),
  );
  if (res.headersSent) return next(error);
  res.status(500).json({ message: 'Unexpected gateway error', requestId: req.requestId });
});
const server = app.listen(port, host, () => {
  console.log(`chatbot gateway: http://${host}:${port}`);
  console.log(`Python target: ${upstream.origin}${prefix || '/'}; frontend: ${dist}`);
  if (!existsSync(index))
    console.warn(
      'Frontend dist/index.html is missing. API proxy is available; build the React project before opening the UI.',
    );
});
server.requestTimeout = timeout;
server.headersTimeout = 60000;
for (const signal of ['SIGINT', 'SIGTERM'])
  process.on(signal, () => {
    server.close(() => process.exit(0));
    setTimeout(() => {
      server.closeAllConnections();
      process.exit(1);
    }, 10000).unref();
  });
