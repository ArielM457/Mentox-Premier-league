import { useState } from 'react'
import { usePreferences } from '../../app/preferences.js'
import { navigate, paths } from '../../app/router.js'
import { Brand } from '../ui/Brand.jsx'
import { Icon } from '../ui/Icon.jsx'

const SIDEBAR_KEY = 'itg:sidebar'

const ITEMS = [
  ['discover', 'home', paths.discover()],
  ['matches', 'match', paths.matches()],
  ['profile', 'user', paths.profile()],
  ['editorial', 'shield', paths.editorial()],
]

function readCollapsed() {
  try {
    return localStorage.getItem(SIDEBAR_KEY) === 'collapsed'
  } catch {
    return false
  }
}

// Marco común de las pantallas internas: barra lateral en escritorio y barra inferior en móvil.
export function AppShell({ active, children }) {
  const { preferences, t } = usePreferences()
  const [collapsed, setCollapsed] = useState(readCollapsed)

  function toggle() {
    const next = !collapsed
    setCollapsed(next)
    try {
      localStorage.setItem(SIDEBAR_KEY, next ? 'collapsed' : 'expanded')
    } catch {
      // Preferencia solo visual.
    }
  }

  return (
    <main className={`app-shell ${preferences.theme === 'light' ? 'light-shell' : 'dark-shell'}`}>
      <aside className={`app-sidebar ${collapsed ? 'collapsed' : ''}`}>
        <div className="sidebar-top">
          <button className="brand-link" type="button" onClick={() => navigate(paths.landing())} aria-label={t.brand}>
            <Brand />
          </button>
          <button aria-label={collapsed ? t.nav.expandMenu : t.nav.collapseMenu} className="collapse-sidebar" onClick={toggle} type="button">
            <Icon name={collapsed ? 'arrow' : 'back'} size={18} />
          </button>
        </div>
        <nav aria-label={t.nav.discover}>
          {ITEMS.map(([key, icon, path]) => (
            <button
              aria-current={active === key ? 'page' : undefined}
              className={active === key ? 'active' : ''}
              key={key}
              onClick={() => navigate(path)}
              title={t.nav[key]}
              type="button"
            >
              <Icon name={icon} /> {t.nav[key]}
            </button>
          ))}
        </nav>
        <button className="sidebar-profile" onClick={() => navigate(paths.profile())} type="button">
          <span>IN</span>
          <div>
            <strong>{t.nav.guest}</strong>
            <small>{t.nav.preferences}</small>
          </div>
          <Icon name="arrow" size={15} />
        </button>
      </aside>
      <nav className="mobile-nav" aria-label={t.nav.discover}>
        {ITEMS.map(([key, icon, path]) => (
          <button
            aria-current={active === key ? 'page' : undefined}
            className={active === key ? 'active' : ''}
            key={key}
            onClick={() => navigate(path)}
            type="button"
          >
            <Icon name={icon} />
            <span>{t.nav[key]}</span>
          </button>
        ))}
      </nav>
      {children}
    </main>
  )
}
