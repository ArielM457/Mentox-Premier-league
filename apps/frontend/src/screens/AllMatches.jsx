import { useState } from 'react'
import { usePreferences } from '../app/preferences.js'
import { openMatch } from '../app/router.js'
import { involves, playerOf, useCatalog } from '../hooks/useCatalog.js'
import { AppShell } from '../components/layout/AppShell.jsx'
import { MatchCard } from '../components/match/MatchCard.jsx'
import { Button } from '../components/ui/Button.jsx'
import { ErrorNotice, LoadingCards } from '../components/ui/Feedback.jsx'
import { Icon } from '../components/ui/Icon.jsx'
import { LanguageSwitch } from '../components/ui/LanguageSwitch.jsx'

const FILTERS = ['LIVE', 'UPCOMING', 'FT']

export function AllMatches() {
  const { t, preferences } = usePreferences()
  const { data: catalog, error, reload } = useCatalog()
  const copy = t.matches
  const [query, setQuery] = useState('')
  const [filter, setFilter] = useState('LIVE')
  const [followOnly, setFollowOnly] = useState(false)
  const player = playerOf(catalog, preferences.favoritePlayerId)

  // La demo no tiene partidos programados: cada partido de la API se puede ver en vivo o como resumen.
  const byFilter = (status) => (status === 'UPCOMING' ? [] : catalog?.matches ?? [])
  const favoriteFirst = (list) =>
    [...list].sort((a, b) => Number(involves(b, preferences.favoriteTeamId)) - Number(involves(a, preferences.favoriteTeamId)))
  const visible = favoriteFirst(byFilter(filter)).filter(
    (match) =>
      (!followOnly || match.metadata.players.some((p) => p.player_id === player?.player_id)) &&
      `${match.metadata.home_team.name} ${match.metadata.away_team.name}`.toLowerCase().includes(query.toLowerCase()),
  )

  return (
    <AppShell active="matches">
      <section className="discover-content">
        <header className="page-header">
          <div>
            <span className="section-kicker">{copy.kicker}</span>
            <h1>{copy.title}</h1>
            <p>{copy.intro}</p>
          </div>
          <LanguageSwitch />
        </header>
        <label className="search-box">
          <Icon name="search" />
          <span className="sr-only">{copy.search}</span>
          <input onChange={(event) => setQuery(event.target.value)} placeholder={copy.search} value={query} />
        </label>
        <div className="all-match-controls">
          <div className="match-filters" role="group">
            {FILTERS.map((value) => (
              <button aria-pressed={filter === value} className={filter === value ? 'active' : ''} key={value} onClick={() => setFilter(value)} type="button">
                {value === 'LIVE' && <span className="live-dot" />}
                {copy.filters[value]}
                <small>{byFilter(value).length}</small>
              </button>
            ))}
          </div>
          {player && (
            <button aria-pressed={followOnly} className={`follow-player-filter ${followOnly ? 'active' : ''}`} onClick={() => setFollowOnly(!followOnly)} type="button">
              <Icon name="user" size={17} />
              <span>
                {copy.onlyPlayer} <strong>{player.name}</strong>
              </span>
              <i>{followOnly ? 'ON' : 'OFF'}</i>
            </button>
          )}
        </div>

        <ErrorNotice message={error && t.common.apiDown} onRetry={reload} retryLabel={t.common.retry} />

        <section className="discover-section all-matches-section">
          <div className="section-heading">
            <div>
              {filter === 'LIVE' && <span className="live-dot" />}
              <h2>{followOnly && player ? copy.relatedTo(player.name) : copy.headings[filter]}</h2>
            </div>
            <span>{copy.results(visible.length)}</span>
          </div>
          {!catalog && !error ? (
            <LoadingCards />
          ) : visible.length ? (
            <div className="match-grid">
              {visible.map((match) => (
                <MatchCard favorite={involves(match, preferences.favoriteTeamId)} key={match.id} match={match} onOpen={openMatch} status={filter} />
              ))}
            </div>
          ) : (
            <div className="empty-state">
              <Icon name="search" size={30} />
              <h3>{copy.emptyTitle}</h3>
              <p>{filter === 'UPCOMING' ? copy.emptyUpcoming : copy.emptyCopy}</p>
              <Button onClick={() => { setQuery(''); setFollowOnly(false); setFilter('LIVE') }}>{copy.clear}</Button>
            </div>
          )}
        </section>
      </section>
    </AppShell>
  )
}
