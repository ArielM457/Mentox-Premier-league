import { useState } from 'react'
import { usePreferences } from '../app/preferences.js'
import { navigate, paths } from '../app/router.js'
import { ROLES, useSession } from '../app/session.js'
import { MODE_ART } from '../data/branding.js'
import { Brand } from '../components/ui/Brand.jsx'
import { Button } from '../components/ui/Button.jsx'
import { ErrorNotice } from '../components/ui/Feedback.jsx'
import { Icon } from '../components/ui/Icon.jsx'
import { LanguageSwitch } from '../components/ui/LanguageSwitch.jsx'

// Usuario de demostración de cada perfil; la contraseña no se muestra en la interfaz.
const PROFILES = [
  { role: ROLES.fan, username: 'aficionado', image: MODE_ART.casual.image },
  { role: ROLES.analyst, username: 'analista', image: MODE_ART.analyst.image },
]

export function Login({ next }) {
  const { t, preferences } = usePreferences()
  const { login } = useSession()
  const copy = t.auth
  const [role, setRole] = useState(ROLES.fan)
  const [username, setUsername] = useState(PROFILES[0].username)
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)

  function pick(profile) {
    setRole(profile.role)
    setUsername(profile.username)
    setPassword('')
    setError(null)
  }

  async function submit(event) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      const user = await login(username, password)
      if (next) navigate(next)
      else if (user.role === ROLES.fan && !preferences.onboarded) navigate(paths.onboarding())
      else navigate(paths.discover())
    } catch (err) {
      setError(err.status === 0 ? t.common.apiDown : err.message)
      setBusy(false)
    }
  }

  return (
    <main className="onboarding compact-onboarding">
      <section className="onboarding-modal compact-modal login-modal">
        <div className="compact-modal-top">
          <button className="brand-link" onClick={() => navigate(paths.landing())} type="button">
            <Brand />
          </button>
          <LanguageSwitch variant="landing" />
        </div>
        <form className="onboarding-form" onSubmit={submit}>
          <div className="onboarding-heading compact-heading">
            <span className="section-kicker">{copy.kicker}</span>
            <h1>{copy.title}</h1>
            <p>{copy.intro}</p>
          </div>

          <div className="visualization-modes login-profiles" role="radiogroup" aria-label={copy.title}>
            {PROFILES.map((profile) => (
              <button
                aria-checked={role === profile.role}
                className={role === profile.role ? 'selected' : ''}
                key={profile.role}
                onClick={() => pick(profile)}
                role="radio"
                type="button"
              >
                <div>
                  <img alt="" src={profile.image} />
                </div>
                <span>
                  <strong>{copy.profiles[profile.role].name}</strong>
                  <small>{copy.profiles[profile.role].description}</small>
                </span>
                {role === profile.role && (
                  <i>
                    <Icon name="check" size={14} />
                  </i>
                )}
              </button>
            ))}
          </div>

          <div className="login-fields">
            <label>
              <span>{copy.username}</span>
              <input autoComplete="username" onChange={(e) => setUsername(e.target.value)} required value={username} />
            </label>
            <label>
              <span>{copy.password}</span>
              <input autoComplete="current-password" autoFocus onChange={(e) => setPassword(e.target.value)} required type="password" value={password} />
            </label>
          </div>
          <ErrorNotice message={error} />
          <p className="login-hint">
            <Icon name="shield" size={15} /> {copy.demoHint}
          </p>
          <div className="onboarding-actions compact-actions">
            <div>
              <Button disabled={busy || !username.trim() || !password} type="submit">
                {busy ? copy.submitting : copy.submit} <Icon name="arrow" size={18} />
              </Button>
            </div>
          </div>
        </form>
      </section>
    </main>
  )
}
