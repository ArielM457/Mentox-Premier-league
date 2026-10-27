import { useEffect, useRef, useState } from 'react'
import { usePreferences } from '../../app/preferences.js'
import { useCommunityRoom } from '../../hooks/useCommunityRoom.js'
import { communityClientId, saveCommunityName, savedCommunityName } from '../../lib/communityIdentity.js'
import { Button } from '../ui/Button.jsx'
import { ErrorNotice } from '../ui/Feedback.jsx'
import { Icon } from '../ui/Icon.jsx'

// Sala de un resumen: votación, sugerencias y chat, todo en tiempo real.
export function CommunityPanel({ matchId, record }) {
  const { t } = usePreferences()
  const copy = t.editorial.community
  const [clientId] = useState(communityClientId)
  const draftId = record.draft.draft_id
  const { room, status, error, lastEvent, vote, send } = useCommunityRoom(matchId, draftId, clientId)
  const [name, setName] = useState(savedCommunityName)
  const [nameMissing, setNameMissing] = useState(false)
  const [mine, setMine] = useState(() => new Set())

  function requireName() {
    const value = name.trim()
    if (!value) {
      setNameMissing(true)
      return null
    }
    setNameMissing(false)
    saveCommunityName(value)
    return value
  }

  async function submit(kind, text) {
    const author = requireName()
    if (!author) return false
    const item = await send(author, kind, text)
    setMine((current) => new Set(current).add(item.message_id))
    return true
  }

  return (
    <div className="community-room">
      <header className="community-head">
        <p>{copy.intro}</p>
        <span className={`community-status status-${status}`}>
          <i /> {copy.status[status] ?? status}
        </span>
      </header>

      <article className="community-summary">
        <span className={`editorial-status status-${record.status}`}>{t.recap.status[record.status]}</span>
        <h3>{record.draft.headline}</h3>
        <p>{record.draft.explanation}</p>
      </article>

      <label className={`community-name ${nameMissing ? 'is-invalid' : ''}`}>
        <span>{copy.name}</span>
        <input
          maxLength={40}
          onChange={(event) => { setName(event.target.value); setNameMissing(false) }}
          placeholder={copy.namePlaceholder}
          value={name}
        />
        {nameMissing && <small role="alert">{copy.nameNeeded}</small>}
      </label>

      <ErrorNotice message={error} />

      <div className="community-grid">
        <div className="community-column">
          <VotePanel lastEvent={lastEvent} onVote={async (choice) => { const author = requireName(); if (author) await vote(author, choice) }} room={room} />
          <MessageList
            emptyLabel={copy.noSuggestions}
            items={room?.suggestions ?? []}
            mine={mine}
            onSend={(text) => submit('suggestion', text)}
            placeholder={copy.suggestionPlaceholder}
            sendLabel={copy.sendSuggestion}
            title={copy.suggestions}
            variant="suggestions"
          />
        </div>
        <MessageList
          emptyLabel={copy.noChat}
          items={room?.chat ?? []}
          live
          mine={mine}
          onSend={(text) => submit('chat', text)}
          placeholder={copy.chatPlaceholder}
          sendLabel={copy.send}
          title={copy.chat}
          variant="chat"
        />
      </div>
      <p className="community-rules">
        <Icon name="shield" size={14} /> {copy.rules}
      </p>
    </div>
  )
}

