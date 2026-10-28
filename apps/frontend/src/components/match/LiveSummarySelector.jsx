import { usePreferences } from '../../app/preferences.js'
import { SUMMARY_TYPES } from '../../lib/summaryMoments.js'

export function LiveSummarySelector({ players, playerId, type, onPlayerChange, onTypeChange }) {
  const { t } = usePreferences()

  return (
    <section className="summary-picker live-summary-picker compact-summary-picker" aria-labelledby="live-summary-title">
      <label className="summary-mode-select">
        <span id="live-summary-title">{t.recap.chooseTitle}</span>
        <select value={type} onChange={(event) => onTypeChange(event.target.value)}>
          {SUMMARY_TYPES.map((value) => (
            <option key={value} value={value}>
              {t.recap.types[value].name} — {t.recap.types[value].description}
            </option>
          ))}
        </select>
      </label>
      {type === 'player_danger' && (
        <label className="summary-player-select compact-player-select">
          <span>{t.recap.choosePlayer}</span>
          <select value={playerId} onChange={(event) => onPlayerChange(event.target.value)}>
            {players.map((player) => <option key={player.player_id} value={player.player_id}>{player.name}</option>)}
          </select>
        </label>
      )}
    </section>
  )
}
