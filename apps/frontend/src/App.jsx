import { useRoute } from './app/router.js'
import { AllMatches } from './screens/AllMatches.jsx'
import { Discover } from './screens/Discover.jsx'
import { Editorial, EditorialDetail } from './screens/Editorial.jsx'
import { Landing } from './screens/Landing.jsx'
import { MatchCenter } from './screens/MatchCenter.jsx'
import { MomentDetail } from './screens/MomentDetail.jsx'
import { Onboarding } from './screens/Onboarding.jsx'
import { Profile } from './screens/Profile.jsx'
import { PrematchPreview } from './screens/PrematchPreview.jsx'
import { Recap } from './screens/Recap.jsx'

export default function App() {
  const { name, params } = useRoute()
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
    case 'preview':
      screen = <PrematchPreview key={params[0]} matchId={params[0]} />
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
    case 'editorialDetail':
      screen = <EditorialDetail key={params.join('/')} matchId={params[0]} draftId={params[1]} />
      break
    default:
      screen = <Landing />
  }

  return screen
}
