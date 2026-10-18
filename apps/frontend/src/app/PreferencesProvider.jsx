import { useEffect, useMemo, useState } from 'react'
import { strings } from '../i18n/strings.js'
import { DEFAULT_PREFERENCES, PreferencesContext, STORAGE_KEY } from './preferences.js'

function load() {
  try {
    return { ...DEFAULT_PREFERENCES, ...JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '{}') }
  } catch {
    return DEFAULT_PREFERENCES
  }
}

export function PreferencesProvider({ children }) {
  const [preferences, setPreferences] = useState(load)

  useEffect(() => {
    document.documentElement.lang = preferences.language
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(preferences))
    } catch {
      // Sin almacenamiento local las preferencias duran solo esta visita.
    }
  }, [preferences])

  const value = useMemo(() => {
    const update = (changes) => setPreferences((current) => ({ ...current, ...changes }))
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
