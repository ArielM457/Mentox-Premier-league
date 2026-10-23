import { createContext, useContext } from 'react'

export const STORAGE_KEY = 'itg:preferences'

export const DEFAULT_PREFERENCES = {
  language: 'es',
  theme: 'dark',
  mode: 'casual',
  level: 'normal',
  favoriteTeamId: '',
  favoritePlayerId: '',
  liveComments: true,
  onboarded: false,
}

export const PreferencesContext = createContext(null)

export function usePreferences() {
  const value = useContext(PreferencesContext)
  if (!value) throw new Error('usePreferences necesita PreferencesProvider')
  return value
}
