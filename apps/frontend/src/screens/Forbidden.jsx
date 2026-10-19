import { usePreferences } from '../app/preferences.js'
import { navigate, paths } from '../app/router.js'
import { useSession } from '../app/session.js'
import { AppShell } from '../components/layout/AppShell.jsx'
import { Button } from '../components/ui/Button.jsx'
import { Icon } from '../components/ui/Icon.jsx'

export function Forbidden() {
  const { t } = usePreferences()
  const { logout } = useSession()
  return (
    <AppShell active="">
      <section className="discover-content">
        <div className="empty-state">
          <Icon name="shield" size={30} />
          <h3>{t.auth.forbidden}</h3>
          <div className="button-row">
            <Button onClick={() => navigate(paths.discover())}>{t.profile.back}</Button>
            <Button variant="ghost" onClick={() => { logout(); navigate(paths.login()) }}>
              {t.auth.switchProfile}
            </Button>
          </div>
        </div>
      </section>
    </AppShell>
  )
}
