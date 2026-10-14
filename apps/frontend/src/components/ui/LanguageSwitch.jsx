import { usePreferences } from '../../app/preferences.js'

const LANGUAGES = [['es', 'ES'], ['en', 'EN']]

// variant "landing" o "header" según el estilo del diseño en cada pantalla.
export function LanguageSwitch({ variant = 'header' }) {
  const { preferences, update } = usePreferences()
  return (
    <div className={variant === 'landing' ? 'language-switch' : 'header-language'} role="group" aria-label="Idioma / Language">
      {LANGUAGES.map(([value, label]) => (
        <button
          aria-pressed={preferences.language === value}
          className={preferences.language === value ? 'active' : ''}
          key={value}
          onClick={() => update({ language: value })}
          type="button"
        >
          {label}
        </button>
      ))}
    </div>
  )
}