function VotePanel({ room, onVote, lastEvent }) {
  const { t } = usePreferences()
  const copy = t.editorial.community
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const tally = room?.tally ?? { approve: 0, reject: 0, total: 0, approve_pct: null }
  const approvePct = tally.total ? Math.round((tally.approve / tally.total) * 100) : 0
  const flash = lastEvent ? copy.newVote(lastEvent.author, copy.voted[lastEvent.vote]) : null

  async function choose(choice) {
    setBusy(true)
    setError(null)
    try {
      await onVote(choice)
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="community-card vote-card" aria-labelledby="community-vote">
      <h4 id="community-vote">{copy.vote}</h4>
      <div className="vote-buttons">
        {['approve', 'reject'].map((choice) => (
          <button
            aria-pressed={room?.my_vote === choice}
            className={`vote-button vote-${choice} ${room?.my_vote === choice ? 'selected' : ''}`}
            disabled={busy || !room}
            key={choice}
            onClick={() => choose(choice)}
            type="button"
          >
            <Icon name={choice === 'approve' ? 'check' : 'close'} size={18} />
            {copy[choice]}
            <b>{choice === 'approve' ? tally.approve : tally.reject}</b>
          </button>
        ))}
      </div>
      <div className="vote-bar" role="img" aria-label={`${approvePct}% ${copy.approve}`}>
        <span className="vote-bar-approve" style={{ width: `${tally.total ? approvePct : 50}%` }} />
      </div>
      <p className="vote-meta" aria-live="polite">
        {tally.total ? `${approvePct}% ${copy.approve.toLowerCase()} · ${copy.tally(tally.total)}` : copy.noVotes}
      </p>
      {room?.my_vote && <p className="vote-mine">{copy.yourVote(copy.voted[room.my_vote])}</p>}
      {flash && <p className="vote-flash" key={lastEvent.at} role="status">{flash}</p>}
      {error && <p className="community-error" role="alert">{error}</p>}
    </section>
  )
}

function MessageList({ title, items, emptyLabel, placeholder, sendLabel, onSend, mine, variant, live = false }) {
  const { t } = usePreferences()
  const copy = t.editorial.community
  const [text, setText] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const list = useRef(null)
  const stickToBottom = useRef(true)

  // El chat baja solo con cada mensaje nuevo, salvo que la persona esté leyendo más arriba.
  useEffect(() => {
    const element = list.current
    if (live && element && stickToBottom.current) element.scrollTop = element.scrollHeight
  }, [items, live])

  async function submit(event) {
    event.preventDefault()
    if (!text.trim()) return
    setBusy(true)
    setError(null)
    try {
      if (await onSend(text)) setText('')
    } catch (err) {
      setError(err.status === 429 && err.data?.retry_after_s ? copy.wait(Math.ceil(err.data.retry_after_s)) : err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className={`community-card messages-card ${variant}`} aria-label={title}>
      <h4>
        {title} <i>{items.length}</i>
      </h4>
      <ol
        aria-live={live ? 'polite' : undefined}
        className="message-list"
        onScroll={(event) => {
          const element = event.currentTarget
          stickToBottom.current = element.scrollHeight - element.scrollTop - element.clientHeight < 40
        }}
        ref={list}
      >
        {items.length === 0 && <li className="message-empty">{emptyLabel}</li>}
        {(live ? items : [...items].reverse()).map((item) => (
          <li className={mine.has(item.message_id) ? 'is-mine' : ''} key={item.message_id}>
            <span className="message-author">
              {mine.has(item.message_id) ? copy.you : item.author}
              <time dateTime={item.created_at}>
                {new Date(item.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </time>
            </span>
            <p>{item.text}</p>
          </li>
        ))}
      </ol>
      <form className="message-form" onSubmit={submit}>
        <label className="sr-only" htmlFor={`message-${variant}`}>{placeholder}</label>
        <textarea
          id={`message-${variant}`}
          maxLength={500}
          onChange={(event) => setText(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter' && !event.shiftKey && live) submit(event)
          }}
          placeholder={placeholder}
          rows={live ? 1 : 2}
          value={text}
        />
        <Button disabled={busy || !text.trim()} type="submit">
          {live ? <Icon name="arrow" size={17} /> : sendLabel}
          {live && <span className="sr-only">{sendLabel}</span>}
        </Button>
      </form>
      {error && <p className="community-error" role="alert">{error}</p>}
    </section>
  )
}
