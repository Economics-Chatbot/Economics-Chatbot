create extension if not exists vector;

create table if not exists public.economic_terms (
  term_id bigserial primary key,
  term_name text not null unique,
  official_definition text not null,
  source_name text not null default '한국은행 경제금융용어 자료',
  source_page integer,
  related_terms text[] not null default '{}',
  embedding vector(1536),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists economic_terms_term_name_idx
  on public.economic_terms using btree (term_name);

create index if not exists economic_terms_embedding_idx
  on public.economic_terms
  using ivfflat (embedding vector_cosine_ops)
  with (lists = 100);

create or replace function public.match_economic_terms(
  query_embedding vector(1536),
  match_count int default 3,
  min_similarity float default 0.72
)
returns table (
  term_id bigint,
  term_name text,
  official_definition text,
  source_name text,
  source_page integer,
  related_terms text[],
  similarity float
)
language sql
stable
as $$
  select
    et.term_id,
    et.term_name,
    et.official_definition,
    et.source_name,
    et.source_page,
    et.related_terms,
    1 - (et.embedding <=> query_embedding) as similarity
  from public.economic_terms et
  where et.embedding is not null
    and 1 - (et.embedding <=> query_embedding) >= min_similarity
  order by et.embedding <=> query_embedding
  limit match_count;
$$;
