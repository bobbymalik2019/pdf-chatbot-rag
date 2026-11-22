'use strict';
// Invoke from Proposed-Solution/chatbot-gateway:
// node --env-file=.env <path-to>/diagnose.cjs env|db|sessions|fingerprint
const crypto = require('node:crypto');
const mode = process.argv[2];
const config = {
  host: process.env.CHATBOT_DB_HOST,
  port: Number(process.env.CHATBOT_DB_PORT),
  database: process.env.CHATBOT_DB_NAME,
  user: process.env.CHATBOT_DB_USER,
  password: process.env.CHATBOT_DB_PASSWORD,
};
function missingFields() {
  return ['host', 'port', 'database', 'user', 'password'].filter(k => !config[k] || (k === 'port' && !Number.isInteger(config[k])));
}
async function main() {
  if (mode === 'env') {
    console.log(JSON.stringify({
      host: config.host || null,
      port: Number.isInteger(config.port) ? config.port : null,
      database: config.database || null,
      user: config.user || null,
      passwordConfigured: Boolean(config.password),
      passwordLength: config.password ? [...config.password].length : 0
    }, null, 2));
    return;
  }
  if (mode === 'fingerprint') {
    if (!config.password) throw new Error('CHATBOT_DB_PASSWORD is not configured');
    // Intentionally ONLY for local consumption by Compare-DbPassword.ps1. Do not share output.
    process.stdout.write(JSON.stringify({
      length: [...config.password].length,
      sha256: crypto.createHash('sha256').update(config.password, 'utf8').digest('hex')
    }));
    return;
  }
  if (mode !== 'db' && mode !== 'sessions') {
    throw new Error('Choose one command: env, db, sessions, fingerprint');
  }
  const missing = missingFields();
  if (missing.length) throw new Error('Missing or invalid database settings: ' + missing.join(', '));
  const { Pool } = require('pg');
  const pool = new Pool({ ...config, max: 1, connectionTimeoutMillis: 5000 });
  try {
    if (mode === 'db') {
      const r = await pool.query('SELECT current_user AS db_user, current_database() AS db_name');
      console.log('CONNECTED', JSON.stringify(r.rows[0]));
    } else {
      const r = await pool.query(`
        SELECT count(*)::int AS total_sessions,
               count(*) FILTER (WHERE sess::jsonb ? 'oidcTransaction')::int AS oidc_transactions,
               count(*) FILTER (WHERE expire > NOW())::int AS unexpired_sessions
          FROM public.chatbot_sessions`);
      console.log('SESSION SUMMARY', JSON.stringify(r.rows[0]));
    }
  } catch (err) {
    console.error('DATABASE ERROR:', err.code || 'UNKNOWN', err.message);
    process.exitCode = 1;
  } finally {
    await pool.end();
  }
}
main().catch(e => { console.error('ERROR:', e.message); process.exitCode = 1; });
