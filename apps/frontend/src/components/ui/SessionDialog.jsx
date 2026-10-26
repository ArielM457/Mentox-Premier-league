import { useEffect, useRef, useState } from 'react'
import { usePreferences } from '../../app/preferences.js'
import { Button } from './Button.jsx'
import { Icon } from './Icon.jsx'

export function SessionDialog({ user, onClose, onSession }) {
  const { t } = usePreferences()
  const dialog = useRef(null)
  const [name, setName] = useState(user)
  useEffect(() => {
    const element = dialog.current
    element.showModal()
    return () => element.close()
  }, [])
  function submit(event) {
    event.preventDefault()
    const next = name.trim()
    if (!next) return
    try { sessionStorage.setItem('itg:demo-user', next) } catch { /* La demo también funciona sin almacenamiento. */ }
    onSession(next)
    onClose()
  }
  function logout() {
    try { sessionStorage.removeItem('itg:demo-user') } catch { /* Sesión solo en memoria. */ }
    onSession('')
    onClose()
  }
  return (
    <dialog ref={dialog} className="session-dialog" aria-labelledby="session-title" aria-describedby="session-description" onCancel={onClose} onClick={(event) => { if (event.target === event.currentTarget) onClose() }}>
      <button className="dialog-close" aria-label={t.common.close} onClick={onClose} type="button"><Icon name="close" /></button>
      <span className="session-avatar"><Icon name="user" size={28} /></span>
      <span className="section-kicker">{t.session.demo}</span>
      <h2 id="session-title">{user ? t.session.account : t.session.title}</h2>
      <p id="session-description">{t.session.description}</p>
      <form onSubmit={submit}>
        <label htmlFor="demo-name">{t.session.name}</label>
        <input autoFocus id="demo-name" autoComplete="off" maxLength={50} required value={name} onChange={(event) => setName(event.target.value)} />
        <Button type="submit">{user ? t.common.save : t.session.enter}<Icon name="arrow" size={18} /></Button>
      </form>
      {user && <Button variant="ghost" onClick={logout}>{t.session.logout}</Button>}
    </dialog>
  )
}
