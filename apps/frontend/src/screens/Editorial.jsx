import { useEffect, useMemo, useRef, useState } from 'react'
import { api } from '../api/client.js'
import { usePreferences } from '../app/preferences.js'
import { navigate, paths } from '../app/router.js'
import { CommunityPanel } from '../components/community/CommunityPanel.jsx'
import { AppShell } from '../components/layout/AppShell.jsx'
import { Assistant } from '../components/match/Assistant.jsx'
import { Button } from '../components/ui/Button.jsx'
import { ErrorNotice, LoadingScreen } from '../components/ui/Feedback.jsx'
import { Icon } from '../components/ui/Icon.jsx'
import { NarrativeCopy } from '../components/ui/NarrativeCopy.jsx'
import { teamBranding } from '../data/branding.js'
import { playerOf, teamOf, useCatalog } from '../hooks/useCatalog.js'

const FILTERS = ['all', 'LIVE', 'FT', 'UPCOMING']
const EMPTY_CARDS = []

function scoreOf(match, teamId) {
  return Number(match.finalScore?.[teamId] ?? 0)
}

function winnerId(match) {
  const home = scoreOf(match, match.metadata.home_team.team_id)
  const away = scoreOf(match, match.metadata.away_team.team_id)
  if (home === away) return null
  return home > away ? match.metadata.home_team.team_id : match.metadata.away_team.team_id
}

export function Editorial() {
  const { t, apiPreferences } = usePreferences()
  const { data: catalog, error: catalogError, reload } = useCatalog()
  const copy = t.editorial.library
  const [library, setLibrary] = useState({ key: null, cards: [], error: null })
  const [query, setQuery] = useState('')
  const [filter, setFilter] = useState('all')
  const requestKey = useMemo(() => catalog
    ? `${catalog.matches.map((match) => match.id).join(',')}|${JSON.stringify(apiPreferences)}`
    : null, [catalog, apiPreferences])
  const loading = !catalogError && (!catalog || library.key !== requestKey)
  const cards = library.key === requestKey ? library.cards : EMPTY_CARDS
  const error = library.key === requestKey ? library.error : null

  useEffect(() => {
    if (!catalog) return
    let active = true
    Promise.all(catalog.matches.map(async (match) => {
      const record = await api.summary(match.id, apiPreferences)
      const tallies = await api.communityTallies(match.id).catch(() => [])
      const tally = tallies.find((item) => item.draft_id === record.draft.draft_id)?.tally ?? { approve: 0, reject: 0, total: 0 }
      return { match, record, tally }
    }))
      .then((items) => { if (active) setLibrary({ key: requestKey, cards: items, error: null }) })
      .catch((err) => { if (active) setLibrary({ key: requestKey, cards: [], error: err.message }) })
    return () => { active = false }
  }, [catalog, apiPreferences, requestKey])

  const visible = useMemo(() => {
    const needle = query.trim().toLocaleLowerCase()
    return cards.filter(({ match, record }) => {
      const matchesFilter = filter === 'all' || match.status === filter
      const haystack = `${match.metadata.home_team.name} ${match.metadata.away_team.name} ${record.draft.headline} ${record.draft.explanation}`.toLocaleLowerCase()
      return matchesFilter && (!needle || haystack.includes(needle))
    })
  }, [cards, filter, query])

  return (
    <AppShell active="editorial">
      <section className="profile-content editorial-content community-library">
        <header className="page-header">
          <div>
            <span className="section-kicker">{copy.kicker}</span>
            <h1>{copy.title}</h1>
            <p>{copy.intro}</p>
          </div>
        </header>
        <ErrorNotice message={(catalogError && t.common.apiDown) || error} onRetry={catalogError ? reload : undefined} retryLabel={t.common.retry} />

        <div className="community-library-tools">
          <label className="community-search">
            <Icon name="search" size={18} />
            <span className="sr-only">{copy.search}</span>
            <input onChange={(event) => setQuery(event.target.value)} placeholder={copy.search} value={query} />
          </label>
          <div className="community-filters" role="group" aria-label={copy.filters}>
            {FILTERS.map((key) => (
              <button aria-pressed={filter === key} className={filter === key ? 'active' : ''} key={key} onClick={() => setFilter(key)} type="button">
                {copy.filter[key]}
              </button>
            ))}
          </div>
        </div>

        {loading && <LoadingScreen />}
        {!loading && visible.length === 0 && <p className="community-library-empty">{copy.empty}</p>}
        <div className="community-match-list">
          {visible.map((item) => <SummaryMatchCard item={item} key={`${item.match.id}/${item.record.draft.draft_id}`} copy={copy} />)}
        </div>
      </section>
    </AppShell>
  )
}

