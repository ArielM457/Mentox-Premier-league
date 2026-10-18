-- Datos ficticios de partidos y resultados de la analítica (Persona 2).
--
-- Todo vive en el esquema match_analytics, que la API de datos de Supabase no
-- expone: solo el backend lo lee con la cadena de conexión de Postgres.
-- Los partidos son sintéticos; la columna provenance lo impide de otra forma.
-- El script es idempotente: puede ejecutarse varias veces.

create schema if not exists match_analytics;

comment on schema match_analytics is
  'Partidos sintéticos, observaciones simuladas y resultados de la analítica. Sin datos reales.';

-- Partido: MatchMetadata 1.0 de Persona 1, más datos de catálogo para la demo.
create table if not exists match_analytics.matches (
  match_id             text primary key,
  schema_version       text not null default '1.0' check (schema_version = '1.0'),
  title                text not null,
  scenario             text not null,
  seed                 integer,
  provenance           text not null default 'synthetic' check (provenance = 'synthetic'),
  home_team_id         text not null,
  home_team_name       text not null,
  away_team_id         text not null,
  away_team_name       text not null,
  pitch_length_m       double precision not null check (pitch_length_m > 0),
  pitch_width_m        double precision not null check (pitch_width_m > 0),
  attacking_directions jsonb not null default '[]'::jsonb,
  kickoff_at           timestamptz,
  created_at           timestamptz not null default now()
);

create table if not exists match_analytics.match_players (
  match_id      text not null references match_analytics.matches (match_id) on delete cascade,
  player_id     text not null,
  roster_order  smallint not null check (roster_order >= 0),
  team_id       text not null,
  name          text not null,
  shirt_number  smallint check (shirt_number between 1 and 99),
  is_goalkeeper boolean not null default false,
  primary key (match_id, player_id)
);

-- Evento: MatchEvent 1.0. sequence conserva el orden de llegada del generador.
create table if not exists match_analytics.match_events (
  match_id          text not null references match_analytics.matches (match_id) on delete cascade,
  event_id          text not null,
  sequence          integer not null check (sequence >= 0),
  schema_version    text not null default '1.0' check (schema_version = '1.0'),
  period            smallint not null check (period between 1 and 4),
  clock_ms          integer not null check (clock_ms >= 0),
  video_time_ms     integer check (video_time_ms >= 0),
  type              text not null,
  team_id           text not null,
  player_id         text,
  start_x           double precision check (start_x between 0 and 100),
  start_y           double precision check (start_y between 0 and 100),
  end_x             double precision check (end_x between 0 and 100),
  end_y             double precision check (end_y between 0 and 100),
  outcome           text not null,
  source            text not null,
  confidence        double precision check (confidence between 0 and 1),
  related_event_ids text[] not null default '{}',
  primary key (match_id, event_id),
  unique (match_id, sequence)
);

-- Observación de seguimiento: VisualTrackObservation de Persona 1.
-- origin repite PredictionOrigin; los datos de la demo son simulated_fixture.
create table if not exists match_analytics.tracking_observations (
  match_id            text not null references match_analytics.matches (match_id) on delete cascade,
  observation_id      text not null,
  video_time_ms       integer not null check (video_time_ms >= 0),
  track_id            text not null,
  team_id             text,
  x                   double precision check (x between 0 and 100),
  y                   double precision check (y between 0 and 100),
  detector_confidence double precision not null check (detector_confidence between 0 and 1),
  origin              text not null check (origin in ('simulated_fixture', 'actual_model')),
  primary key (match_id, observation_id)
);

create index if not exists tracking_observations_by_time
  on match_analytics.tracking_observations (match_id, video_time_ms);

-- Identidad resuelta de una pista: ResolvedVisualIdentity de Persona 1.
create table if not exists match_analytics.visual_identities (
  match_id                    text not null references match_analytics.matches (match_id) on delete cascade,
  observation_id              text not null,
  video_time_ms               integer not null check (video_time_ms >= 0),
  track_id                    text not null,
  player_id                   text,
  identity_status             text not null check (identity_status in ('confirmed', 'unconfirmed')),
  detector_confidence         double precision not null check (detector_confidence between 0 and 1),
  identity_evidence_kind      text,
  identity_evidence_reference text,
  primary key (match_id, observation_id),
  check (identity_status = 'unconfirmed' or player_id is not null)
);

