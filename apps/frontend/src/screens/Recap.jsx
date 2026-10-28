import { NarrativeCopy } from '../components/ui/NarrativeCopy.jsx'
import { useEffect, useMemo, useState } from 'react'
import { api } from '../api/client.js'
import { preferencesForMatch, usePreferences } from '../app/preferences.js'
import { navigate, paths } from '../app/router.js'
import { useCatalog } from '../hooks/useCatalog.js'
import { formatMatchClock, momentIdOf } from '../lib/overlays.js'
import { recordExperience } from '../lib/experience.js'
import { AppShell } from '../components/layout/AppShell.jsx'
import { MatchScore } from '../components/match/MatchScore.jsx'
import { Button } from '../components/ui/Button.jsx'
import { ErrorNotice, LoadingCards } from '../components/ui/Feedback.jsx'
import { Icon } from '../components/ui/Icon.jsx'
import { PlayerIllustration } from '../components/ui/PlayerIllustration.jsx'

const TOP = 3
const SUMMARY_TYPES = ['short', 'extended', 'player_danger']

export function Recap({ matchId }) {
  const { t, preferences, apiPreferences } = usePreferences()
  const { data: catalog, error: catalogError, reload } = useCatalog()
  const match = catalog?.matches.find((m) => m.id === matchId)
  const matchApiPreferences = useMemo(
    () => match ? preferencesForMatch(apiPreferences, match.metadata) : apiPreferences,
    [apiPreferences, match],
  )
  const [summary, setSummary] = useState(null)
  const [moments, setMoments] = useState(null)
  const [error, setError] = useState(null)
  const [summaryType, setSummaryType] = useState('short')
  const matchPlayers = match?.metadata.players ?? []
  const preferredPlayer = matchPlayers.some((player) => player.player_id === preferences.favoritePlayerId)
    ? preferences.favoritePlayerId
    : matchPlayers[0]?.player_id ?? ''
  const [summaryPlayerId, setSummaryPlayerId] = useState('')
  const selectedPlayerId = matchPlayers.some((player) => player.player_id === summaryPlayerId)
    ? summaryPlayerId
    : preferredPlayer

  useEffect(() => {
    if (!match) return undefined
    recordExperience(matchId, 'recap')
    let active = true
    if (summaryType === 'player_danger' && !selectedPlayerId) return undefined
    const home = match.metadata.home_team
    const away = match.metadata.away_team
    const mockSummary = {
      is_mock: true,
      status: 'approved',
      draft: {
        headline: t.recap.mockHeadline(
          home.name,
          match.finalScore[home.team_id] ?? 0,
          away.name,
          match.finalScore[away.team_id] ?? 0,
        ),
        explanation: t.recap.mockExplanation(summaryType),
      },
    }
    Promise.all([
      api.summary(matchId, matchApiPreferences, { type: summaryType, playerId: summaryType === 'player_danger' ? selectedPlayerId : null }).catch(() => mockSummary),
      api.overlays(matchId, matchApiPreferences, match.durationMs).catch(() => ({ overlays: [] })),
    ])
      .then(([record, batch]) => {
        if (!active) return
        const playerEventIds = new Set(
          match.events.filter((event) => event.player_id === selectedPlayerId).map((event) => event.event_id),
        )
        const top = batch.overlays
          .filter((o) => !o.suppressed && o.kind !== 'player_quiet')
          .filter((o) => summaryType !== 'short' || o.kind === 'goal')
          .filter((o) => summaryType !== 'player_danger' || (
            ['goal', 'shot'].includes(o.kind) && o.source_event_ids.some((id) => playerEventIds.has(id))
          ))
          .sort((a, b) => b.priority - a.priority || a.video_time_ms - b.video_time_ms)
          .slice(0, summaryType === 'extended' ? TOP : batch.overlays.length)
          .sort((a, b) => a.video_time_ms - b.video_time_ms)
        setSummary(record)
        setMoments(top)
        setError(null)
      })
      .catch((err) => active && setError(err.message))
    return () => { active = false }
  }, [match, matchApiPreferences, matchId, selectedPlayerId, summaryType, t.recap])

  return (
    <AppShell active="matches">
      <section className="recap-content">
        <header className="page-header">
          <div>
            <span className="section-kicker">{t.recap.kicker}</span>
            <h1>{t.recap.title(moments?.length ?? TOP)}</h1>
          </div>
          {match && (
            <Button variant="ghost" onClick={() => navigate(paths.match(matchId))}>
              <Icon name="replay" /> {t.match.replay}
            </Button>
          )}
        </header>
        <ErrorNotice message={(catalogError && t.common.apiDown) || error} onRetry={reload} retryLabel={t.common.retry} />
        {(!catalog || (match && !summary && !error)) && !catalogError && <LoadingCards />}
        {catalog && !match && <ErrorNotice message={t.moment.notFound} />}
        {match && (
          <MatchScore metadata={match.metadata} minute={t.matches.final} score={match.finalScore} status="FT" statusLabel={t.matches.status.FT} />
        )}

        {match && (
          <section className="summary-picker" aria-labelledby="summary-picker-title">
            <div>
              <span className="section-kicker">{t.recap.chooseKicker}</span>
              <h2 id="summary-picker-title">{t.recap.chooseTitle}</h2>
            </div>
            <div className="summary-type-grid">
              {SUMMARY_TYPES.map((type) => (
                <button aria-pressed={summaryType === type} className={summaryType === type ? 'selected' : ''} key={type} onClick={() => setSummaryType(type)} type="button">
                  <Icon name={type === 'short' ? 'ball' : type === 'extended' ? 'match' : 'user'} />
                  <span><strong>{t.recap.types[type].name}</strong><small>{t.recap.types[type].description}</small></span>
                </button>
              ))}
            </div>
            {summaryType === 'player_danger' && (
              <label className="summary-player-select">
                <span>{t.recap.choosePlayer}</span>
                <select value={selectedPlayerId} onChange={(event) => setSummaryPlayerId(event.target.value)}>
                  {matchPlayers.map((player) => <option key={player.player_id} value={player.player_id}>{player.name}</option>)}
                </select>
              </label>
            )}
          </section>
        )}

        {summary && (
          <section className="recap-hero">
            <div className="recap-art">
              <span className="celebration-number">{moments?.length ?? 0}</span>
              <PlayerIllustration compact />
            </div>
            <div>
              <span className="section-kicker">
                <Icon name="spark" size={16} /> {t.recap.summaryKicker}
              </span>
              <h2>{summary.draft.headline}</h2>
              <NarrativeCopy text={summary.draft.explanation} />
              <div className="recap-meta">
                <span className={`editorial-status status-${summary.status}`}>{summary.is_mock ? t.recap.mockLabel : t.recap.status[summary.status]}</span>
                <span className="personal-note">{t.recap.personal(t.modes[preferences.mode].name)}</span>
              </div>
              {summary.status === 'pending' && <p className="recap-note">{t.recap.pendingNote}</p>}
              {!summary.is_mock && (
                <Button variant="lime" onClick={() => navigate(paths.editorial())}>
                  <Icon name="shield" size={17} /> {t.recap.goReview}
                </Button>
              )}
            </div>
          </section>
        )}

        {moments && (
          <section className="recap-moments">
            <div className="section-heading">
              <div>
                <h2>{t.recap.top(moments.length)}</h2>
              </div>
              <span>{t.recap.select}</span>
            </div>
            <div className="recap-list">
              {moments.map((m, index) => (
                <button key={m.message_id} onClick={() => navigate(paths.moment(matchId, momentIdOf(m)))} type="button">
                  <span className="moment-number">{index + 1}</span>
                  <span className="moment-time">{formatMatchClock(m, t.match.period)}</span>
                  <div>
                    <strong>{m.headline}</strong>
                    <small>{m.explanation}</small>
                  </div>
                  <Icon name="arrow" />
                </button>
              ))}
            </div>
          </section>
        )}
      </section>
    </AppShell>
  )
}