function SummaryMatchCard({ item, copy }) {
  const { match, record, tally } = item
  const home = match.metadata.home_team
  const away = match.metadata.away_team
  const homeBrand = teamBranding(home)
  const awayBrand = teamBranding(away)
  const winner = winnerId(match)
  return (
    <article className="community-match-card">
      <div className="community-match-visual" style={{ '--home-color': homeBrand.color, '--away-color': awayBrand.color }}>
        <div className={`community-team-side home ${winner === home.team_id ? 'winner' : ''}`}>
          {homeBrand.logo ? <img alt="" src={homeBrand.logo} /> : <strong>{homeBrand.short}</strong>}
          <span>{home.name}</span>
        </div>
        <div className={`community-team-side away ${winner === away.team_id ? 'winner' : ''}`}>
          {awayBrand.logo ? <img alt="" src={awayBrand.logo} /> : <strong>{awayBrand.short}</strong>}
          <span>{away.name}</span>
        </div>
        <div className="community-match-score" aria-label={`${home.name} ${scoreOf(match, home.team_id)}, ${away.name} ${scoreOf(match, away.team_id)}`}>
          <b>{scoreOf(match, home.team_id)}</b><i>–</i><b>{scoreOf(match, away.team_id)}</b>
        </div>
      </div>
      <div className="community-match-overview">
        <div className="community-match-heading">
          <div>
            <span className={`editorial-status status-${record.status}`}>{copy.status[record.status]}</span>
            <h2>{record.draft.headline}</h2>
          </div>
          <span className="community-match-state">{copy.filter[match.status]}</span>
        </div>
        <div className="community-overview-copy"><NarrativeCopy text={record.draft.explanation} /></div>
        <div className="community-card-footer">
          <div className="community-card-votes" aria-label={copy.votesLabel}>
            <span><Icon name="thumbUp" size={17} /> {tally.approve}</span>
            <span><Icon name="thumbDown" size={17} /> {tally.reject}</span>
          </div>
          <Button onClick={() => navigate(paths.editorialDetail(match.id, record.draft.draft_id))}>
            {copy.open} <Icon name="arrow" size={17} />
          </Button>
        </div>
      </div>
    </article>
  )
}

export function EditorialDetail({ matchId, draftId }) {
  const { t, apiPreferences, preferences } = usePreferences()
  const { data: catalog, error: catalogError, reload } = useCatalog()
  const copy = t.editorial.detail
  const match = catalog?.matches.find((item) => item.id === matchId)
  const [record, setRecord] = useState(null)
  const [preview, setPreview] = useState(null)
  const [error, setError] = useState(null)
  const timeRef = useRef(match?.durationMs ?? 0)

  useEffect(() => {
    timeRef.current = match?.durationMs ?? 0
  }, [match?.durationMs])

  useEffect(() => {
    if (!match) return
    let active = true
    Promise.all([api.summary(matchId, apiPreferences), api.preview(matchId).catch(() => null)])
      .then(([summary, prematch]) => {
        if (!active) return
        if (summary.draft.draft_id !== draftId) throw new Error(copy.notFound)
        setRecord(summary)
        setPreview(prematch)
        setError(null)
      })
      .catch((err) => { if (active) setError(err.message) })
    return () => { active = false }
  }, [match, matchId, draftId, apiPreferences, copy.notFound])

  if (!catalog && !catalogError) return <AppShell active="editorial"><LoadingScreen /></AppShell>
  if (!match) return <AppShell active="editorial"><ErrorNotice message={catalogError || copy.notFound} onRetry={reload} retryLabel={t.common.retry} /></AppShell>

  const home = match.metadata.home_team
  const away = match.metadata.away_team
  const winner = winnerId(match)
  const featured = winner === away.team_id ? away : home
  const featuredBrand = teamBranding(featured)

  return (
    <AppShell active="editorial">
      <section className="profile-content editorial-content community-review-detail">
        <button className="community-detail-back" onClick={() => navigate(paths.editorial())} type="button"><Icon name="back" size={18} /> {copy.back}</button>
        <ErrorNotice message={catalogError || error} onRetry={catalogError ? reload : undefined} retryLabel={t.common.retry} />
        {!record ? <LoadingScreen /> : (
          <div className="community-detail-grid">
            <article className="community-detail-story">
              <div className="community-detail-team" style={{ '--team-color': featuredBrand.color }}>
                {featuredBrand.logo && <img alt={featured.name} src={featuredBrand.logo} />}
                <div><span>{copy.featured}</span><strong>{featured.name}</strong></div>
                <div className="community-detail-score"><b>{scoreOf(match, home.team_id)}</b><i>–</i><b>{scoreOf(match, away.team_id)}</b></div>
              </div>
              <div className="community-detail-summary">
                <span className={`editorial-status status-${record.status}`}>{t.editorial.library.status[record.status]}</span>
                <h1>{record.draft.headline}</h1>
                <NarrativeCopy text={record.draft.explanation} />
              </div>
              <section className="community-tactics">
                <span className="section-kicker">{copy.tacticsKicker}</span>
                <h2>{copy.tactics}</h2>
                <div>
                  {(preview?.simulations ?? []).slice(0, 4).map((simulation) => (
                    <article key={simulation.simulation_id}>
                      <strong>{simulation.title}</strong>
                      <p>{simulation.summary}</p>
                    </article>
                  ))}
                </div>
              </section>
            </article>
            <aside className="community-detail-side">
              <Assistant
                canExplore={false}
                favoriteClub={teamOf(catalog, preferences.favoriteTeamId)}
                favoritePlayer={playerOf(catalog, preferences.favoritePlayerId)}
                matchId={matchId}
                onExplore={() => {}}
                timeRef={timeRef}
              />
              <CommunityPanel compact matchId={matchId} record={record} showSummary={false} />
            </aside>
          </div>
        )}
      </section>
    </AppShell>
  )
}
