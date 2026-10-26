import { usePreferences } from '../../app/preferences.js'
import { Icon } from './Icon.jsx'

export function ThemeToggle() {
  const { preferences, update, t } = usePreferences()
  const dark = preferences.theme !== 'light'
  return (
    <button className="theme-toggle" aria-label={dark ? t.common.lightTheme : t.common.darkTheme} title={dark ? t.common.lightTheme : t.common.darkTheme} onClick={() => update({ theme: dark ? 'light' : 'dark' })} type="button">
      <Icon name={dark ? 'sun' : 'moon'} size={18} />
      <span>{dark ? t.common.lightTheme : t.common.darkTheme}</span>
    </button>
  )
}
