import { readFileSync, writeFileSync, copyFileSync, existsSync } from 'node:fs';
import { resolve } from 'node:path';

const file = resolve('src/server.js');
if (!existsSync(file)) throw new Error('Run from chatbot-gateway root: src/server.js not found');
const oldText = readFileSync(file, 'utf8');
const importLine = "import { selectApiUpstream } from './api-routing.js';";
if (oldText.includes(importLine)) {
  console.log('Already applied: routing helper import exists');
  process.exit(0);
}
const start = oldText.indexOf('function resolveApiUpstream(req) {');
const end = oldText.indexOf('// No express.json()', start);
if (start < 0 || end < 0 || end <= start) {
  throw new Error('Expected resolveApiUpstream function not found; no files changed');
}
const fragment = oldText.slice(start, end);
if (!fragment.includes('isProjectConversation') || !fragment.includes('isConversation') ||
    !fragment.includes('chatHistoryUpstream.origin')) {
  throw new Error('Routing function differs from reviewed server.js; no files changed');
}
if (!oldText.includes("import express from 'express';"))
  throw new Error('Expected ESM import not found; no files changed');
const replacement =
`function resolveApiUpstream(req) {
  return selectApiUpstream(req.originalUrl, upstream.origin, chatHistoryUpstream.origin);
}

`;
const updated = oldText.replace("import express from 'express';",
  "import express from 'express';\n" + importLine)
  .slice(0); // preserve original content other than explicit edits
// Do replacement after import insertion so original offsets are not reused.
const final = updated.replace(fragment, replacement);
if (final === oldText || final.includes('const isProjectConversation ='))
  throw new Error('Unexpected patch result; no files changed');
copyFileSync(file, file + '.before-routing-tests.bak');
writeFileSync(file, final, 'utf8');
console.log('Patched src/server.js; backup: src/server.js.before-routing-tests.bak');
