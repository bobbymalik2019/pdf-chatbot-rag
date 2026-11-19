
import session from 'express-session';
import connectPgSimple from 'connect-pg-simple';
import pg from 'pg';

const { Pool } = pg;
const PgSession = connectPgSimple(session);

//const databaseUrl = process.env.CHATBOT_SESSION_DATABASE_URL;
const sessionSecret = process.env.CHATBOT_SESSION_SECRET;

const idleMinutes = Number(
  process.env.CHATBOT_SESSION_IDLE_MINUTES || 30
);

// if (!databaseUrl) {
//   throw new Error('CHATBOT_SESSION_DATABASE_URL is required');
// }

if (!sessionSecret || sessionSecret.length < 32) {
  throw new Error('CHATBOT_SESSION_SECRET must be at least 32 characters');
}

if (!Number.isInteger(idleMinutes) || idleMinutes < 1) {
  throw new Error('Invalid CHATBOT_SESSION_IDLE_MINUTES');
}

// const pool = new Pool({
//   connectionString: databaseUrl,
//   max: 5,
//   connectionTimeoutMillis: 5000,
//   idleTimeoutMillis: 30000,
// });

const pool = new Pool({
  host: process.env.CHATBOT_DB_HOST,
  port: Number(process.env.CHATBOT_DB_PORT),
  database: process.env.CHATBOT_DB_NAME,
  user: process.env.CHATBOT_DB_USER,
  password: process.env.CHATBOT_DB_PASSWORD,

  max: 5,
  connectionTimeoutMillis: 5000,
  idleTimeoutMillis: 30000,
});

pool.on('error', (error) => {
  console.error('Session PostgreSQL connection error:', error.message);
});

const sessionStore = new PgSession({
  pool,
  schemaName: 'public',
  tableName: 'chatbot_sessions',
  createTableIfMissing: false,
  pruneSessionInterval: 15 * 60,
});

sessionStore.on('error', (error) => {
  console.error('Session store error:', error.message);
});

export const sessionMiddleware = session({
  name: 'chatbot.sid',
  secret: sessionSecret,
  store: sessionStore,

  resave: false,
  saveUninitialized: false,
  rolling: true,

  cookie: {
    httpOnly: true,
    secure: true,
    sameSite: 'lax',
    path: '/',
    maxAge: idleMinutes * 60 * 1000,
  },
});

export { pool as sessionPool };
