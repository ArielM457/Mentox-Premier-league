import { useRoute } from './app/router.js'
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
  switch (name) {
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
