import { useState } from 'react'
import { api } from '../../api/client.js'
import { usePreferences } from '../../app/preferences.js'
import { Button } from '../ui/Button.jsx'
import { Icon } from '../ui/Icon.jsx'

// Preguntas sobre el partido respondidas con los eventos ya ocurridos (RF-34).
// ``onClose`` (opcional) añade en la cabecera el botón que oculta el panel.
export function Assistant({ matchId, timeRef, favoriteClub, favoritePlayer, onExplore, canExplore, onClose }) {
  const { t, apiPreferences, preferences } = usePreferences()
  const [question, setQuestion] = useState('')
  const [asked, setAsked] = useState(null)
  const [answer, setAnswer] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)

  async function ask(text) {
    const value = text.trim()
    if (!value) return
    setAsked(value)
    setBusy(true)
    setError(null)
    try {
      const result = await api.ask(matchId, value, timeRef.current, apiPreferences)
      setAnswer(result.answer)
      setQuestion('')
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <aside className="assistant" aria-labelledby="assistant-title">
      <div className="assistant-title">
        <span id="assistant-title">
          <Icon name="spark" /> {t.assistant.title}
        </span>
        <span className="assistant-title-tools">
          <span className="ai-mode">{t.modes[preferences.mode].name}</span>
          {onClose && (
            <button aria-controls="match-agent-panel" aria-label={t.match.hideAgent} className="assistant-close" onClick={onClose} title={t.match.hideAgent} type="button">
              <Icon name="panelClose" size={18} />
            </button>
          )}
        </span>
      </div>
      {asked && <div className="assistant-question">{asked}</div>}
      <div className="assistant-answer" aria-live="polite">
        <span className="spark-avatar">
          <Icon name="spark" size={17} />
        </span>
        <div>
          {error ? (
            <p className="assistant-error">{error}</p>
          ) : busy ? (
            <p>{t.assistant.asking}</p>
          ) : answer ? (
            <>
              <p><strong>{answer.headline}</strong></p>
              <p>{answer.explanation}</p>
              <p className="assistant-sources">
                {t.assistant.sources}: {answer.source_event_ids.length ? answer.source_event_ids.join(', ') : t.assistant.noSources}
              </p>
            </>
          ) : (
            <p>{t.assistant.empty}</p>
          )}
        </div>
      </div>
      <form
        className="assistant-form"
        onSubmit={(event) => {
          event.preventDefault()
          ask(question)
        }}
      >
        <label className="sr-only" htmlFor="assistant-question">{t.assistant.placeholder}</label>
        <input
          id="assistant-question"
          maxLength={500}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder={t.assistant.placeholder}
          value={question}
        />
        <button aria-label={t.assistant.ask} disabled={busy || !question.trim()} type="submit">
          <Icon name="arrow" size={17} />
        </button>
      </form>
      <div className="suggestions">
        <strong>{t.assistant.suggestions}</strong>
        {t.assistant.suggested(favoriteClub?.name, favoritePlayer?.name).map((item) => (
          <button className={item === asked ? 'active' : ''} disabled={busy} key={item} onClick={() => ask(item)} type="button">
            {item}
          </button>
        ))}
      </div>
      <Button variant="secondary" onClick={onExplore} disabled={!canExplore}>
        <Icon name="play" size={17} /> {t.assistant.explore}
      </Button>
    </aside>
  )
}
