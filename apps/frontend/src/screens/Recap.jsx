import { NarrativeCopy } from '../components/ui/NarrativeCopy.jsx'
import { useEffect, useMemo, useState } from 'react'
import { api } from '../api/client.js'
import { preferencesForMatch, usePreferences } from '../app/preferences.js'
import { navigate, paths } from '../app/router.js'
import { useCatalog } from '../hooks/useCatalog.js'
import { momentIdOf } from '../lib/overlays.js'
import { recordExperience } from '../lib/experience.js'
import { filterSummaryMoments } from '../lib/summaryMoments.js'
import { AppShell } from '../components/layout/AppShell.jsx'
import { InsightsPanel, MomentWorkspace } from '../components/match/LiveExperiencePanels.jsx'
import { LiveSummarySelector } from '../components/match/LiveSummarySelector.jsx'
import { MatchScore } from '../components/match/MatchScore.jsx'
import { Button } from '../components/ui/Button.jsx'
import { ErrorNotice, LoadingCards } from '../components/ui/Feedback.jsx'
import { Icon } from '../components/ui/Icon.jsx'

const TOP = 3

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
  const [selectedMomentId, setSelectedMomentId] = useState(null)
  const matchPlayers = match?.metadata.players ?? []
  const preferredPlayer = matchPlayers.some((player) => player.player_id === preferences.favoritePlayerId)
    ? preferences.favoritePlayerId
    : matchPlayers[0]?.player_id ?? ''
  const [summaryPlayerId, setSummaryPlayerId] = useState('')
  const selectedPlayerId = matchPlayers.some((player) => player.player_id === summaryPlayerId)
    ? summaryPlayerId
    : preferredPlayer
  const summaryMoments = useMemo(() => filterSummaryMoments({
    events: match?.events ?? [],
    moments: moments ?? [],
    playerId: selectedPlayerId,
    type: summaryType,
  }), [match?.events, moments, selectedPlayerId, summaryType])
  const selectedMoment = summaryMoments.find((moment) => moment.message_id === selectedMomentId) ?? summaryMoments[0] ?? null

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
        setSummary(record)
        setMoments(batch.overlays)
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
            <h1>{t.recap.title(summaryMoments.length || TOP)}</h1>
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
          <LiveSummarySelector
            onPlayerChange={setSummaryPlayerId}
            onTypeChange={setSummaryType}
            playerId={selectedPlayerId}
            players={matchPlayers}
            type={summaryType}
          />
        )}

        {summary && (
          <section className="recap-hero">
            <div className="recap-art">
              <img alt="" className="recap-professional-art" src="/images/match-recap-professional.png" />
              <span className="celebration-number">{summaryMoments.length}</span>
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

        {moments && match && (
          <section className="match-summary recap-analysis">
            <MomentWorkspace
              events={match.events}
              matchId={matchId}
              metadata={match.metadata}
              moment={selectedMoment}
              moments={summaryMoments}
              onOpen={(moment) => navigate(paths.moment(matchId, momentIdOf(moment)))}
              onSelect={(moment) => setSelectedMomentId(moment.message_id)}
            />
            <InsightsPanel
              events={match.events}
              metadata={match.metadata}
              moments={summaryMoments}
              onSelect={(moment) => setSelectedMomentId(moment.message_id)}
              selectedId={selectedMoment?.message_id}
            />
          </section>
        )}
      </section>
    </AppShell>
  )
}
