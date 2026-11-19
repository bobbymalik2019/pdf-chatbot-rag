
-- ============================================================
-- RAG CHATBOT DATABASE SCHEMA
-- Version: 1.0
-- Database: rag_db
-- PostgreSQL: 17
-- Vector extension: pgvector
-- Embedding model: nomic-embed-text
-- Embedding dimensions: 768
-- ============================================================

BEGIN;

-- Enable vector support
CREATE EXTENSION IF NOT EXISTS vector;


-- ============================================================
-- 1. APPLICATION USERS
-- ============================================================

CREATE TABLE app_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    external_user_id VARCHAR(255) UNIQUE,
    display_name VARCHAR(255),

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- ============================================================
-- 2. KNOWLEDGE PROJECTS
-- ============================================================

CREATE TABLE knowledge_projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    owner_id UUID NOT NULL
        REFERENCES app_users(id),

    name VARCHAR(255) NOT NULL,
    description TEXT,

    tags TEXT[] NOT NULL DEFAULT '{}',

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_project_owner_name
        UNIQUE (owner_id, name)
);


-- ============================================================
-- 3. DOCUMENTS
-- ============================================================

CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    project_id UUID NOT NULL
        REFERENCES knowledge_projects(id),

    filename VARCHAR(255) NOT NULL,

    page_count INTEGER NOT NULL DEFAULT 0
        CHECK (page_count >= 0),

    status VARCHAR(30) NOT NULL DEFAULT 'PENDING'
        CHECK (
            status IN (
                'PENDING',
                'PROCESSING',
                'READY',
                'FAILED'
            )
        ),

    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- ============================================================
-- 4. DOCUMENT CHUNKS
-- ============================================================

CREATE TABLE document_chunks (
    id BIGSERIAL PRIMARY KEY,

    document_id UUID NOT NULL
        REFERENCES documents(id)
        ON DELETE CASCADE,

    chunk_index INTEGER NOT NULL
        CHECK (chunk_index >= 0),

    text TEXT NOT NULL
        CHECK (length(btrim(text)) > 0),

    start_page INTEGER NOT NULL
        CHECK (start_page >= 1),

    end_page INTEGER NOT NULL,

    embedding VECTOR(768) NOT NULL,

    embedding_model VARCHAR(100) NOT NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT chk_chunk_page_range
        CHECK (end_page >= start_page),

    CONSTRAINT uq_document_chunk_index
        UNIQUE (document_id, chunk_index)
);


-- ============================================================
-- 5. RELATIONAL LOOKUP INDEXES
-- ============================================================

CREATE INDEX idx_knowledge_projects_owner_id
    ON knowledge_projects(owner_id);

CREATE INDEX idx_documents_project_id
    ON documents(project_id);

CREATE INDEX idx_document_chunks_document_id
    ON document_chunks(document_id);


COMMIT;



SELECT
    datname AS database_name,
    pg_get_userbyid(datdba) AS database_owner
FROM pg_database
WHERE datname IN ('rag_db', 'sso_db');


CREATE ROLE sso_owner NOLOGIN;

SELECT
    rolname,
    rolcanlogin,
    rolsuper,
    rolcreatedb,
    rolcreaterole
FROM pg_roles
WHERE rolname = 'sso_owner';

ALTER DATABASE sso_db OWNER TO sso_owner;

SELECT
    datname AS database_name,
    pg_get_userbyid(datdba) AS database_owner
FROM pg_database
WHERE datname IN ('rag_db', 'sso_db');


BEGIN;

ALTER TABLE public.app_users OWNER TO sso_owner;
ALTER TABLE public.app_user_credentials OWNER TO sso_owner;
ALTER TABLE public.app_user_roles OWNER TO sso_owner;
ALTER TABLE public.auth_sessions OWNER TO sso_owner;
ALTER TABLE public.oauth_clients OWNER TO sso_owner;
ALTER TABLE public.oauth_authorization_codes OWNER TO sso_owner;
ALTER TABLE public.oauth_refresh_tokens OWNER TO sso_owner;

COMMIT;



BEGIN;

ALTER TABLE public.app_users OWNER TO sso_owner;
ALTER TABLE public.app_user_credentials OWNER TO sso_owner;
ALTER TABLE public.app_user_roles OWNER TO sso_owner;
ALTER TABLE public.auth_sessions OWNER TO sso_owner;
ALTER TABLE public.oauth_clients OWNER TO sso_owner;
ALTER TABLE public.oauth_authorization_codes OWNER TO sso_owner;
ALTER TABLE public.oauth_refresh_tokens OWNER TO sso_owner;

COMMIT;



SELECT current_database(), current_user;


  CREATE TABLE IF NOT EXISTS public.chatbot_sessions (
    sid VARCHAR NOT NULL PRIMARY KEY,
    sess JSON NOT NULL,
    expire TIMESTAMP(6) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_chatbot_sessions_expire
    ON public.chatbot_sessions (expire);