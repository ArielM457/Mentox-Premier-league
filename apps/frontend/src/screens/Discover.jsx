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
  const clubMatches = club ? catalog.matches.filter((m) => involves(m, club.team_id)) : []
  const playerMatches = player ? catalog.matches.filter((m) => m.metadata.players.some((p) => p.player_id === player.player_id)) : []
  const actions = player ? catalog.actions[player.player_id] ?? 0 : 0

  return (
    <AppShell active="discover">
      <section className="discover-content">
        <header className="page-header">
          <div>
            <span className="section-kicker">{copy.kicker}</span>
            <h1>{copy.greeting()}</h1>
            <p>
              {club ? copy.firstClub(club.name) : copy.exploreAll}
              {copy.insightsIn} <strong>{t.modes[preferences.mode].name}</strong>.
            </p>
          </div>
          <LanguageSwitch />
        </header>

        <ErrorNotice message={error && t.common.apiDown} onRetry={reload} retryLabel={t.common.retry} />
        {!catalog && !error && <LoadingCards />}

        {catalog && (
          <section className="favorite-club-section">
            <div className="section-heading">
              <div>
                <span className="favorite-club-icon">
                  <Icon name="spark" size={17} />
                </span>
                <div>
                  <small>{club ? copy.favoriteClub : t.matches.kicker}</small>
                  <h2>{club ? copy.clubMatches(club.name) : t.matches.headings.LIVE}</h2>
                </div>
              </div>
              <button onClick={() => navigate(paths.matches())} type="button">
                {copy.seeAll} <Icon name="arrow" size={15} />
              </button>
            </div>
            {(club ? clubMatches : catalog.matches).length ? (
              <div className="favorite-match-row">
                {(club ? clubMatches : catalog.matches).map((match) => (
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
