// Cliente de la API de partido. Cada función lanza ApiError con el detalle del backend.
import { strings } from '../i18n/strings.js'

export class ApiError extends Error {
  constructor(message, status, data = null) {
    super(message)
    this.status = status
    this.data = data
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

async function request(path, options = {}) {
  let response
  try {
    response = await fetch(path, {
      signal: AbortSignal.timeout(20_000),
      ...options,
      headers: options.headers ?? (options.body ? { 'Content-Type': 'application/json' } : undefined),
    })
  } catch {
    // PreferencesProvider mantiene el idioma elegido en <html lang>.
    throw new ApiError((strings[document.documentElement.lang] ?? strings.es).common.apiDown, 0)
  }
  const data = await response.json().catch(() => null)
  if (!response.ok) {
    const detail = typeof data?.detail === 'string' ? data.detail : JSON.stringify(data?.detail ?? response.statusText)
    throw new ApiError(detail, response.status, data)
  }
  return data
}

const base = (matchId) => `/api/v1/matches/${encodeURIComponent(matchId)}`

export const api = {
  health: () => request('/api/v1/health'),
  listMatches: () => request('/api/v1/matches'),
  loadMatch: (body) => request('/api/v1/matches', { method: 'POST', body: JSON.stringify(body) }),
  match: (id) => request(base(id)),
  preview: (id) => request(`${base(id)}/preview`),
  tracking: (id, from, to) => request(`${base(id)}/tracking?from_video_ms=${Math.floor(from)}&to_video_ms=${Math.floor(to)}`),
  momentAnalysis: (id, candidateId, prefs, anchorEventId) => {
    const params = prefsQuery(prefs)
    if (anchorEventId) params.set('anchor_event_id', anchorEventId)
    return request(`${base(id)}/moments/${encodeURIComponent(candidateId)}/analysis?${params}`)
  },
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
  summary: (id, prefs, options = {}) => {
    const params = prefsQuery(prefs)
    params.set('summary_type', options.type ?? 'extended')
    if (options.playerId) params.set('player_id', options.playerId)
    return request(`${base(id)}/summary?${params}`)
  },
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
  simulate: (id, prefs) => request(`${base(id)}/simulation?${prefsQuery(prefs)}`, { method: 'POST' }),
  highlights: (id) => request(`${base(id)}/highlights`),
  reviewHighlight: (id, clipId, decision, reviewer) =>
    request(`${base(id)}/highlights/${encodeURIComponent(clipId)}/review`, {
      method: 'POST',
      body: JSON.stringify({ decision, reviewer }),
    }),
  playback: (id, action, t) =>
    request(`${base(id)}/playback`, {
      method: 'POST',
      body: JSON.stringify({ action, video_time_ms: t == null ? null : Math.floor(t) }),
    }),
  visionStatus: () => request('/api/v1/integration/status'),
  // Despertar la GPU (escala desde cero) tarda más que el límite general de 20 s.
  prepareVisionModels: () => request('/api/v1/integration/live/models/prepare', { method: 'POST', signal: AbortSignal.timeout(180_000) }),
  visionTimeline: (start, end, limit = 40) =>
    request(`/api/v1/integration/timeline?start_ms=${Math.floor(start)}&end_ms=${Math.floor(end)}&spatial_limit=${limit}`),
  visionPlayback: (action, t, matchId) =>
    request(`/api/v1/integration/live/playback/${action}`, {
      method: 'POST',
      body: JSON.stringify({ video_time_ms: Math.floor(t ?? 0), match_id: matchId }),
    }),
  captureVisionFrame: (matchId, t, image) => request(
    `/api/v1/integration/live/capture/frame?match_id=${encodeURIComponent(matchId)}&video_time_ms=${Math.floor(t)}`,
    { method: 'POST', body: image, headers: { 'Content-Type': image.type || 'image/jpeg' } },
  ),
  communityTallies: (id) => request(`${base(id)}/community`),
  communityRoom: (id, draftId, clientId) =>
    request(`${base(id)}/community/${encodeURIComponent(draftId)}?client_id=${encodeURIComponent(clientId)}`),
  communityVote: (id, draftId, body) =>
    request(`${base(id)}/community/${encodeURIComponent(draftId)}/votes`, { method: 'POST', body: JSON.stringify(body) }),
  communityPost: (id, draftId, body) =>
    request(`${base(id)}/community/${encodeURIComponent(draftId)}/messages`, { method: 'POST', body: JSON.stringify(body) }),
  communityStreamUrl: (id, draftId) => `${base(id)}/community/${encodeURIComponent(draftId)}/stream`,
}
