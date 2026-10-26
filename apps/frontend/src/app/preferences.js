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

const LANGUAGE_NAMES = { es: 'Español', en: 'English' }

// Las narraciones declaran sus preferencias como «clave:valor» (language:es, favorite_player:p-9…).
// Se muestran con los nombres de la interfaz; una clave desconocida queda tal cual.
export function describePreferences(tags, t, metadata) {
  const teams = metadata ? [metadata.home_team, metadata.away_team] : []
  const label = (tag) => {
    const split = tag.indexOf(':')
    const key = tag.slice(0, split)
    const value = tag.slice(split + 1)
    switch (key) {
      case 'language': return LANGUAGE_NAMES[value] ?? value
      case 'mode': return t.modes[value]?.name ?? value
      case 'level': return t.levels[value]?.name ?? value
      case 'favorite_team': return teams.find((team) => team.team_id === value)?.name ?? value
      case 'favorite_player': return metadata?.players.find((player) => player.player_id === value)?.name ?? value
      default: return tag
    }
  }
  return tags.map(label).join(' · ')
}

export const PreferencesContext = createContext(null)

export function usePreferences() {
  const value = useContext(PreferencesContext)
  if (!value) throw new Error('usePreferences necesita PreferencesProvider')
  return value
}
