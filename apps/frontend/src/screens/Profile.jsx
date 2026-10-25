import { useState } from 'react'
import { usePreferences } from '../app/preferences.js'
import { navigate, paths } from '../app/router.js'
import { MODE_ART, playerPhoto, teamBranding } from '../data/branding.js'
import { useCatalog } from '../hooks/useCatalog.js'
import { loadExperience } from '../lib/experience.js'
import { AppShell } from '../components/layout/AppShell.jsx'
import { Button } from '../components/ui/Button.jsx'
import { ErrorNotice } from '../components/ui/Feedback.jsx'
import { Icon } from '../components/ui/Icon.jsx'

const LANGUAGES = [['en', 'EN', 'English'], ['es', 'ES', 'Español']]
const LEVEL_ICONS = { simple: 'spark', normal: 'match', advanced: 'chart' }

export function Profile() {
  const { t, preferences, update } = usePreferences()
  const { data: catalog, error, reload } = useCatalog()
  const copy = t.profile
  const [draft, setDraft] = useState(preferences)
  const [saved, setSaved] = useState(false)
  const [experience] = useState(loadExperience)
  const set = (changes) => {
    setSaved(false)
    setDraft((current) => ({ ...current, ...changes }))
  }
  const players = catalog?.players.filter((p) => !draft.favoriteTeamId || p.team_id === draft.favoriteTeamId) ?? []
  const playerName = catalog?.players.find((p) => p.player_id === draft.favoritePlayerId)?.name ?? t.common.none
  const invalidMode = draft.mode === 'player' && !draft.favoritePlayerId
  const matchHistory = experience.viewedMatches
    .map((entry) => ({ ...entry, match: catalog?.matches.find((match) => match.id === entry.matchId) }))
    .filter((entry) => entry.match)
  const recapHistory = experience.viewedRecaps
    .map((entry) => ({ ...entry, match: catalog?.matches.find((match) => match.id === entry.matchId) }))
    .filter((entry) => entry.match)
  const playerMatches = draft.favoritePlayerId
    ? catalog?.matches.filter((match) => match.metadata.players.some((player) => player.player_id === draft.favoritePlayerId)) ?? []
    : []

  function save() {
    if (invalidMode) return
    update({ ...draft, onboarded: true })
    setSaved(true)
  }

  return (
    <AppShell active="profile">
      <section className="profile-content">
        <header className="page-header">
          <div>
            <span className="section-kicker">{copy.kicker}</span>
            <h1>{copy.title}</h1>
            <p>{copy.intro}</p>
          </div>
        </header>
        <ErrorNotice message={error && t.common.apiDown} onRetry={reload} retryLabel={t.common.retry} />
        <section className="experience-grid">
          <ExperienceList copy={copy.history} empty={copy.emptyHistory} entries={matchHistory} onOpen={(id) => navigate(paths.match(id))} />
          <ExperienceList copy={copy.summaries} empty={copy.emptySummaries} entries={recapHistory} onOpen={(id) => navigate(paths.recap(id))} />
          <article className="experience-panel">
            <h2>{copy.playerContent}</h2>
            {!draft.favoritePlayerId && <p>{copy.choosePlayer}</p>}
            {draft.favoritePlayerId && playerMatches.length === 0 && <p>{copy.emptyPlayerContent}</p>}
            {playerMatches.map((match) => (
              <button key={match.id} onClick={() => navigate(paths.match(match.id))} type="button">
                <strong>{match.metadata.home_team.name} · {match.metadata.away_team.name}</strong>
                <small>{copy.openPlayerContent}</small>
                <Icon name="arrow" size={15} />
              </button>
            ))}
          </article>
        </section>
        <div className="profile-card">
          <div className="profile-intro">
            <span>IN</span>
            <div>
              <h2>{copy.guest}</h2>
              <p>{copy.since}</p>
            </div>
          </div>
          <div className="preference-summary four">
            <span>
              <small>{copy.language}</small>
              <strong>{draft.language === 'es' ? 'Español' : 'English'}</strong>
            </span>
            <span>
              <small>{copy.player}</small>
              <strong>{playerName}</strong>
            </span>
            <span>
              <small>{copy.mode}</small>
              <strong>{t.modes[draft.mode].name}</strong>
            </span>
            <span>
              <small>{copy.level}</small>
              <strong>{t.levels[draft.level].name}</strong>
            </span>
          </div>

          <div className="preference-block">
            <h3>{copy.language}</h3>
            <div className="language-options">
              {LANGUAGES.map(([value, code, name]) => (
                <button aria-pressed={draft.language === value} className={draft.language === value ? 'selected' : ''} key={value} onClick={() => set({ language: value })} type="button">
                  <span>{code}</span>
                  <strong>{name}</strong>
                  {draft.language === value && <Icon name="check" size={16} />}
                </button>
              ))}
            </div>
          </div>

          <div className="preference-block">
            <h3>{copy.club}</h3>
            <div className="team-grid compact-grid">
              <button aria-pressed={!draft.favoriteTeamId} className={`team-select ${!draft.favoriteTeamId ? 'selected' : ''}`} onClick={() => set({ favoriteTeamId: '', favoritePlayerId: '' })} type="button">
                <span className="profile-club-logo none-logo">—</span>
                <strong>{t.common.none}</strong>
              </button>
              {catalog?.clubs.map((team) => {
                const brand = teamBranding(team)
                const selected = draft.favoriteTeamId === team.team_id
                return (
                  <button aria-pressed={selected} className={`team-select ${selected ? 'selected' : ''}`} key={team.team_id} onClick={() => set({ favoriteTeamId: team.team_id, favoritePlayerId: '' })} type="button">
                    {brand.logo ? <img alt={t.onboarding.crest(team.name)} className="profile-club-logo" src={brand.logo} /> : <span className="profile-club-logo">{brand.short}</span>}
                    <strong>{team.name}</strong>
                  </button>
                )
              })}
            </div>
          </div>

          <div className="preference-block">
            <h3>{copy.player}</h3>
            <div className="player-options">
              {players.map((player) => (
                <button aria-pressed={draft.favoritePlayerId === player.player_id} className={draft.favoritePlayerId === player.player_id ? 'selected' : ''} key={player.player_id} onClick={() => set({ favoritePlayerId: player.player_id })} type="button">
                  <img alt="" src={playerPhoto(player.player_id)} />
                  <div>
                    <strong>{player.name}</strong>
                    <small>
                      {catalog.clubs.find((c) => c.team_id === player.team_id)?.name} · {t.common.shirt} {player.shirt_number ?? '—'}
                    </small>
                  </div>
                  {draft.favoritePlayerId === player.player_id && <Icon name="check" size={16} />}
                </button>
              ))}
            </div>
          </div>

          <div className="preference-block">
            <h3>{copy.mode}</h3>
            <div className="profile-modes">
              {['casual', 'analyst', 'player'].map((mode) => (
                <button aria-pressed={draft.mode === mode} className={draft.mode === mode ? 'selected' : ''} key={mode} onClick={() => set({ mode })} type="button">
                  <Icon name={MODE_ART[mode].icon} />
                  <span>
                    <strong>{t.modes[mode].name}</strong>
                    <small>{t.modes[mode].description}</small>
                  </span>
                </button>
              ))}
            </div>
            {invalidMode && <p className="form-warning" role="alert">{copy.playerNeeded}</p>}
            {draft.mode === 'analyst' && (
              <button
                aria-pressed={draft.liveComments}
                className={`analyst-comments-toggle ${draft.liveComments ? 'selected' : ''}`}
                onClick={() => set({ liveComments: !draft.liveComments })}
                type="button"
              >
                <Icon name="match" />
                <span><strong>{copy.liveComments}</strong><small>{copy.liveCommentsCopy}</small></span>
                <Icon name={draft.liveComments ? 'check' : 'close'} size={16} />
              </button>
            )}
          </div>

          <div className="preference-block">
            <h3>{copy.level}</h3>
            <div className="profile-modes">
              {['simple', 'normal', 'advanced'].map((level) => (
                <button aria-pressed={draft.level === level} className={draft.level === level ? 'selected' : ''} key={level} onClick={() => set({ level })} type="button">
                  <Icon name={LEVEL_ICONS[level]} />
                  <span>
                    <strong>{t.levels[level].name}</strong>
                    <small>{t.levels[level].description}</small>
                  </span>
                </button>
              ))}
            </div>
          </div>

          <div className="save-row">
            <Button disabled={invalidMode} onClick={save}>
              {saved ? (<><Icon name="check" /> {t.common.saved}</>) : t.common.save}
            </Button>
            <Button variant="ghost" onClick={() => navigate(paths.discover())}>
              {copy.back}
            </Button>
          </div>
        </div>
      </section>
    </AppShell>
  )
}

function ExperienceList({ copy, empty, entries, onOpen }) {
  return (
    <article className="experience-panel">
      <h2>{copy}</h2>
      {entries.length === 0 && <p>{empty}</p>}
      {entries.slice(0, 4).map(({ match, viewedAt }) => (
        <button key={match.id} onClick={() => onOpen(match.id)} type="button">
          <strong>{match.metadata.home_team.name} · {match.metadata.away_team.name}</strong>
          <small>{new Date(viewedAt).toLocaleDateString()}</small>
          <Icon name="arrow" size={15} />
        </button>
      ))}
    </article>
  )
}
