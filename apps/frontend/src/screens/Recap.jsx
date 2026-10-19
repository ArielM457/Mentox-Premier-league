import { useEffect, useState } from 'react'
import { api } from '../api/client.js'
import { usePreferences } from '../app/preferences.js'
import { navigate, paths } from '../app/router.js'
import { useSession } from '../app/session.js'
import { useCatalog } from '../hooks/useCatalog.js'
import { formatMatchClock, momentIdOf } from '../lib/overlays.js'
import { AppShell } from '../components/layout/AppShell.jsx'
import { MatchScore } from '../components/match/MatchScore.jsx'
import { Button } from '../components/ui/Button.jsx'
import { ErrorNotice, LoadingCards } from '../components/ui/Feedback.jsx'
import { Icon } from '../components/ui/Icon.jsx'
import { PlayerIllustration } from '../components/ui/PlayerIllustration.jsx'

const TOP = 3

export function Recap({ matchId }) {
  const { t, preferences, apiPreferences } = usePreferences()
  const { data: catalog, error: catalogError, reload } = useCatalog()
  const { isAnalyst } = useSession()
  const match = catalog?.matches.find((m) => m.id === matchId)
  const [summary, setSummary] = useState(null)
  const [moments, setMoments] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!match) return undefined
    let active = true
    Promise.all([api.summary(matchId, apiPreferences), api.overlays(matchId, apiPreferences, match.durationMs)])
      .then(([record, batch]) => {
        if (!active) return
        const top = batch.overlays
          .filter((o) => !o.suppressed && o.kind !== 'player_quiet')
          .sort((a, b) => b.priority - a.priority || a.video_time_ms - b.video_time_ms)
          .slice(0, TOP)
          .sort((a, b) => a.video_time_ms - b.video_time_ms)
        setSummary(record)
        setMoments(top)
        setError(null)
      })
      .catch((err) => active && setError(err.message))
    return () => { active = false }
  }, [apiPreferences, match, matchId])

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
        {!match && !catalogError && <LoadingCards />}
        {match && (
          <MatchScore metadata={match.metadata} minute={t.matches.final} score={match.finalScore} status="FT" statusLabel={t.matches.status.FT} />
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
              <p>{summary.draft.explanation}</p>
              <div className="recap-meta">
                <span className={`editorial-status status-${summary.status}`}>{t.recap.status[summary.status]}</span>
                <span className="personal-note">{t.recap.personal(t.modes[preferences.mode].name)}</span>
              </div>
              {summary.status === 'pending' && <p className="recap-note">{t.recap.pendingNote}</p>}
              {isAnalyst && (
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
