export const SUMMARY_TYPES = ['short', 'extended', 'player_danger']

export function filterSummaryMoments({ events, moments, playerId, type }) {
  const playerEvents = new Set(
    events
      .filter((event) => event.player_id === playerId || event.receiver_player_id === playerId)
      .map((event) => event.event_id),
  )
  const filtered = moments
    .filter((moment) => !moment.suppressed && moment.kind !== 'player_quiet')
    .filter((moment) => type !== 'short' || moment.kind === 'goal')
    .filter((moment) => type !== 'extended' || ['goal', 'shot', 'recovery', 'turnover'].includes(moment.kind) || moment.priority >= 60)
    .filter((moment) => type !== 'player_danger' || (
      ['goal', 'shot'].includes(moment.kind) && (moment.source_event_ids ?? []).some((id) => playerEvents.has(id))
    ))
    .sort((a, b) => a.video_time_ms - b.video_time_ms)

  if (type === 'short') return filtered.slice(0, 3)
  if (type === 'extended') return filtered.slice(0, 8)
  return filtered
}
