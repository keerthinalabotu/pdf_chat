-- Enable UUID extension
create extension if not exists "uuid-ossp";

-- Papers table
create table papers (
    id uuid primary key default uuid_generate_v4(),
    title text not null,
    authors text[] not null,
    abstract text,
    created_at timestamp with time zone default now()
);

-- Paper sections table
create table paper_sections (
    id uuid primary key default uuid_generate_v4(),
    paper_id uuid references papers(id) on delete cascade,
    title text not null,
    content text not null,
    start_page integer,
    end_page integer,
    created_at timestamp with time zone default now()
);

-- Paper formulas table
create table paper_formulas (
    id uuid primary key default uuid_generate_v4(),
    paper_id uuid references papers(id) on delete cascade,
    latex text not null,
    explanation text,
    context text,
    created_at timestamp with time zone default now()
);

-- Chat messages table
create table chat_messages (
    id uuid primary key default uuid_generate_v4(),
    conversation_id uuid not null,
    paper_id uuid references papers(id) on delete cascade,
    role text not null check (role in ('user', 'assistant')),
    content text not null,
    timestamp timestamp with time zone default now()
);

-- Create indexes
create index idx_paper_sections_paper_id on paper_sections(paper_id);
create index idx_paper_formulas_paper_id on paper_formulas(paper_id);
create index idx_chat_messages_conversation_id on chat_messages(conversation_id);
create index idx_chat_messages_paper_id on chat_messages(paper_id);