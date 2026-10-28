create table if not exists public.match_summaries (
  draft_id text primary key,
  match_id text not null references public.matches(id) on delete cascade,
  status text not null check (status in ('pending', 'approved', 'rejected')),
  reviewer text,
  note text,
  decided_at timestamptz,
  headline text not null,
  explanation text not null,
  payload jsonb not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.community_votes (
  match_id text not null references public.matches(id) on delete cascade,
  draft_id text not null,
  client_id text not null,
  author text not null,
  vote text not null check (vote in ('approve', 'reject')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key (match_id, draft_id, client_id)
);

create table if not exists public.community_messages (
  message_id text primary key,
  match_id text not null references public.matches(id) on delete cascade,
  draft_id text not null,
  client_id text not null,
  kind text not null check (kind in ('chat', 'suggestion')),
  author text not null,
  text text not null,
  created_at timestamptz not null default now()
);

create index if not exists match_summaries_match_idx on public.match_summaries(match_id);
create index if not exists community_votes_summary_idx on public.community_votes(match_id, draft_id);
create index if not exists community_messages_summary_time_idx on public.community_messages(match_id, draft_id, created_at);

alter table public.match_summaries enable row level security;
alter table public.community_votes enable row level security;
alter table public.community_messages enable row level security;

comment on table public.match_summaries is 'Resúmenes finales y su decisión editorial.';
comment on table public.community_votes is 'Likes y dislikes por persona y resumen.';
comment on table public.community_messages is 'Sugerencias y conversación de cada resumen.';
