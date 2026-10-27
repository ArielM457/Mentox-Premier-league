import { usePreferences } from '../../app/preferences.js'

export function NarrativeCopy({ text = '' }) {
  const { t } = usePreferences()
  const readable = Object.entries(t.kinds).reduce((copy, [key, label]) => copy.replace(new RegExp(`\\b${key}\\b`, 'g'), label), text)
  const [facts, moments] = readable.split(/(?:Momentos|Moments):\s*/)
  return <div className="narrative-copy"><p>{facts}</p>{moments && <ul>{moments.split(';').map((moment) => <li key={moment}>{moment.trim()}</li>)}</ul>}</div>
}
