create or replace function public.match_economic_terms(
  query_embedding vector(1536),
  match_count int default 8
)
returns table (
  term_id int,
  term_name text,
  official_definition text,
  related_terms text[],
  similarity double precision,
  matched_source text
)
language sql
stable
security invoker
set search_path = public, extensions
as $$
  with all_matches as (
    select
      t.term_id::int,
      t.term_name,
      t.official_definition,
      t.related_terms,
      1 - (c.definition_embedding <=> query_embedding) as similarity,
      'definition'::text as matched_source
    from public.context c
    join public.terms t on t.term_id = c.term_id
    where c.definition_embedding is not null
      and t.official_definition is not null
      and btrim(t.official_definition) <> ''

    union all

    select
      t.term_id::int,
      t.term_name,
      t.official_definition,
      t.related_terms,
      1 - (s.search_embedding <=> query_embedding) as similarity,
      'search_name'::text as matched_source
    from public.search_names s
    join public.terms t on t.term_id = s.term_id
    where s.search_embedding is not null
      and t.official_definition is not null
      and btrim(t.official_definition) <> ''
  ),
  best_per_term as (
    select distinct on (term_id)
      term_id,
      term_name,
      official_definition,
      related_terms,
      similarity,
      matched_source
    from all_matches
    order by term_id, similarity desc
  )
  select
    term_id,
    term_name,
    official_definition,
    related_terms,
    similarity,
    matched_source
  from best_per_term
  order by similarity desc
  limit match_count;
$$;

grant execute on function public.match_economic_terms(vector(1536), int) to service_role;
