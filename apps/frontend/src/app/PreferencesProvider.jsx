import { useEffect, useMemo, useState } from 'react'
import { strings } from '../i18n/strings.js'
import { DEFAULT_PREFERENCES, PreferencesContext, STORAGE_KEY } from './preferences.js'
import { useSession } from './session.js'

// Cada cuenta guarda sus propias preferencias; sin sesión solo importa el idioma.
const keyFor = (username) => (username ? `${STORAGE_KEY}:${username}` : STORAGE_KEY)

function load(key, language) {
  try {
    const saved = localStorage.getItem(key)
    if (saved) return { ...DEFAULT_PREFERENCES, ...JSON.parse(saved) }
  } catch {
    // Sin almacenamiento local se usan los valores por defecto.
  }
  // Una cuenta nueva hereda el idioma elegido antes de iniciar sesión.
  return { ...DEFAULT_PREFERENCES, language: language ?? DEFAULT_PREFERENCES.language }
}

export function PreferencesProvider({ children }) {
  const { user } = useSession()
  const key = keyFor(user?.username)
  const [state, setState] = useState(() => ({ key, preferences: load(key) }))

  // Al iniciar o cerrar sesión se cargan las preferencias de esa cuenta.
  let { preferences } = state
  if (state.key !== key) {
    preferences = load(key, preferences.language)
    setState({ key, preferences })
  }

  useEffect(() => {
    document.documentElement.lang = state.preferences.language
    try {
      localStorage.setItem(state.key, JSON.stringify(state.preferences))
    } catch {
      // Sin almacenamiento local las preferencias duran solo esta visita.
    }
  }, [state])

  const value = useMemo(() => {
    const update = (changes) => setState((current) => ({ ...current, preferences: { ...current.preferences, ...changes } }))
    // Lo que se envía a la API. Sin jugador favorito, el modo jugador cae a casual en vez de fallar.
    const apiPreferences = {
      language: preferences.language,
      mode: preferences.mode === 'player' && !preferences.favoritePlayerId ? 'casual' : preferences.mode,
      level: preferences.level,
      favoriteTeamId: preferences.favoriteTeamId,
      favoritePlayerId: preferences.favoritePlayerId,
    }
    return { preferences, update, apiPreferences, t: strings[preferences.language] }
  }, [preferences])

  return <PreferencesContext.Provider value={value}>{children}</PreferencesContext.Provider>
}
