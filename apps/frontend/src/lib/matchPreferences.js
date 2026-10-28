// Una preferencia global puede corresponder a otro partido del catálogo.
// No enviar ese ID a una sesión MESSI ni cambiar la preferencia guardada.
export function preferencesForMatch(preferences, metadata) {
  const teams = [metadata?.home_team?.team_id, metadata?.away_team?.team_id]
  const players = metadata?.players ?? []
  const favoriteTeamId = teams.includes(preferences.favoriteTeamId) ? preferences.favoriteTeamId : ''
  const favoritePlayerId = players.some((player) => player.player_id === preferences.favoritePlayerId) ? preferences.favoritePlayerId : ''
  return { ...preferences, favoriteTeamId, favoritePlayerId,
    mode: preferences.mode === 'player' && !favoritePlayerId ? 'casual' : preferences.mode }
}
