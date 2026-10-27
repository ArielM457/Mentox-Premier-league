// Identidad anónima para la comunidad: un identificador aleatorio por navegador
// (un voto por persona) y el nombre que la persona elige. No hay inicio de sesión.
const ID_KEY = 'tpm:community-id'
const NAME_KEY = 'tpm:community-name'

function randomId() {
  if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID().replaceAll('-', '')
  return Array.from({ length: 24 }, () => Math.floor(Math.random() * 36).toString(36)).join('')
}

export function communityClientId() {
  try {
    let id = localStorage.getItem(ID_KEY)
    if (!id) {
      id = randomId()
      localStorage.setItem(ID_KEY, id)
    }
    return id
  } catch {
    // Sin almacenamiento el identificador dura hasta recargar.
    return (communityClientId.fallback ??= randomId())
  }
}

export function savedCommunityName() {
  try {
    return localStorage.getItem(NAME_KEY) ?? ''
  } catch {
    return ''
  }
}

export function saveCommunityName(name) {
  try {
    localStorage.setItem(NAME_KEY, name)
  } catch {
    // Solo es una comodidad.
  }
}
