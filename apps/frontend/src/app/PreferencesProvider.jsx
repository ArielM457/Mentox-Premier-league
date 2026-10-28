import { useEffect, useLayoutEffect, useMemo, useState } from 'react'
import { strings } from '../i18n/strings.js'
import { CONFIGURATION_STORAGE_KEYS, DEFAULT_PREFERENCES, PreferencesContext, STORAGE_KEY } from './preferences.js'

function load() {
  try {
    return { ...DEFAULT_PREFERENCES, ...JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '{}') }
  } catch {
    return DEFAULT_PREFERENCES
  }
}

export function PreferencesProvider({ children }) {
  const [preferences, setPreferences] = useState(load)

  useLayoutEffect(() => {
    document.documentElement.dataset.theme = preferences.theme === 'light' ? 'light' : 'dark'
    document.documentElement.style.colorScheme = preferences.theme === 'light' ? 'light' : 'dark'
  }, [preferences.theme])

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
    const reset = () => {
      try {
        CONFIGURATION_STORAGE_KEYS.forEach((key) => localStorage.removeItem(key))
      } catch {
        // El estado de React igualmente se reinicia si el navegador bloquea el almacenamiento.
      }
      setPreferences({ ...DEFAULT_PREFERENCES })
    }
    return { preferences, reset, update, t: strings[preferences.language] }
  }, [preferences])

  // Los cambios visuales no reinician las consultas ni el canal del partido.
  const apiPreferences = useMemo(() => {
    const apiPreferences = {
      language: preferences.language,
      mode: preferences.mode === 'player' && !preferences.favoritePlayerId ? 'casual' : preferences.mode,
      level: preferences.mode === 'professional_analyst' ? 'advanced' : preferences.level,
      favoriteTeamId: preferences.favoriteTeamId,
      favoritePlayerId: preferences.favoritePlayerId,
    }
    return apiPreferences
  }, [preferences.language, preferences.mode, preferences.level, preferences.favoriteTeamId, preferences.favoritePlayerId])

  return <PreferencesContext.Provider value={{ ...value, apiPreferences }}>{children}</PreferencesContext.Provider>
}
