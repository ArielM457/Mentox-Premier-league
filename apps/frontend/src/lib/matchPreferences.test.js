import assert from 'node:assert/strict'
import test from 'node:test'
import { preferencesForMatch } from './matchPreferences.js'

const metadata = { home_team: {team_id: 'messi-home'}, away_team: {team_id: 'messi-away'}, players: [{player_id: 'messi-7'}] }

test('preferencias antiguas de Ariel no bloquean la sesión MESSI', () => {
  const preferences = { mode: 'player', language: 'es', favoriteTeamId: 'aurora', favoritePlayerId: 'aurora-8' }
  const scoped = preferencesForMatch(preferences, metadata)
  assert.equal(scoped.mode, 'casual')
  assert.equal(scoped.favoriteTeamId, '')
  assert.equal(scoped.favoritePlayerId, '')
  assert.equal(preferences.favoriteTeamId, 'aurora')
})

test('preserva preferencias válidas del mismo partido', () => {
  const preferences = {mode: 'player', favoriteTeamId: 'messi-home', favoritePlayerId: 'messi-7'}
  assert.deepEqual(preferencesForMatch(preferences, metadata), preferences)
})
