import { useState } from 'react'
import { usePreferences } from '../../app/preferences.js'
import { navigate, paths } from '../../app/router.js'
import { useSession } from '../../app/session.js'
import { Brand } from '../ui/Brand.jsx'
import { Icon } from '../ui/Icon.jsx'

const SIDEBAR_KEY = 'itg:sidebar'

const ITEMS = [
  ['discover', 'home', paths.discover()],
  ['matches', 'match', paths.matches()],
  ['profile', 'user', paths.profile()],
  ['editorial', 'shield', paths.editorial(), 'analyst'],
]

function initials(name) {
  return name.split(' ').map((word) => word[0]).join('').slice(0, 2).toUpperCase()
}

function readCollapsed() {
  try {
    return localStorage.getItem(SIDEBAR_KEY) === 'collapsed'
  } catch {
    return false
  }
}

// Marco común de las pantallas internas: barra lateral en escritorio y barra inferior en móvil.
export function AppShell({ active, dark = false, children }) {
  const { t } = usePreferences()
  const { user, isAnalyst, logout } = useSession()
  const [collapsed, setCollapsed] = useState(readCollapsed)
  const items = ITEMS.filter(([, , , role]) => !role || (role === 'analyst' && isAnalyst))

  function signOut() {
    logout()
    navigate(paths.landing())
  }

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
    <main className={`app-shell ${dark ? 'dark-shell' : 'light-shell'}`}>
      <aside className={`app-sidebar ${collapsed ? 'collapsed' : ''}`}>
        <div className="sidebar-top">
          <button className="brand-link" type="button" onClick={() => navigate(paths.landing())} aria-label="Inside the Game">
            <Brand />
          </button>
          <button aria-label={collapsed ? 'Expandir menú' : 'Contraer menú'} className="collapse-sidebar" onClick={toggle} type="button">
            <Icon name={collapsed ? 'arrow' : 'back'} size={18} />
          </button>
        </div>
        <nav aria-label={t.nav.discover}>
          {items.map(([key, icon, path]) => (
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
        <div className="sidebar-account">
          <button className="sidebar-profile" onClick={() => navigate(paths.profile())} type="button">
            <span className={isAnalyst ? 'is-analyst' : ''}>{initials(user?.display_name ?? t.nav.guest)}</span>
            <div>
              <strong>{user?.display_name ?? t.nav.guest}</strong>
              <small>{user ? t.auth.roles[user.role] : t.nav.preferences}</small>
            </div>
            <Icon name="arrow" size={15} />
          </button>
          {user && (
            <button className="sidebar-logout" onClick={signOut} title={t.auth.logout} type="button">
              <Icon name="back" size={16} /> {t.auth.logout}
            </button>
          )}
        </div>
      </aside>
      <nav className="mobile-nav" aria-label={t.nav.discover} style={{ gridTemplateColumns: `repeat(${items.length}, 1fr)` }}>
        {items.map(([key, icon, path]) => (
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
