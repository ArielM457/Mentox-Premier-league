create table if not exists public.matches (
  id text primary key,
  home_team text not null,
  away_team text not null,
  duration_ms bigint not null check (duration_ms >= 0),
  metadata jsonb not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.match_events (
  event_id text primary key,
  match_id text not null references public.matches(id) on delete cascade,
  video_time_ms bigint,
  clock_ms bigint not null check (clock_ms >= 0),
  event_type text not null,
  payload jsonb not null,
  created_at timestamptz not null default now()
);

create table if not exists public.moments (
  message_id text primary key,
  match_id text not null references public.matches(id) on delete cascade,
  candidate_id text,
  video_time_ms bigint not null check (video_time_ms >= 0),
  priority integer not null check (priority between 0 and 100),
  kind text not null,
  headline text not null,
  explanation text not null,
  source_event_ids jsonb not null default '[]'::jsonb,
  payload jsonb not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.assistant_messages (
  id uuid primary key default gen_random_uuid(),
  match_id text not null references public.matches(id) on delete cascade,
  video_time_ms bigint not null check (video_time_ms >= 0),
  question text not null,
  headline text not null,
  explanation text not null,
  source_event_ids jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists match_events_match_time_idx
  on public.match_events(match_id, video_time_ms);
create index if not exists moments_match_time_idx
  on public.moments(match_id, video_time_ms);
create index if not exists assistant_messages_match_time_idx
  on public.assistant_messages(match_id, video_time_ms);

alter table public.matches enable row level security;
alter table public.match_events enable row level security;
alter table public.moments enable row level security;
alter table public.assistant_messages enable row level security;

comment on table public.matches is 'Partidos sintéticos y sus metadatos.';
comment on table public.match_events is 'Eventos normalizados que alimentan estado y agentes.';
comment on table public.moments is 'Momentos narrativos con sus eventos de origen.';
comment on table public.assistant_messages is 'Preguntas y respuestas respaldadas por eventos ocurridos.';
