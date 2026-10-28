import { useState } from 'react'
import { usePreferences } from '../app/preferences.js'
import { navigate, paths } from '../app/router.js'
import { MODE_ART, playerPhoto, teamBranding } from '../data/branding.js'
import { useCatalog } from '../hooks/useCatalog.js'
import { AppShell } from '../components/layout/AppShell.jsx'
import { Button } from '../components/ui/Button.jsx'
import { ErrorNotice } from '../components/ui/Feedback.jsx'
import { Icon } from '../components/ui/Icon.jsx'
import { LANGUAGES, languageName } from '../i18n/languages.js'

const LEVEL_ICONS = { simple: 'spark', normal: 'match', advanced: 'chart' }

export function Profile() {
  const { t, preferences, reset, update } = usePreferences()
  const { data: catalog, error, reload } = useCatalog()
  const copy = t.profile
  const [draft, setDraft] = useState(() => {
    const { language, mode, level, favoriteTeamId, favoritePlayerId, liveComments } = preferences
    return { language, mode, level, favoriteTeamId, favoritePlayerId, liveComments }
  })
  const [saved, setSaved] = useState(false)
  const [confirmReset, setConfirmReset] = useState(false)
  const set = (changes) => {
    setSaved(false)
    setDraft((current) => ({ ...current, ...changes }))
  }
  const players = catalog?.players.filter((p) => !draft.favoriteTeamId || p.team_id === draft.favoriteTeamId) ?? []
  const playerName = catalog?.players.find((p) => p.player_id === draft.favoritePlayerId)?.name ?? t.common.none
  const invalidMode = draft.mode === 'player' && !draft.favoritePlayerId

  function save() {
    if (invalidMode) return
    const professionalDefaults = draft.mode === 'professional_analyst'
      ? { level: 'advanced', liveComments: true }
      : {}
    update({ ...draft, ...professionalDefaults, onboarded: true })
    setSaved(true)
  }

  function resetConfiguration() {
    reset()
    navigate(paths.onboarding())
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
        <div className="profile-card">
          <div className="profile-intro">
            <span><Icon name="user" /></span>
            <div>
              <h2>{t.nav.preferences}</h2>
              <p>{copy.since}</p>
            </div>
          </div>
          <div className="preference-summary four">
            <span>
              <small>{copy.language}</small>
              <strong>{languageName(draft.language)}</strong>
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
              {LANGUAGES.map(({ value, code, name }) => (
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
            <div className="player-options"><button aria-pressed={!draft.favoritePlayerId} className={!draft.favoritePlayerId ? 'selected' : ''} onClick={() => set({ favoritePlayerId: '', mode: draft.mode === 'player' ? 'casual' : draft.mode })} type="button"><Icon name="user" /><strong>{t.common.none}</strong></button>
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
              {['casual', 'analyst', 'professional_analyst', 'player'].map((mode) => (
                <button aria-pressed={draft.mode === mode} className={draft.mode === mode ? 'selected' : ''} key={mode} onClick={() => set(mode === 'professional_analyst' ? { mode, level: 'advanced', liveComments: true } : { mode })} type="button">
                  <Icon name={MODE_ART[mode].icon} />
                  <span>
                    <strong>{t.modes[mode].name}</strong>
                    <small>{t.modes[mode].description}</small>
                  </span>
                </button>
              ))}
            </div>
            {invalidMode && <p className="form-warning" role="alert">{copy.playerNeeded}</p>}
            {['analyst', 'professional_analyst'].includes(draft.mode) && (
              <button
                aria-checked={draft.mode === 'professional_analyst' || draft.liveComments}
                role="switch"
                className={`analyst-comments-toggle ${draft.mode === 'professional_analyst' || draft.liveComments ? 'selected' : ''}`}
                disabled={draft.mode === 'professional_analyst'}
                onClick={() => set({ liveComments: !draft.liveComments })}
                type="button"
              >
                <Icon name="match" />
                <span><strong>{copy.liveComments}</strong><small>{copy.liveCommentsCopy}</small></span>
                <span className="switch-track" aria-hidden="true"><span /></span>
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

          <div className="save-row"><span className="save-note" role="status">{saved ? t.common.saved : t.profile.saveHint}</span>
            <Button disabled={invalidMode} onClick={save}>
              {saved ? (<><Icon name="check" /> {t.common.saved}</>) : t.common.save}
            </Button>
            <Button variant="ghost" onClick={() => navigate(paths.discover())}>
              {copy.back}
            </Button>
          </div>

          <section className="reset-preferences" aria-labelledby="reset-preferences-title">
            <div>
              <span className="reset-preferences-icon"><Icon name="trash" /></span>
              <div>
                <h3 id="reset-preferences-title">{copy.resetTitle}</h3>
                <p>{copy.resetCopy}</p>
              </div>
            </div>
            {!confirmReset ? (
              <Button className="danger" variant="ghost" onClick={() => setConfirmReset(true)}>
                <Icon name="trash" size={17} /> {copy.resetAction}
              </Button>
            ) : (
              <div className="reset-confirmation" role="alert">
                <strong>{copy.resetConfirm}</strong>
                <div>
                  <Button className="danger" variant="ghost" onClick={resetConfiguration}>
                    <Icon name="trash" size={17} /> {copy.resetConfirmAction}
                  </Button>
                  <Button variant="ghost" onClick={() => setConfirmReset(false)}>{copy.resetCancel}</Button>
                </div>
              </div>
            )}
          </section>
        </div>
      </section>
    </AppShell>
  )
}
