import { useEffect, useState } from 'react'

// Enrutador mínimo con el hash de la URL: el botón Atrás del navegador funciona
// y cada pantalla se puede abrir o compartir con su dirección.
const ROUTES = [
  ['landing', /^\/?$/],
  ['onboarding', /^\/onboarding$/],
  ['discover', /^\/discover$/],
  ['matches', /^\/matches$/],
  ['preview', /^\/match\/([^/]+)\/preview$/],
  ['match', /^\/match\/([^/]+)$/],
  ['moment', /^\/match\/([^/]+)\/moment\/([^/]+)$/],
  ['recap', /^\/recap\/([^/]+)$/],
  ['profile', /^\/profile$/],
  ['editorial', /^\/editorial$/],
]

export function parseRoute(hash) {
  const path = decodeURIComponent(hash.replace(/^#/, '')) || '/'
  for (const [name, pattern] of ROUTES) {
    const match = path.match(pattern)
    if (match) return { name, params: match.slice(1) }
  }
  return { name: 'landing', params: [] }
}

export function navigate(path) {
  window.location.hash = path
}

export const paths = {
  landing: () => '/',
  onboarding: () => '/onboarding',
  discover: () => '/discover',
  matches: () => '/matches',
  match: (matchId) => `/match/${encodeURIComponent(matchId)}`,
  preview: (matchId) => `/match/${encodeURIComponent(matchId)}/preview`,
  moment: (matchId, momentId) => `/match/${encodeURIComponent(matchId)}/moment/${encodeURIComponent(momentId)}`,
  recap: (matchId) => `/recap/${encodeURIComponent(matchId)}`,
  profile: () => '/profile',
  editorial: () => '/editorial',
}

// Un partido "FT" abre su resumen; uno en vivo abre el centro del partido.
export function openMatch(match, status) {
  navigate(status === 'FT' ? paths.recap(match.id) : status === 'UPCOMING' ? paths.preview(match.id) : paths.match(match.id))
}

export function useRoute() {
  const [route, setRoute] = useState(() => parseRoute(window.location.hash))
  useEffect(() => {
    const onChange = () => {
      setRoute(parseRoute(window.location.hash))
      window.scrollTo({ top: 0 })
    }
    window.addEventListener('hashchange', onChange)
    return () => window.removeEventListener('hashchange', onChange)
  }, [])
  return route
}
