import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'

const STORAGE_KEY = 'breakpoint.selectedEngagementId'

interface EngagementContextValue {
  engagementId: number | null
  setEngagementId: (id: number | null) => void
}

const EngagementContext = createContext<EngagementContextValue | null>(null)

function readStoredEngagementId(): number | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? Number(raw) : null
  } catch {
    // localStorage kann in manchen Umgebungen (privater Modus, Storage
    // deaktiviert) einen Fehler werfen — Auswahl fällt dann auf "keins" zurück.
    return null
  }
}

export function EngagementProvider({ children }: { children: ReactNode }) {
  const [engagementId, setEngagementIdState] = useState<number | null>(readStoredEngagementId)

  useEffect(() => {
    try {
      if (engagementId === null) {
        localStorage.removeItem(STORAGE_KEY)
      } else {
        localStorage.setItem(STORAGE_KEY, String(engagementId))
      }
    } catch {
      // s.o. — Persistenz ist ein Komfortfeature, kein Korrektheitserfordernis.
    }
  }, [engagementId])

  const value = useMemo(() => ({ engagementId, setEngagementId: setEngagementIdState }), [engagementId])

  return <EngagementContext.Provider value={value}>{children}</EngagementContext.Provider>
}

// Context + zugehöriger Hook bewusst in einer Datei (Standard-React-Idiom) —
// oxlint(only-export-components) betrifft nur Fast-Refresh-Komfort, keine Korrektheit.
// eslint-disable-next-line react-refresh/only-export-components
export function useEngagement(): EngagementContextValue {
  const ctx = useContext(EngagementContext)
  if (!ctx) {
    throw new Error('useEngagement muss innerhalb von <EngagementProvider> verwendet werden')
  }
  return ctx
}