-- Registro de un análisis: los mismos archivos que el procesador guarda en Blob.
create table if not exists match_analytics.analytics_runs (
  run_id            text primary key,
  match_id          text not null references match_analytics.matches (match_id) on delete cascade,
  produced_by       text not null,
  engine_version    text,
  attention_version text,
  profile           text,
  event_count       integer,
  candidate_count   integer,
  manifest          jsonb,
  created_at        timestamptz not null default now()
);

create index if not exists analytics_runs_by_match
  on match_analytics.analytics_runs (match_id, created_at desc);

-- content guarda el JSON tal cual; un .jsonl se guarda como arreglo.
create table if not exists match_analytics.analytics_run_files (
  run_id       text not null references match_analytics.analytics_runs (run_id) on delete cascade,
  name         text not null,
  content_type text not null,
  sha256       text not null,
  size_bytes   integer not null,
  content      jsonb not null,
  primary key (run_id, name)
);

-- Vistas para consultar sin desarmar el JSON a mano.
create or replace view match_analytics.final_metrics
with (security_invoker = true) as
select r.run_id,
       r.match_id,
       r.created_at,
       m ->> 'key'                       as key,
       m ->> 'team_id'                   as team_id,
       m ->> 'player_id'                 as player_id,
       (m ->> 'value')::double precision as value,
       (m ->> 'available')::boolean      as available,
       m ->> 'unit'                      as unit,
       m ->> 'origin'                    as origin,
       m ->> 'formula_version'           as formula_version,
       m -> 'source_event_ids'           as source_event_ids,
       m                                 as metric
from match_analytics.analytics_runs r
join match_analytics.analytics_run_files f
  on f.run_id = r.run_id and f.name in ('final-snapshot.json', 'tracking-metrics.jsonl')
cross join lateral jsonb_array_elements(
  case when f.name = 'final-snapshot.json' then f.content -> 'metrics' else f.content end
) as m;

create or replace view match_analytics.attention_decisions
with (security_invoker = true) as
select r.run_id,
       r.match_id,
       r.created_at,
       d ->> 'candidate_id'        as candidate_id,
       d ->> 'kind'                as kind,
       d ->> 'outcome'             as outcome,
       (d ->> 'priority')::integer  as priority,
       (d ->> 'threshold')::integer as threshold,
       d ->> 'profile'             as profile,
       (d ->> 'period')::integer    as period,
       (d ->> 'clock_ms')::integer  as clock_ms,
       d ->> 'team_id'             as team_id,
       d -> 'reasons'              as reasons,
       d                           as decision
from match_analytics.analytics_runs r
join match_analytics.analytics_run_files f
  on f.run_id = r.run_id and f.name = 'attention-decisions.jsonl'
cross join lateral jsonb_array_elements(f.content) as d;

create or replace view match_analytics.candidate_proposals
with (security_invoker = true) as
select r.run_id,
       r.match_id,
       r.created_at,
       c ->> 'candidate_id'             as candidate_id,
       c ->> 'kind'                     as kind,
       (c ->> 'priority')::integer      as priority,
       (c ->> 'period')::integer        as period,
       (c ->> 'clock_ms')::integer      as clock_ms,
       (c ->> 'video_time_ms')::integer as video_time_ms,
       c ->> 'team_id'                  as team_id,
       c -> 'player_ids'                as player_ids,
       c -> 'source_event_ids'          as source_event_ids,
       c                                as candidate
from match_analytics.analytics_runs r
join match_analytics.analytics_run_files f
  on f.run_id = r.run_id and f.name = 'candidates.jsonl'
cross join lateral jsonb_array_elements(f.content) as c;

create or replace view match_analytics.tracking_alerts
with (security_invoker = true) as
select r.run_id,
       r.match_id,
       r.created_at,
       a ->> 'alert_id'  as alert_id,
       a ->> 'kind'      as kind,
       a ->> 'player_id' as player_id,
       a ->> 'origin'    as origin,
       a                 as alert
from match_analytics.analytics_runs r
join match_analytics.analytics_run_files f
  on f.run_id = r.run_id and f.name = 'tracking-alerts.jsonl'
cross join lateral jsonb_array_elements(f.content) as a;

-- Defensa adicional si alguien expone el esquema: sin políticas, nadie lee
-- mediante la API de datos. El dueño (la conexión del backend) no se ve afectado.
alter table match_analytics.matches               enable row level security;
alter table match_analytics.match_players         enable row level security;
alter table match_analytics.match_events          enable row level security;
alter table match_analytics.tracking_observations enable row level security;
alter table match_analytics.visual_identities     enable row level security;
alter table match_analytics.analytics_runs        enable row level security;
alter table match_analytics.analytics_run_files   enable row level security;
