import { createContext, useContext } from 'react'
import { languageName } from '../i18n/languages.js'

export const STORAGE_KEY = 'itg:preferences'
export const CONFIGURATION_STORAGE_KEYS = [
  STORAGE_KEY,
  'itg:sidebar',
  'itg:match-agent-open',
]

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

// Las narraciones declaran sus preferencias como «clave:valor» (language:es, favorite_player:p-9…).
// Se muestran con los nombres de la interfaz; una clave desconocida queda tal cual.
export function describePreferences(tags, t, metadata) {
  const teams = metadata ? [metadata.home_team, metadata.away_team] : []
  const label = (tag) => {
    const split = tag.indexOf(':')
    const key = tag.slice(0, split)
    const value = tag.slice(split + 1)
    switch (key) {
      case 'language': return languageName(value)
      case 'mode': return t.modes[value]?.name ?? value
      case 'level': return t.levels[value]?.name ?? value
      case 'favorite_team': return teams.find((team) => team.team_id === value)?.name ?? value
      case 'favorite_player': return metadata?.players.find((player) => player.player_id === value)?.name ?? value
      default: return tag
    }
  }
  return tags.map(label).join(' · ')
}

export function preferencesForMatch(preferences, metadata) {
  const teamIds = new Set([metadata.home_team.team_id, metadata.away_team.team_id])
  const playerIds = new Set(metadata.players.map((player) => player.player_id))
  const hasPlayer = playerIds.has(preferences.favoritePlayerId)
  return {
    ...preferences,
    level: preferences.mode === 'professional_analyst' ? 'advanced' : preferences.level,
    liveComments: preferences.mode === 'professional_analyst' ? true : preferences.liveComments,
    favoriteTeamId: teamIds.has(preferences.favoriteTeamId) ? preferences.favoriteTeamId : '',
    favoritePlayerId: hasPlayer ? preferences.favoritePlayerId : '',
    mode: preferences.mode === 'player' && !hasPlayer ? 'casual' : preferences.mode,
  }
}

export const PreferencesContext = createContext(null)

export function usePreferences() {
  const value = useContext(PreferencesContext)
  if (!value) throw new Error('usePreferences necesita PreferencesProvider')
  return value
}
