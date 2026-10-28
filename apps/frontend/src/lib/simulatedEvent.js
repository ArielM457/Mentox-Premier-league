// La atribución viene del simulador, nunca se presenta como identidad detectada.
export function describeSimulatedEvent(payload, metadata, copy) {
  const players = metadata?.players ?? []
  const player = players.find((item) => item.player_id === payload.player_id)?.name ?? copy.unknownPlayer
  const receiver = players.find((item) => item.player_id === payload.receiver_player_id)?.name
  const team = [metadata?.home_team, metadata?.away_team].find((item) => item?.team_id === payload.team_id)?.name ?? copy.unknownTeam
  const kind = payload.event_type ?? payload.type
  let text
  if (kind === 'pass') text = receiver ? copy.pass(player, receiver) : copy.passUnknown(player)
  else if (kind === 'shot') text = payload.outcome === 'goal' ? copy.goal(player) : copy.shot(player)
  else if (kind === 'possession_change') text = copy.possession(team)
  else text = `${player} · ${copy.types[kind] ?? kind}`
  const facts = []
  if (payload.distance_m != null && Number.isFinite(Number(payload.distance_m))) facts.push(`${Number(payload.distance_m).toFixed(1)} m`)
  if (payload.launch_speed_m_s != null && Number.isFinite(Number(payload.launch_speed_m_s))) facts.push(`${copy.launchSpeed}: ${(Number(payload.launch_speed_m_s) * 3.6).toFixed(1)} km/h`)
  return {
    title: `${text} · ${team}`,
    evidence: [copy.source, copy.outcomes[payload.outcome] ?? copy.outcomes.unknown, ...facts,
      payload.model_candidates?.length ? copy.candidates(payload.model_candidates.length) : copy.noConfirmation].join(' · '),
  }
}
