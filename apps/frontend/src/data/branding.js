// Identidad visual del diseño de Persona 5 aplicada a los equipos sintéticos de la API.
// Los nombres, jugadores y datos siempre vienen del backend; aquí solo hay escudos, colores y fotos.

const TEAM_BRANDING = {
  'team-aurora': { short: 'AUR', color: '#963879', logo: '/images/clubs/aurora-athletic.webp' },
  'team-rio': { short: 'RIO', color: '#6539d5', logo: '/images/clubs/riverside-united.webp' },
}

const PLAYER_PHOTOS = Array.from({ length: 18 }, (_, i) => `/images/players/player-${String(i + 1).padStart(2, '0')}.webp`)

export function teamBranding(team) {
  const known = TEAM_BRANDING[team?.team_id]
  if (known) return known
  const short = (team?.name ?? '?').replace(/[^A-Za-zÁÉÍÓÚÑáéíóúñ ]/g, '').split(' ').map((w) => w[0]).join('').slice(0, 3).toUpperCase()
  return { short, color: '#8257f5', logo: null }
}

// Foto estable para cada jugador: el mismo identificador recibe siempre la misma imagen.
export function playerPhoto(playerId) {
  let hash = 0
  for (const char of playerId ?? '') hash = (hash * 31 + char.charCodeAt(0)) >>> 0
  return PLAYER_PHOTOS[hash % PLAYER_PHOTOS.length]
}

export const MODE_ART = {
  casual: { icon: 'spark', image: '/images/fans.webp' },
  analyst: { icon: 'chart', image: '/images/duel.webp' },
  player: { icon: 'user', image: '/images/player.webp' },
}
