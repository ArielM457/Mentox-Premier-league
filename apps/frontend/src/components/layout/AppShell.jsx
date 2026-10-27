import { useState } from 'react'
import { usePreferences } from '../../app/preferences.js'
import { navigate, paths } from '../../app/router.js'
import { Brand } from '../ui/Brand.jsx'
import { Icon } from '../ui/Icon.jsx'
import { useCatalog } from '../../hooks/useCatalog.js'
import { LoadingScreen } from '../ui/Feedback.jsx'
import { ThemeToggle } from '../ui/ThemeToggle.jsx'
import { SessionDialog } from '../ui/SessionDialog.jsx'
import { readDemoSession } from '../../lib/session.js'

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
  const { data: catalog, error: catalogError } = useCatalog()
  const [collapsed, setCollapsed] = useState(readCollapsed)
  const [user, setUser] = useState(readDemoSession)
  const [sessionOpen, setSessionOpen] = useState(false)

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
      <a href="#page-content" className="skip-link" onClick={(event) => { event.preventDefault(); document.getElementById('page-content')?.focus() }}>{t.common.skipContent}</a>
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
        <button className="sidebar-profile" onClick={() => setSessionOpen(true)} type="button">
          <span>{user ? user.slice(0, 2).toUpperCase() : 'IN'}</span>
          <div>
            <strong>{user || t.nav.guest}</strong>
            <small>{user ? t.session.account : t.session.title}</small>
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
      <div className="shell-toolbar">
        <ThemeToggle />
        <button className="account-button" onClick={() => setSessionOpen(true)} type="button"><Icon name="user" size={18} />{user || t.nav.guest}</button>
      </div>
      <div id="page-content" tabIndex={-1}>{!catalog && !catalogError ? <LoadingScreen /> : children}</div>
      {sessionOpen && <SessionDialog user={user} onSession={setUser} onClose={() => setSessionOpen(false)} />}
    </main>
  )
}
