import { useRoute } from './app/router.js'
import { usePreferences } from './app/preferences.js'
import { Icon } from './components/ui/Icon.jsx'
import { AllMatches } from './screens/AllMatches.jsx'
import { Discover } from './screens/Discover.jsx'
import { Editorial } from './screens/Editorial.jsx'
import { Landing } from './screens/Landing.jsx'
import { MatchCenter } from './screens/MatchCenter.jsx'
import { MomentDetail } from './screens/MomentDetail.jsx'
import { Onboarding } from './screens/Onboarding.jsx'
import { Profile } from './screens/Profile.jsx'
import { Recap } from './screens/Recap.jsx'

export default function App() {
  const { name, params } = useRoute()
  const { preferences, update, t } = usePreferences()
  let screen
  switch (name) {
    case 'onboarding':
      screen = <Onboarding />
      break
    case 'discover':
      screen = <Discover />
      break
    case 'matches':
      screen = <AllMatches />
      break
    case 'match':
      screen = <MatchCenter key={params[0]} matchId={params[0]} />
      break
    case 'moment':
      screen = <MomentDetail key={params.join('/')} matchId={params[0]} momentId={params[1]} />
      break
    case 'recap':
      screen = <Recap key={params[0]} matchId={params[0]} />
      break
    case 'profile':
      screen = <Profile />
      break
    case 'editorial':
      screen = <Editorial />
      break
    default:
      screen = <Landing />
  }

  const dark = preferences.theme !== 'light'
  return (
    <>
      {screen}
      <button
        aria-label={dark ? t.common.lightTheme : t.common.darkTheme}
        aria-pressed={dark}
        className="theme-toggle"
        onClick={() => update({ theme: dark ? 'light' : 'dark' })}
        title={dark ? t.common.lightTheme : t.common.darkTheme}
        type="button"
      >
        <Icon name={dark ? 'sun' : 'moon'} size={20} />
        <span>{dark ? t.common.lightTheme : t.common.darkTheme}</span>
      </button>
    </>
  )
}
