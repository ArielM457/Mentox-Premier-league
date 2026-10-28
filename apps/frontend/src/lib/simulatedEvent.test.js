import assert from 'node:assert/strict'
import test from 'node:test'
import { describeSimulatedEvent } from './simulatedEvent.js'
import { strings } from '../i18n/strings.js'

const metadata = {
  players: [{ player_id: '6', name: 'Jugador 6' }, { player_id: '7', name: 'Jugador 7' }],
  home_team: { team_id: 'home', name: 'MESSI Local' },
}

for (const language of ['es', 'en']) {
  test(`simulator pass stays explicitly attributed in ${language}`, () => {
    const text = describeSimulatedEvent({
      type: 'pass', team_id: 'home', player_id: '6', receiver_player_id: '7',
      outcome: 'success', distance_m: 12.4, launch_speed_m_s: 10,
      model_candidates: [{ status: 'temporal_candidate_only' }],
    }, metadata, strings[language].match.simulatedEvent)
    assert.match(text.title, /Jugador 6/)
    assert.match(text.title, /Jugador 7/)
    assert.match(text.evidence, /MESSI/)
    assert.match(text.evidence, /12.4 m/)
    assert.match(text.evidence, /36.0 km\/h/)
    assert.match(text.evidence, language === 'es' ? /sin verificar/ : /unverified/)
  })
}

test('unknown player and missing distance are not invented', () => {
  const text = describeSimulatedEvent({ type: 'pass', outcome: 'unknown' }, metadata, strings.es.match.simulatedEvent)
  assert.match(text.title, /sin identificar/)
  assert.doesNotMatch(text.evidence, /0.0 m|NaN/)
})
