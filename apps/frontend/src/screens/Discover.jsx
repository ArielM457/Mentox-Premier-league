import { usePreferences } from '../app/preferences.js'
import { navigate, openMatch, paths } from '../app/router.js'
import { involves, playerOf, teamOf, useCatalog } from '../hooks/useCatalog.js'
import { AppShell } from '../components/layout/AppShell.jsx'
import { MatchCard } from '../components/match/MatchCard.jsx'
import { Button } from '../components/ui/Button.jsx'
import { ErrorNotice, LoadingCards } from '../components/ui/Feedback.jsx'
import { Icon } from '../components/ui/Icon.jsx'
import { LanguageSwitch } from '../components/ui/LanguageSwitch.jsx'

export function Discover() {
  const { t, preferences } = usePreferences()
  const { data: catalog, error, reload } = useCatalog()
  const copy = t.discover
  const club = teamOf(catalog, preferences.favoriteTeamId)
  const player = playerOf(catalog, preferences.favoritePlayerId)
  const playerMatches = player ? catalog.matches.filter((m) => m.metadata.players.some((p) => p.player_id === player.player_id)) : []
  const actions = player ? catalog.actions[player.player_id] ?? 0 : 0
  const liveMatches = catalog?.matches.filter((match) => match.status === 'LIVE') ?? []
  const recentMatch = catalog?.matches.find((match) => match.status === 'FT')
  const upcomingMatch = catalog?.matches.find((match) => match.status === 'UPCOMING')

  return (
    <AppShell active="discover">
      <section className="discover-content">
        <header className="page-header">
          <div>
            <span className="section-kicker">{copy.kicker}</span>
            <h1>{copy.greeting()}</h1>
          </div>
          <LanguageSwitch />
        </header>

        <ErrorNotice message={error && t.common.apiDown} onRetry={reload} retryLabel={t.common.retry} />
        {!catalog && !error && <LoadingCards />}

        {catalog && liveMatches.length > 0 && (
          <section className="favorite-club-section live-home-section">
            <div className="section-heading">
              <div>
                <span className="favorite-club-icon">
                  <Icon name="broadcast" size={19} />
                </span>
                <div>
                  <small>{t.matches.kicker}</small>
                  <h2>{t.matches.headings.LIVE}</h2>
                </div>
              </div>
              <button onClick={() => navigate(paths.matches())} type="button">
                {copy.seeAll} <Icon name="arrow" size={15} />
              </button>
            </div>
            {liveMatches.length ? (
              <div className="favorite-match-row">
                {liveMatches.map((match) => (
                  <MatchCard favorite={Boolean(club)} key={match.id} match={match} onOpen={openMatch} status="LIVE" />
                ))}
              </div>
            ) : (
              <div className="favorite-filter-empty">
                <Icon name="match" size={22} />
                <span>
                  {copy.noClubMatches(club.name)}
                  <small>{copy.exploreDemo}</small>
                </span>
              </div>
            )}
          </section>
        )}

        {catalog && (recentMatch || upcomingMatch) && (
          <section className="discover-fixtures-section">
            <div className="section-heading">
              <div>
                <span className="favorite-club-icon"><Icon name="match" size={18} /></span>
                <div>
                  <small>{copy.scheduleKicker}</small>
                  <h2>{copy.scheduleTitle}</h2>
                </div>
              </div>
              <button onClick={() => navigate(paths.matches())} type="button">
                {copy.seeAll} <Icon name="arrow" size={15} />
              </button>
            </div>
            <div className="fixture-pair">
              {recentMatch && (
                <article>
                  <span>{copy.latestMatch}</span>
                  <MatchCard match={recentMatch} onOpen={openMatch} status="FT" />
                </article>
              )}
              {upcomingMatch && (
                <article>
                  <span>{copy.nextMatch}</span>
                  <MatchCard match={upcomingMatch} onOpen={openMatch} status="UPCOMING" />
                </article>
              )}
            </div>
          </section>
        )}

        {player && playerMatches.length > 0 && (
          <section className="favorite-club-section player-matches-section">
            <div className="section-heading">
              <div>
                <span className="favorite-club-icon player-icon">
                  <Icon name="user" size={17} />
                </span>
                <div>
                  <small>{copy.favoritePlayer}</small>
                  <h2>{copy.playerMatches(player.name)}</h2>
                </div>
              </div>
              <button onClick={() => navigate(paths.matches())} type="button">
                {copy.seeAll} <Icon name="arrow" size={15} />
              </button>
            </div>
            <div className="favorite-match-row">
              {playerMatches.map((match) => (
                <MatchCard favorite={club ? involves(match, club.team_id) : false} key={match.id} match={match} onOpen={openMatch} status="FT" />
              ))}
            </div>
          </section>
        )}

        {player && (
          <section className="player-insight-section">
            <div className="section-heading">
              <div>
                <span className="favorite-club-icon">
                  <Icon name="user" size={17} />
                </span>
                <div>
                  <small>{copy.tracking}</small>
                  <h2>{copy.playerInfo}</h2>
                </div>
              </div>
              <button onClick={() => navigate(paths.profile())} type="button">
                {copy.changePlayer}
              </button>
            </div>
            <div className="insight-banner">
              <div className="insight-art">
                <span>{actions}</span>
                <small>{copy.actions}</small>
              </div>
              <div>
                <span className="section-kicker">{copy.playerKicker}</span>
                <h2>{copy.playerQuestion(player.name)}</h2>
                <p>{copy.playerCopy(player.name, actions)}</p>
                <span className="favorite-player-label">
                  <Icon name="user" size={14} /> {copy.following(player.name)}
                </span>
                <Button onClick={() => navigate(paths.matches())}>
                  {copy.watchPlayer(player.name)} <Icon name="arrow" size={17} />
                </Button>
              </div>
              <Icon name="spark" size={40} />
            </div>
          </section>
        )}
      </section>
    </AppShell>
  )
}
