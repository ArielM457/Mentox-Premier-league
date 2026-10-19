import { createContext, useContext } from 'react'

export const SESSION_KEY = 'itg:session'

export const ROLES = { fan: 'fan', analyst: 'analyst' }

export const SessionContext = createContext(null)

export function useSession() {
  const value = useContext(SessionContext)
  if (!value) throw new Error('useSession necesita SessionProvider')
  return value
}
