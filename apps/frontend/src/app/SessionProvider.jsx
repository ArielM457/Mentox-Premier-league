import { useCallback, useEffect, useMemo, useState } from 'react'
import { api, setAuthToken, UNAUTHORIZED_EVENT } from '../api/client.js'
import { ROLES, SESSION_KEY, SessionContext } from './session.js'

// La sesión se guarda en sessionStorage: dura mientras la pestaña esté abierta.
function load() {
  try {
    const saved = JSON.parse(sessionStorage.getItem(SESSION_KEY) ?? 'null')
    if (saved?.token && saved?.user) {
      setAuthToken(saved.token)
      return saved
    }
  } catch {
    // Sin almacenamiento la sesión dura solo hasta recargar.
  }
  return null
}

function persist(session) {
  try {
    if (session) sessionStorage.setItem(SESSION_KEY, JSON.stringify(session))
    else sessionStorage.removeItem(SESSION_KEY)
  } catch {
    // Ver load().
  }
}

export function SessionProvider({ children }) {
  const [session, setSession] = useState(load)

  const logout = useCallback(() => {
    setAuthToken(null)
    persist(null)
    setSession(null)
  }, [])

  const login = useCallback(async (username, password) => {
    const result = await api.login(username, password)
    const next = { token: result.token, user: result.user }
    setAuthToken(next.token)
    persist(next)
    setSession(next)
    return next.user
  }, [])

  useEffect(() => {
    window.addEventListener(UNAUTHORIZED_EVENT, logout)
    return () => window.removeEventListener(UNAUTHORIZED_EVENT, logout)
  }, [logout])

  const value = useMemo(
    () => ({
      user: session?.user ?? null,
      isAnalyst: session?.user?.role === ROLES.analyst,
      login,
      logout,
    }),
    [session, login, logout],
  )

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>
}
