import { usePreferences } from '../../app/preferences.js'
import { LANGUAGES } from '../../i18n/languages.js'

// variant "landing" o "header" según el estilo del diseño en cada pantalla.
export function LanguageSwitch({ variant = 'header' }) {
  const { preferences, t, update } = usePreferences()
  return (
    <label className={variant === 'landing' ? 'language-switch' : 'header-language'}>
      <span className="sr-only">{t.profile.language}</span>
      <select aria-label={t.profile.language} onChange={(event) => update({ language: event.target.value })} value={preferences.language}>
        {LANGUAGES.map(({ value, code, name }) => (
          <option key={value} value={value}>{code} · {name}</option>
        ))}
      </select>
    </label>
  )
}
