-- Campos de MatchEvent 1.0 que añadió la rama develop el 25 de octubre de 2026:
-- receptor del pase, intención de la jugada y duración de una detención
-- (faltas, tarjetas, lesiones y reanudaciones). Idempotente.

alter table match_analytics.match_events
  add column if not exists receiver_player_id text,
  add column if not exists situation text,
  add column if not exists stoppage_ms integer not null default 0;

do $$
begin
  if not exists (
    select 1 from pg_constraint where conname = 'match_events_situation_length'
  ) then
    alter table match_analytics.match_events
      add constraint match_events_situation_length check (char_length(situation) <= 80);
  end if;
  if not exists (
    select 1 from pg_constraint where conname = 'match_events_stoppage_range'
  ) then
    alter table match_analytics.match_events
      add constraint match_events_stoppage_range check (stoppage_ms between 0 and 120000);
  end if;
end $$;
