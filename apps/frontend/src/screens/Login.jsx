import { useEffect, useRef, useState } from 'react'
import { usePreferences } from '../app/preferences.js'
import { navigate, paths } from '../app/router.js'
import { ROLES, useSession } from '../app/session.js'
import { DEMO_ACCOUNTS } from '../data/demoAccounts.js'
import { Brand } from '../components/ui/Brand.jsx'
import { Icon } from '../components/ui/Icon.jsx'
import { LanguageSwitch } from '../components/ui/LanguageSwitch.jsx'

const ROLE_ICONS = { [ROLES.fan]: 'user', [ROLES.analyst]: 'chart' }

export function Login({ next }) {
  const { t } = usePreferences()
  const { login, notice, dismissNotice } = useSession()
  const copy = t.auth
  const [role, setRole] = useState(ROLES.fan)
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [remember, setRemember] = useState(false)
  const [showPassword, setShowPassword] = useState(false)
  const [capsLock, setCapsLock] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const [invalid, setInvalid] = useState(false)
  const [lockedUntil, setLockedUntil] = useState(0)
  const [now, setNow] = useState(() => Date.now())
  const [demoFilled, setDemoFilled] = useState(false)
  const passwordRef = useRef(null)

  const lockedFor = Math.max(0, Math.ceil((lockedUntil - now) / 1000))

  // Cuenta regresiva del bloqueo temporal.
  useEffect(() => {
    if (!lockedUntil) return undefined
    const id = setInterval(() => {
      const current = Date.now()
      setNow(current)
      if (current >= lockedUntil) {
        setLockedUntil(0)
        setError(null)
      }
    }, 1000)
    return () => clearInterval(id)
  }, [lockedUntil])

  function pickRole(value) {
    setRole(value)
    setError(null)
    setDemoFilled(false)
  }

  function useDemo() {
    const account = DEMO_ACCOUNTS[role]
    setUsername(account.username)
    setPassword(account.password)
    setInvalid(false)
    setError(null)
    setDemoFilled(true)
  }

  function trackCapsLock(event) {
    if (typeof event.getModifierState === 'function') setCapsLock(event.getModifierState('CapsLock'))
  }

  async function submit(event) {
    event.preventDefault()
    if (!username.trim() || !password) {
      setInvalid(true)
      setError({ message: copy.required })
      return
    }
    setBusy(true)
    setError(null)
    dismissNotice()
    try {
      await login(username, password, remember)
      // Si la cuenta aún no configuró su experiencia, App muestra la configuración primero.
      navigate(next || paths.discover())
    } catch (err) {
      setBusy(false)
      setPassword('')
      passwordRef.current?.focus()
      if (err.status === 429) {
        const retry = err.data?.retry_after_s ?? 60
        setNow(Date.now())
        setLockedUntil(Date.now() + retry * 1000)
        setError({ locked: true })
      } else if (err.status === 401) {
        setInvalid(true)
        setError({ message: err.message, attemptsLeft: err.data?.attempts_left })
      } else {
        setError({ message: err.status === 0 ? t.common.apiDown : err.message })
      }
    }
  }

  const locked = lockedFor > 0

  return (
    <main className="auth-page">
      <aside className="auth-brand" aria-hidden="true">
        <div className="auth-brand-top">
          <Brand light />
        </div>
        <div className="auth-brand-copy">
          <span className="auth-kicker">
            <span className="live-dot" /> {copy.brandKicker}
          </span>
          <h2>{copy.brandTitle}</h2>
          <p>{copy.brandCopy}</p>
          <ul>
            {copy.features.map((feature) => (
              <li key={feature}>
                <Icon name="check" size={16} /> {feature}
              </li>
            ))}
          </ul>
        </div>
        <img alt="" className="auth-brand-art" src="/images/stadium.webp" />
        <p className="auth-secure">
          <Icon name="lock" size={14} /> {copy.secure}
        </p>
      </aside>

      <section className="auth-panel">
        <div className="auth-panel-top">
          <button className="auth-back" onClick={() => navigate(paths.landing())} type="button">
            <Icon name="back" size={16} /> {copy.back}
          </button>
          <LanguageSwitch variant="landing" />
        </div>

        <form className="auth-card" noValidate onSubmit={submit}>
          <div className="auth-mobile-brand">
            <Brand />
          </div>
          <span className="section-kicker">{copy.kicker}</span>
          <h1>{copy.title}</h1>
          <p className="auth-intro">{copy.intro}</p>

          {notice === 'expired' && (
            <div className="auth-alert info" role="status">
              <Icon name="lock" size={17} /> <span>{copy.expired}</span>
            </div>
          )}

          <fieldset className="auth-roles">
            <legend>{copy.profile}</legend>
            <div role="radiogroup" aria-label={copy.profile}>
              {[ROLES.fan, ROLES.analyst].map((value) => (
                <button
                  aria-checked={role === value}
                  className={role === value ? 'selected' : ''}
                  key={value}
                  onClick={() => pickRole(value)}
                  role="radio"
                  type="button"
                >
                  <Icon name={ROLE_ICONS[value]} size={18} />
                  {copy.profiles[value].name}
                </button>
              ))}
            </div>
            <p>{copy.profiles[role].description}</p>
          </fieldset>

          <label className="auth-field">
            <span>{copy.username}</span>
            <div className={`auth-input ${invalid && !username.trim() ? 'is-invalid' : ''}`}>
              <Icon name="user" size={18} />
              <input
                aria-invalid={invalid && !username.trim()}
                autoCapitalize="none"
                autoComplete="username"
                autoFocus
                onChange={(e) => { setUsername(e.target.value); setDemoFilled(false) }}
                placeholder={copy.usernamePlaceholder}
                spellCheck="false"
                value={username}
              />
            </div>
          </label>

          <label className="auth-field">
            <span>{copy.password}</span>
            <div className={`auth-input ${invalid && (!password || error?.attemptsLeft != null) ? 'is-invalid' : ''}`}>
              <Icon name="lock" size={18} />
              <input
                aria-describedby={capsLock ? 'caps-lock' : undefined}
                aria-invalid={invalid && !password}
                autoComplete="current-password"
                onChange={(e) => { setPassword(e.target.value); setDemoFilled(false) }}
                onKeyDown={trackCapsLock}
                onKeyUp={trackCapsLock}
                placeholder={copy.passwordPlaceholder}
                ref={passwordRef}
                type={showPassword ? 'text' : 'password'}
                value={password}
              />
              <button
                aria-label={showPassword ? copy.hidePassword : copy.showPassword}
                aria-pressed={showPassword}
                className="auth-reveal"
                onClick={() => setShowPassword(!showPassword)}
                type="button"
              >
                <Icon name={showPassword ? 'eyeOff' : 'eye'} size={18} />
              </button>
            </div>
            {capsLock && (
              <small className="auth-caps" id="caps-lock">
                <Icon name="alert" size={14} /> {copy.capsLock}
              </small>
            )}
          </label>

          <label className="auth-remember">
            <input checked={remember} onChange={(e) => setRemember(e.target.checked)} type="checkbox" />
            <span>
              <strong>{copy.remember}</strong>
              <small>{copy.rememberHint}</small>
            </span>
          </label>

          {error && (
            <div className="auth-alert error" role="alert">
              <Icon name={locked ? 'lock' : 'alert'} size={17} />
              <span>
                {locked ? copy.locked(lockedFor) : error.message}
                {!locked && error.attemptsLeft != null && <small>{copy.attemptsLeft(error.attemptsLeft)}</small>}
              </span>
            </div>
          )}
          {demoFilled && !error && (
            <div className="auth-alert info" role="status">
              <Icon name="check" size={17} /> <span>{copy.demoFilled}</span>
            </div>
          )}

          <button className="btn btn-primary auth-submit" disabled={busy || locked} type="submit">
            {busy ? (
              <>
                <span className="auth-spinner" aria-hidden="true" /> {copy.submitting}
              </>
            ) : (
              <>
                {copy.submit} <Icon name="arrow" size={18} />
              </>
            )}
          </button>

          <div className="auth-divider">
            <span>{copy.or}</span>
          </div>
          <button className="btn btn-ghost auth-demo" disabled={busy} onClick={useDemo} type="button">
            <Icon name="spark" size={17} /> {copy.useDemo} · {copy.profiles[role].name}
          </button>

          <p className="auth-footnote">
            <Icon name="shield" size={14} /> {copy.secure}
          </p>
        </form>
      </section>
    </main>
  )
}
