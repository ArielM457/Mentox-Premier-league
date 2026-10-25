const STORAGE_KEY = 'itg:experience'
const LIMIT = 20

const EMPTY = { viewedMatches: [], viewedRecaps: [] }

export function loadExperience() {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '{}')
    return {
      viewedMatches: Array.isArray(saved.viewedMatches) ? saved.viewedMatches : [],
      viewedRecaps: Array.isArray(saved.viewedRecaps) ? saved.viewedRecaps : [],
    }
  } catch {
    return EMPTY
  }
}

export function recordExperience(matchId, kind = 'match') {
  const current = loadExperience()
  const key = kind === 'recap' ? 'viewedRecaps' : 'viewedMatches'
  const entry = { matchId, viewedAt: new Date().toISOString() }
  const next = [entry, ...current[key].filter((item) => item.matchId !== matchId)].slice(0, LIMIT)
  const updated = { ...current, [key]: next }
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(updated))
  } catch {
    // La experiencia sigue funcionando aunque el navegador bloquee el almacenamiento.
  }
  return updated
}
