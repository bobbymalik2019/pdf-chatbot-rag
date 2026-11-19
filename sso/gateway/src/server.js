import express from 'express';
import { createProxyMiddleware } from 'http-proxy-middleware';
import { randomUUID } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import { existsSync } from 'node:fs';

const root = path.dirname(fileURLToPath(import.meta.url));
const dist = path.resolve(root, '../../frontend/dist');
const index = path.join(dist, 'index.html');
const port = Number(process.env.PORT || '3100');
const host = process.env.HOST || '127.0.0.1';
const upstream = new URL(process.env.SSO_PYTHON_ORIGIN || 'http://127.0.0.1:8100');
if (
  !['http:', 'https:'].includes(upstream.protocol) ||
  upstream.pathname !== '/' ||
  upstream.username ||
  upstream.password
) {
  throw new Error('SSO_PYTHON_ORIGIN must be an HTTP(S) origin');
}
const app = express();
app.disable('x-powered-by');
app.set('trust proxy', false);
app.use((req, res, next) => {
  req.requestId = randomUUID();
  res.setHeader('X-Content-Type-Options', 'nosniff');
  res.setHeader('Referrer-Policy', 'no-referrer');
  res.setHeader('X-Frame-Options', 'DENY');
  res.setHeader(
    'Content-Security-Policy',
    "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'",
  );
  next();
});

// No JSON body parser before proxy; preserve cookies, JSON, form POSTs, and token responses.
const proxy = createProxyMiddleware({
  target: upstream.origin,
  changeOrigin: true,
  // Express strips mount prefixes; restore complete original path for FastAPI.
  pathRewrite: (_path, req) => req.originalUrl,
  proxyTimeout: 180000,
  timeout: 180000,
  on: {
    proxyReq(proxyReq, req) {
      proxyReq.setHeader('X-Request-ID', req.requestId);
      // No identity headers are trusted from the browser.
      for (const h of ['x-user-id', 'x-user-role', 'x-authenticated-user', 'x-forwarded-user'])
        proxyReq.removeHeader(h);
    },
    proxyRes(proxyRes) {
      proxyRes.headers['cache-control'] = 'no-store';
    },
    error(err, req, res) {
      console.error(
        JSON.stringify({ event: 'sso_upstream_error', requestId: req.requestId, code: err.code }),
      );
      if (res.headersSent) return res.destroy();
      res.writeHead(502, { 'content-type': 'application/json', 'cache-control': 'no-store' });
      res.end(JSON.stringify({ message: 'SSO service unavailable' }));
    },
  },
});
app.use(
  ['/api', '/oauth', '/.well-known', '/healthz'],
  (req, res, next) => {
    res.setHeader('Cache-Control', 'no-store');
    next();
  },
  proxy,
);
app.use(
  express.static(dist, {
    index: false,
    dotfiles: 'deny',
    setHeaders(res, filePath) {
      res.setHeader(
        'Cache-Control',
        filePath.includes(`${path.sep}assets${path.sep}`)
          ? 'public,max-age=31536000,immutable'
          : 'no-store',
      );
    },
  }),
);
app.get(/.*/, (req, res, next) => {
  if (path.extname(req.path) || !req.accepts('html')) return next();
  if (!existsSync(index))
    return res.status(503).json({ message: 'Build the React UI using npm run build' });
  return res.sendFile(index);
});
app.use((_req, res) => res.status(404).json({ message: 'Not found' }));
const server = app.listen(port, host, () =>
  console.log(`SSO UI + gateway: http://${host}:${port} → ${upstream.origin}`),
);
server.requestTimeout = 180000;
server.headersTimeout = 60000;
