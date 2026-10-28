const prefix = 'tpm:match-session:'

export function readMatchSession(matchId) {
  try {
    const value = JSON.parse(window.localStorage.getItem(`${prefix}${matchId}`) || '{}')
    return value && typeof value === 'object' ? value : {}
  } catch {
    return {}
  }
}

export function saveMatchSession(matchId, partial) {
  try {
    const previous = readMatchSession(matchId)
    window.localStorage.setItem(`${prefix}${matchId}`, JSON.stringify({ ...previous, ...partial }))
  } catch {
    // La experiencia sigue disponible si el navegador bloquea el almacenamiento.
  }
}
