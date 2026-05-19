-- Organica Biotech Website Bot - database schema (Postgres + pgvector)

create extension if not exists vector;

-- Knowledge base: one row per searchable chunk
create table if not exists kb_chunks (
    id           text primary key,
    vertical     text,
    sub_category text,
    product      text,
    doc_type     text,
    source       text,
    text         text not null,
    embedding    vector(1024)
);
create index if not exists kb_chunks_embedding_idx
    on kb_chunks using hnsw (embedding vector_cosine_ops);

-- One row per chat session
create table if not exists conversations (
    id          uuid primary key default gen_random_uuid(),
    session_id  text,
    vertical    text,
    page_url    text,
    user_agent  text,
    location    jsonb,
    started_at  timestamptz not null default now()
);

-- Every message in every conversation (full transcript)
create table if not exists messages (
    id              bigserial primary key,
    conversation_id uuid references conversations(id) on delete cascade,
    role            text not null,        -- 'user' | 'assistant'
    content         text not null,
    created_at      timestamptz not null default now()
);
create index if not exists messages_conv_idx on messages(conversation_id);

-- Captured leads
create table if not exists leads (
    id               bigserial primary key,
    conversation_id  uuid references conversations(id) on delete set null,
    name             text,
    email            text,
    phone            text,
    vertical         text,
    product_interest text,
    intent           text,
    location         jsonb,
    consent          boolean default false,
    created_at       timestamptz not null default now()
);
create index if not exists leads_created_idx on leads(created_at desc);
