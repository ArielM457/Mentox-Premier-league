import { usePreferences } from '../app/preferences.js'
import { navigate, openMatch, paths } from '../app/router.js'
import { involves, playerOf, teamOf, useCatalog } from '../hooks/useCatalog.js'
import { AppShell } from '../components/layout/AppShell.jsx'
import { MatchCard } from '../components/match/MatchCard.jsx'
import { Button } from '../components/ui/Button.jsx'
import { ErrorNotice, LoadingCards } from '../components/ui/Feedback.jsx'
import { Icon } from '../components/ui/Icon.jsx'
import { LanguageSwitch } from '../components/ui/LanguageSwitch.jsx'
import { playerPhoto, teamBranding } from '../data/branding.js'

// Inicio: primero el acceso a los partidos de la demo; después el club y el jugador favoritos,
// con un estado vacío que invita a elegirlos.
export function Discover() {
  const { t, preferences } = usePreferences()
  const { data: catalog, error, reload } = useCatalog()
  const copy = t.discover
  const club = teamOf(catalog, preferences.favoriteTeamId)
  const player = playerOf(catalog, preferences.favoritePlayerId)
  const clubMatches = club ? catalog.matches.filter((match) => involves(match, club.team_id)) : []
  const playerMatches = player ? catalog.matches.filter((match) => match.metadata.players.some((item) => item.player_id === player.player_id)) : []
  const actions = player ? catalog.actions[player.player_id] ?? 0 : 0
  const brand = club ? teamBranding(club) : null
  const liveMatches = catalog?.matches.filter((match) => match.status === 'LIVE') ?? []
  const recentMatch = catalog?.matches.find((match) => match.status === 'FT')
  const upcomingMatch = catalog?.matches.find((match) => match.status === 'UPCOMING')

  return (
    <AppShell active="discover">
      <section className="discover-content">
        <header className="page-header"><div><h1>{copy.welcome}</h1><p>{copy.subtitle}</p></div><LanguageSwitch /></header>
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
            <div className="favorite-match-row">
              {liveMatches.map((match) => (
                <MatchCard favorite={club ? involves(match, club.team_id) : false} key={match.id} match={match} onOpen={openMatch} status="LIVE" />
              ))}
            </div>
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

        {catalog && <>
          <section className="favorite-club-section home-club-section">
            <div className="section-heading">
              <div>{brand?.logo ? <img className="home-club-logo" src={brand.logo} alt="" /> : <Icon name="match" size={28} />}<div>{club && <small>{copy.favoriteClub}</small>}<h2>{club?.name || copy.favoriteClub}</h2></div></div>
              {club && <button onClick={() => navigate(paths.profile())} type="button">{copy.editFavorites}<Icon name="arrow" size={16} /></button>}
            </div>
            {!club ? <FavoriteEmpty icon="match" title={copy.chooseClubTitle} description={copy.chooseClubCopy} action={copy.chooseClubAction} /> : clubMatches.length ? <div className="favorite-match-row">{clubMatches.map((match) => <MatchCard favorite key={match.id} match={match} onOpen={openMatch} status={match.status} />)}</div> : <p className="muted-copy">{copy.noClubMatches(club.name)}</p>}
          </section>
          <section className="favorite-club-section player-matches-section home-player-section">
            <div className="section-heading"><div><Icon name="user" size={28} /><div>{player && <small>{copy.favoritePlayer}</small>}<h2>{player?.name || copy.favoritePlayer}</h2></div></div>{player && <button onClick={() => navigate(paths.profile())} type="button">{copy.changePlayer}<Icon name="arrow" size={16} /></button>}</div>
            {!player ? <FavoriteEmpty icon="user" title={copy.choosePlayerTitle} description={copy.choosePlayerCopy} action={copy.choosePlayerAction} /> : <>
              <div className="home-player-summary"><img src={playerPhoto(player.player_id)} alt="" /><div><strong>{copy.following(player.name)}</strong><p>{copy.playerCopy(player.name, actions)}</p><span className="player-action-count">{actions} {copy.actions}</span></div></div>
              {playerMatches.length > 0 && <div className="favorite-match-row">{playerMatches.map((match) => <MatchCard favorite={club ? involves(match, club.team_id) : false} key={match.id} match={match} onOpen={openMatch} status={match.status} />)}</div>}
            </>}
          </section>
        </>}
      </section>
    </AppShell>
  )
}

function FavoriteEmpty({ icon, title, description, action }) {
  return <div className="favorite-empty"><span className="empty-icon"><Icon name={icon} size={28} /></span><h3>{title}</h3><p>{description}</p><Button onClick={() => navigate(paths.profile())}>{action}<Icon name="arrow" size={17} /></Button></div>
}
