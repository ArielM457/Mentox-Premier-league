alter table public.match_summaries
  add column if not exists summary_type text not null default 'extended'
    check (summary_type in ('short', 'extended', 'player_danger')),
  add column if not exists player_id text;

create index if not exists match_summaries_variant_idx
  on public.match_summaries(match_id, summary_type, player_id);

comment on column public.match_summaries.summary_type is
  'Tipo de resumen solicitado: corto, extendido o peligro por jugador.';
comment on column public.match_summaries.player_id is
  'Jugador elegido cuando summary_type es player_danger.';
