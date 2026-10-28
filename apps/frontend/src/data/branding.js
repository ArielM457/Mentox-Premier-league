// Identidad visual del diseño de Persona 5 aplicada a los equipos sintéticos de la API.
// Los nombres, jugadores y datos siempre vienen del backend; aquí solo hay escudos, colores y fotos.

const TEAM_BRANDING = {
  'team-aurora': { short: 'AUR', color: '#963879', logo: '/images/clubs/aurora-athletic.webp' },
  'team-rio': { short: 'RIO', color: '#6539d5', logo: '/images/clubs/riverside-united.webp' },
  'team-north-city': { short: 'NC', color: '#d8ff65', logo: '/images/clubs/north-city.png' },
  'team-harborline': { short: 'HF', color: '#205664', logo: '/images/clubs/harborline-fc.png' },
  'team-summit-vale': { short: 'SV', color: '#404b8d', logo: '/images/clubs/summit-vale.png' },
  'team-ember-borough': { short: 'EB', color: '#963653', logo: '/images/clubs/ember-borough.png' },
}

// Clubes del diseño inicial que todavía no tienen un partido cargado.
// Se mantienen en el catálogo de preferencias; los datos de partido siguen llegando de la API.
export const ADDITIONAL_CLUBS = [
  { team_id: 'team-north-city', name: 'North City' },
  { team_id: 'team-harborline', name: 'Harborline FC' },
  { team_id: 'team-summit-vale', name: 'Summit Vale' },
  { team_id: 'team-ember-borough', name: 'Ember Borough' },
]

export const ADDITIONAL_PLAYERS = [
  { player_id: 'north-1', team_id: 'team-north-city', name: 'Milo Arden', shirt_number: 1 },
  { player_id: 'north-8', team_id: 'team-north-city', name: 'Teo Varin', shirt_number: 8 },
  { player_id: 'north-9', team_id: 'team-north-city', name: 'Cael Norr', shirt_number: 9 },
  { player_id: 'harborline-1', team_id: 'team-harborline', name: 'Samir Dax', shirt_number: 1 },
  { player_id: 'harborline-8', team_id: 'team-harborline', name: 'Arin Solt', shirt_number: 8 },
  { player_id: 'harborline-9', team_id: 'team-harborline', name: 'Tomas Vey', shirt_number: 9 },
  { player_id: 'summit-1', team_id: 'team-summit-vale', name: 'Oskar Venn', shirt_number: 1 },
  { player_id: 'summit-8', team_id: 'team-summit-vale', name: 'Mateo Brin', shirt_number: 8 },
  { player_id: 'summit-9', team_id: 'team-summit-vale', name: 'Soren Vale', shirt_number: 9 },
  { player_id: 'ember-1', team_id: 'team-ember-borough', name: 'Idris Kellan', shirt_number: 1 },
  { player_id: 'ember-8', team_id: 'team-ember-borough', name: 'Pavel Orin', shirt_number: 8 },
  { player_id: 'ember-9', team_id: 'team-ember-borough', name: 'Rafael Miro', shirt_number: 9 },
]

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
  professional_analyst: { icon: 'chart', image: '/images/duel.webp' },
  player: { icon: 'user', image: '/images/player.webp' },
}
