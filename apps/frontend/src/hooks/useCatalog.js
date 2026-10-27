import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client.js'

// Catálogo de la demo: partidos cargados en la API, sus equipos y jugadores.
// Se pide una vez y se comparte entre pantallas; reload() lo vuelve a pedir.
let cache = null
let pending = null
function sharedCatalog() {
  if (!pending) pending = fetchCatalog().then((data) => { cache = data; return data }).finally(() => { pending = null })
  return pending
}

async function fetchCatalog() {
  const list = await api.listMatches()
  const matches = await Promise.all(
    list.map(async (item) => {
      const upcoming = item.status === 'UPCOMING'
      const [detail, final, events] = await Promise.all([
        api.match(item.match_id),
        upcoming ? Promise.resolve({ score: {} }) : api.state(item.match_id, item.duration_ms),
        upcoming ? Promise.resolve({ events: [] }) : api.events(item.match_id, item.duration_ms),
      ])
      return {
        id: item.match_id,
        status: item.status,
        metadata: detail.metadata,
        durationMs: detail.duration_ms,
        eventCount: detail.event_count,
        finalScore: final.score,
        events: events.events,
        video: detail.video,
      }
    }),
  )

  const clubs = new Map()
  const players = new Map()
  for (const match of matches) {
    for (const team of [match.metadata.home_team, match.metadata.away_team]) clubs.set(team.team_id, team)
    for (const player of match.metadata.players) players.set(player.player_id, player)
  }
  const actions = {}
  for (const match of matches) {
    for (const event of match.events) {
      if (event.player_id) actions[event.player_id] = (actions[event.player_id] ?? 0) + 1
    }
  }
  return {
    matches,
    clubs: [...clubs.values()],
    players: [...players.values()].sort((a, b) => (a.shirt_number ?? 99) - (b.shirt_number ?? 99)),
    actions,
  }
}

export function useCatalog() {
  const [state, setState] = useState(() => (cache ? { data: cache, error: null } : { data: null, error: null }))

  const reload = useCallback(async () => {
    try {
      cache = await sharedCatalog()
      setState({ data: cache, error: null })
    } catch (error) {
      setState((current) => ({ data: current.data, error: error.message }))
    }
  }, [])

  useEffect(() => {
    if (!cache) reload()
  }, [reload])

  return { ...state, reload }
}

export function teamOf(catalog, teamId) {
  return catalog?.clubs.find((team) => team.team_id === teamId) ?? null
}

export function playerOf(catalog, playerId) {
  return catalog?.players.find((player) => player.player_id === playerId) ?? null
}

export function involves(match, teamId) {
  return match.metadata.home_team.team_id === teamId || match.metadata.away_team.team_id === teamId
}
