import { ThemeToggle } from '../components/ui/ThemeToggle.jsx'
import { useState } from 'react'
import { usePreferences } from '../app/preferences.js'
import { navigate, paths } from '../app/router.js'
import { MODE_ART, playerPhoto, teamBranding } from '../data/branding.js'
import { useCatalog } from '../hooks/useCatalog.js'
import { Brand } from '../components/ui/Brand.jsx'
import { Button } from '../components/ui/Button.jsx'
import { ErrorNotice, LoadingScreen } from '../components/ui/Feedback.jsx'
import { Icon } from '../components/ui/Icon.jsx'

const LANGUAGES = [['es', 'ES', 'Español', 'Experiencia en español'], ['en', 'EN', 'English', 'Experience in English']]

export function Onboarding() {
  const { t, preferences, update } = usePreferences()
  const { data: catalog, error, reload } = useCatalog()
  const copy = t.onboarding
  const [step, setStep] = useState(0)
  const [draft, setDraft] = useState({
    language: preferences.language,
    favoriteTeamId: preferences.favoriteTeamId,
    favoritePlayerId: preferences.favoritePlayerId,
    mode: preferences.mode,
  })
  const set = (changes) => setDraft((current) => ({ ...current, ...changes }))
  const club = catalog?.clubs.find((team) => team.team_id === draft.favoriteTeamId)
  const players = catalog?.players.filter((player) => player.team_id === draft.favoriteTeamId) ?? []

  function finish() {
    update({ ...draft, onboarded: true })
    navigate(paths.discover())
  }

  return (
    <main className="onboarding compact-onboarding">
      <section className="onboarding-modal compact-modal">
        <div className="compact-modal-top">
          <Brand />
          <ThemeToggle />
          <button className="skip-setup" onClick={() => { update({ onboarded: true }); navigate(paths.discover()) }} type="button">
            {copy.skip}
          </button>
        </div>
        <div className="onboarding-form">
          <div className="onboarding-heading compact-heading">
            <span className="section-kicker">{copy.kicker}</span>
            <h1>{copy.title}</h1>
            <p>{copy.intro}</p>
          </div>
          <div className="experience-stepper" aria-label={`${step + 1} / 4`}>
            {copy.steps.map((label, index) => (
              <button
                aria-current={index === step ? 'step' : undefined}
                aria-label={copy.step(index + 1, label)}
                className={`${index === step ? 'active' : ''} ${index < step ? 'complete' : ''}`}
                key={label}
                onClick={() => setStep(index)}
                type="button"
              >
                <span>{index < step ? <Icon name="check" size={13} /> : index + 1}</span>
                <small>{label}</small>
              </button>
            ))}
          </div>

          <ErrorNotice message={error && t.common.apiDown} onRetry={reload} retryLabel={t.common.retry} />

          {!catalog && !error && (step === 1 || step === 2) && <LoadingScreen compact />}

          {step === 0 && (
            <div className="onboarding-preference onboarding-step compact-step">
              <StepIntro number="01" title={copy.languageTitle} text={copy.languageCopy} />
              <div className="onboarding-language language-cards">
                {LANGUAGES.map(([value, code, name, description]) => (
                  <button aria-pressed={draft.language === value} className={draft.language === value ? 'selected' : ''} key={value} onClick={() => { set({ language: value }); update({ language: value }) }} type="button">
                    <b>{code}</b>
                    <span>
                      <strong>{name}</strong>
                      <small>{description}</small>
                    </span>
                    {draft.language === value && <Icon name="check" size={16} />}
                  </button>
                ))}
              </div>
            </div>
          )}

          {step === 1 && catalog && (
            <div className="onboarding-preference onboarding-step compact-step">
              <StepIntro number="02" title={copy.clubTitle} text={copy.clubCopy} />
              <div className="club-logo-grid">
                {catalog?.clubs.map((team) => {
                  const brand = teamBranding(team)
                  const selected = draft.favoriteTeamId === team.team_id
                  return (
                    <button aria-pressed={selected} className={selected ? 'selected' : ''} key={team.team_id} onClick={() => set({ favoriteTeamId: team.team_id, favoritePlayerId: '' })} type="button">
                      {brand.logo ? <img alt={copy.crest(team.name)} src={brand.logo} /> : <b>{brand.short}</b>}
                      <strong>{team.name}</strong>
                      {selected && (
                        <span>
                          <Icon name="check" size={14} />
                        </span>
                      )}
                    </button>
                  )
                })}
              </div>
            </div>
          )}

          {step === 2 && catalog && (
            <div className="onboarding-preference onboarding-step compact-step">
              <StepIntro number="03" title={club ? copy.playersOf(club.name) : copy.chooseClubFirst} text={copy.playerCopy} />
              {club ? (
                <div className="player-card-grid">
                  {players.map((player) => (
                    <button aria-pressed={draft.favoritePlayerId === player.player_id} className={draft.favoritePlayerId === player.player_id ? 'selected' : ''} key={player.player_id} onClick={() => set({ favoritePlayerId: player.player_id })} type="button">
                      <img alt="" src={playerPhoto(player.player_id)} />
                      <span>
                        <strong>{player.name}</strong>
                        <small>{t.common.shirt} {player.shirt_number ?? '—'}</small>
                      </span>
                      {draft.favoritePlayerId === player.player_id && (
                        <i>
                          <Icon name="check" size={14} />
                        </i>
                      )}
                    </button>
                  ))}
                </div>
              ) : (
                <button className="choose-club-prompt" onClick={() => setStep(1)} type="button">
                  <Icon name="match" size={24} /> {copy.chooseClub}
                </button>
              )}
            </div>
          )}

          {step === 3 && (
            <div className="onboarding-preference onboarding-step compact-step">
              <StepIntro number="04" title={copy.modeTitle} text={copy.modeCopy} />
              <div className="visualization-modes three">
                {['casual', 'analyst', 'player'].map((mode) => {
                  const disabled = mode === 'player' && !draft.favoritePlayerId
                  return (
                    <button aria-pressed={draft.mode === mode} className={draft.mode === mode ? 'selected' : ''} disabled={disabled} key={mode} onClick={() => set({ mode })} title={disabled ? t.profile.playerNeeded : undefined} type="button">
                      <div>
                        <img alt="" src={MODE_ART[mode].image} />
                      </div>
                      <span>
                        <strong>{t.modes[mode].name}</strong>
                        <small>{disabled ? t.profile.playerNeeded : t.modes[mode].description}</small>
                      </span>
                      {draft.mode === mode && (
                        <i>
                          <Icon name="check" size={14} />
                        </i>
                      )}
                    </button>
                  )
                })}
              </div>
            </div>
          )}

          <div className="onboarding-actions compact-actions">
            <div>
              {step > 0 && (
                <Button variant="ghost" onClick={() => setStep(step - 1)}>
                  <Icon name="back" size={18} /> {t.common.back}
                </Button>
              )}
              {step < 3 ? (
                <Button onClick={() => setStep(step + 1)}>
                  {t.common.continue} <Icon name="arrow" size={18} />
                </Button>
              ) : (
                <Button onClick={finish}>
                  {copy.finish} <Icon name="arrow" size={18} />
                </Button>
              )}
            </div>
          </div>
        </div>
      </section>
    </main>
  )
}

function StepIntro({ number, title, text }) {
  return (
    <div className="step-intro">
      <span>{number}</span>
      <div>
        <h2>{title}</h2>
        <p>{text}</p>
      </div>
    </div>
  )
}
