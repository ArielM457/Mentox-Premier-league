import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { api, setAuthToken, UNAUTHORIZED_EVENT } from '../api/client.js'
import { ROLES, SESSION_KEY, SessionContext } from './session.js'

// "Recordarme" guarda la sesión en localStorage; si no, en sessionStorage (se cierra con la pestaña).
function storages() {
  try {
    return [localStorage, sessionStorage]
  } catch {
    return []
  }
}

function load() {
  for (const storage of storages()) {
    try {
      const saved = JSON.parse(storage.getItem(SESSION_KEY) ?? 'null')
      if (saved?.token && saved?.user && saved.expiresAt * 1000 > Date.now()) {
        setAuthToken(saved.token)
        return saved
      }
      storage.removeItem(SESSION_KEY)
    } catch {
      // Almacenamiento no disponible: se intenta con el siguiente.
    }
  }
  return null
}

function persist(session) {
  for (const storage of storages()) {
    try {
      storage.removeItem(SESSION_KEY)
      if (session && (storage === localStorage) === session.remember) storage.setItem(SESSION_KEY, JSON.stringify(session))
    } catch {
      // Sin almacenamiento la sesión dura hasta recargar.
    }
  }
}

export function SessionProvider({ children }) {
  const [session, setSession] = useState(load)
  // Motivo del último cierre automático, para explicarlo en la pantalla de inicio de sesión.
  const [notice, setNotice] = useState(null)

  const clear = useCallback((reason = null) => {
    setAuthToken(null)
    persist(null)
    setSession(null)
    setNotice(reason)
  }, [])

  const logout = useCallback(() => {
    // Se revoca en el servidor sin esperar: cerrar sesión siempre funciona en la interfaz.
    api.logout().catch(() => {})
    clear(null)
  }, [clear])

  const login = useCallback(async (username, password, remember) => {
    const result = await api.login(username, password)
    const next = { token: result.token, user: result.user, expiresAt: result.expires_at, remember }
    setAuthToken(next.token)
    persist(next)
    setSession(next)
    setNotice(null)
    return next.user
  }, [])

  // Cualquier 401 de la API cierra la sesión (token vencido o revocado).
  useEffect(() => {
    const onUnauthorized = () => clear('expired')
    window.addEventListener(UNAUTHORIZED_EVENT, onUnauthorized)
    return () => window.removeEventListener(UNAUTHORIZED_EVENT, onUnauthorized)
  }, [clear])

  // Al abrir la app se confirma con el servidor que la sesión guardada sigue vigente
  // (pudo cerrarse en otra pestaña o el backend pudo reiniciarse con otro secreto).
  const checkedToken = useRef(null)
  useEffect(() => {
    if (!session || checkedToken.current === session.token) return
    checkedToken.current = session.token
    api.me().catch((err) => {
      if (err.status === 401) clear('expired')
    })
  }, [session, clear])

  // Cierre automático cuando vence el token, aunque no se haga ninguna petición.
  useEffect(() => {
    if (!session) return undefined
    const ms = session.expiresAt * 1000 - Date.now()
    const id = setTimeout(() => clear('expired'), Math.max(0, Math.min(ms, 2 ** 31 - 1)))
    return () => clearTimeout(id)
  }, [session, clear])

  const value = useMemo(
    () => ({
      user: session?.user ?? null,
      expiresAt: session?.expiresAt ?? null,
      isAnalyst: session?.user?.role === ROLES.analyst,
      notice,
      dismissNotice: () => setNotice(null),
      login,
      logout,
    }),
    [session, notice, login, logout],
  )

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>
}
