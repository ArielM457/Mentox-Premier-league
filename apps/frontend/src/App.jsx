import { ANALYST_ONLY, PROTECTED, useRoute } from './app/router.js'
import { useSession } from './app/session.js'
import { AllMatches } from './screens/AllMatches.jsx'
import { Discover } from './screens/Discover.jsx'
import { Editorial } from './screens/Editorial.jsx'
import { Forbidden } from './screens/Forbidden.jsx'
import { Landing } from './screens/Landing.jsx'
import { Login } from './screens/Login.jsx'
import { MatchCenter } from './screens/MatchCenter.jsx'
import { MomentDetail } from './screens/MomentDetail.jsx'
import { Onboarding } from './screens/Onboarding.jsx'
import { Profile } from './screens/Profile.jsx'
import { Recap } from './screens/Recap.jsx'

export default function App() {
  const route = useRoute()
  const { user, isAnalyst } = useSession()
  const { name, params, path, query } = route

  // Sin sesión se pide iniciarla y después se vuelve a la misma pantalla.
  if (PROTECTED.has(name) && !user) return <Login next={path} />
  if (ANALYST_ONLY.has(name) && !isAnalyst) return <Forbidden />

  switch (name) {
    case 'login':
      return <Login next={query.next} />
    case 'onboarding':
      return <Onboarding />
    case 'discover':
      return <Discover />
    case 'matches':
      return <AllMatches />
    case 'match':
      return <MatchCenter key={params[0]} matchId={params[0]} />
    case 'moment':
      return <MomentDetail key={params.join('/')} matchId={params[0]} momentId={params[1]} />
    case 'recap':
      return <Recap key={params[0]} matchId={params[0]} />
    case 'profile':
      return <Profile />
    case 'editorial':
      return <Editorial />
    default:
      return <Landing />
  }
}
