// Cliente de la API de partido. Cada función lanza ApiError con el detalle del backend.

export class ApiError extends Error {
  constructor(message, status) {
    super(message)
    this.status = status
  }
}

function prefsQuery(prefs) {
  const params = new URLSearchParams()
  params.set('language', prefs.language)
  params.set('mode', prefs.mode)
  params.set('level', prefs.level)
  if (prefs.favoriteTeamId) params.set('favorite_team_id', prefs.favoriteTeamId)
  if (prefs.favoritePlayerId) params.set('favorite_player_id', prefs.favoritePlayerId)
  return params
}

export function prefsBody(prefs) {
  return {
    language: prefs.language,
    mode: prefs.mode,
    level: prefs.level,
    favorite_team_id: prefs.favoriteTeamId || null,
    favorite_player_id: prefs.favoritePlayerId || null,
  }
}

// Token de la sesión actual; lo fija SessionProvider al iniciar o cerrar sesión.
let authToken = null

export function setAuthToken(token) {
  authToken = token
}

export const UNAUTHORIZED_EVENT = 'itg:unauthorized'

async function request(path, options = {}) {
  const headers = {}
  if (options.body) headers['Content-Type'] = 'application/json'
  if (authToken) headers.Authorization = `Bearer ${authToken}`
  let response
  try {
    response = await fetch(path, { ...options, headers })
  } catch {
    throw new ApiError('No hay conexión con la API', 0)
  }
  const data = await response.json().catch(() => null)
  if (!response.ok) {
    const detail = typeof data?.detail === 'string' ? data.detail : JSON.stringify(data?.detail ?? response.statusText)
    // Una sesión vencida o inválida se cierra en toda la aplicación.
    if (response.status === 401 && authToken) window.dispatchEvent(new Event(UNAUTHORIZED_EVENT))
    throw new ApiError(detail, response.status)
  }
  return data
}

const base = (matchId) => `/api/v1/matches/${encodeURIComponent(matchId)}`

export const api = {
  login: (username, password) =>
    request('/api/v1/auth/login', { method: 'POST', body: JSON.stringify({ username, password }) }),
  me: () => request('/api/v1/auth/me'),
  analystFeed: (id, prefs, until) => {
    const params = prefsQuery(prefs)
    params.set('until_video_ms', String(Math.floor(until)))
    return request(`${base(id)}/analyst/feed?${params}`)
  },
  health: () => request('/api/v1/health'),
  listMatches: () => request('/api/v1/matches'),
  loadMatch: (body) => request('/api/v1/matches', { method: 'POST', body: JSON.stringify(body) }),
  match: (id) => request(base(id)),
  events: (id, until) => request(`${base(id)}/events?until_video_ms=${Math.floor(until)}`),
  state: (id, t) => request(`${base(id)}/state?video_time_ms=${Math.floor(t)}`),
  overlays: (id, prefs, until) => {
    const params = prefsQuery(prefs)
    params.set('until_video_ms', String(Math.floor(until)))
    return request(`${base(id)}/overlays?${params}`)
  },
  streamUrl: (id, prefs, from, speed) => {
    const params = prefsQuery(prefs)
    params.set('from_video_ms', String(Math.floor(from)))
    params.set('speed', String(speed))
    return `${base(id)}/stream?${params}`
  },
  sources: (id, draftId) => request(`${base(id)}/drafts/${encodeURIComponent(draftId)}/sources`),
  ask: (id, question, t, prefs) =>
    request(`${base(id)}/questions`, {
      method: 'POST',
      body: JSON.stringify({ question, video_time_ms: Math.floor(t), preferences: prefsBody(prefs) }),
    }),
  summary: (id, prefs) => request(`${base(id)}/summary?${prefsQuery(prefs)}`),
  editorial: (id) => request(`${base(id)}/editorial`),
  review: (id, draftId, decision, reviewer, note) =>
    request(`${base(id)}/editorial/${encodeURIComponent(draftId)}/review`, {
      method: 'POST',
      body: JSON.stringify({ decision, reviewer, note: note || null }),
    }),
  published: (id, draftId) => request(`${base(id)}/editorial/${encodeURIComponent(draftId)}/published`),
  report: (id, draftId, messageId, reason) =>
    request(`${base(id)}/reports`, {
      method: 'POST',
      body: JSON.stringify({ draft_id: draftId, message_id: messageId || null, reason }),
    }),
  reports: (id) => request(`${base(id)}/reports`),
  playback: (id, action, t) =>
    request(`${base(id)}/playback`, {
      method: 'POST',
      body: JSON.stringify({ action, video_time_ms: t == null ? null : Math.floor(t) }),
    }),
}
