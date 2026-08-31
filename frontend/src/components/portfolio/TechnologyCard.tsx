import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'

import type { CapabilityRead, PortfolioTechnologyRead } from '../../lib/api'
import { getPortfolioTechnologyHistory } from '../../lib/api'
import { CapabilityCheckboxList } from './CapabilityCheckboxList'

export function TechnologyCard({
  technology,
  capabilities,
  onUpdate,
  onDeactivate,
  isUpdating,
}: {
  technology: PortfolioTechnologyRead
  capabilities: CapabilityRead[]
  onUpdate: (id: number, payload: { name: string; type: string; capability_ids: number[] }) => void
  onDeactivate: (id: number) => void
  isUpdating: boolean
}) {
  const [isEditing, setIsEditing] = useState(false)
  const [showHistory, setShowHistory] = useState(false)
  const [name, setName] = useState(technology.name)
  const [type, setType] = useState(technology.type)
  const [selectedIds, setSelectedIds] = useState<Set<number>>(
    () => new Set(capabilities.filter((c) => technology.capabilities.includes(c.name)).map((c) => c.id)),
  )

  const historyQuery = useQuery({
    queryKey: ['portfolio-history', technology.id],
    queryFn: () => getPortfolioTechnologyHistory(technology.id),
    enabled: showHistory,
  })

  function startEditing() {
    setName(technology.name)
    setType(technology.type)
    setSelectedIds(new Set(capabilities.filter((c) => technology.capabilities.includes(c.name)).map((c) => c.id)))
    setIsEditing(true)
  }

  function save() {
    onUpdate(technology.id, { name, type, capability_ids: [...selectedIds] })
    setIsEditing(false)
  }

  return (
    <div className="flex flex-col gap-3 rounded-md border border-line bg-graphite-850 p-4">
      {isEditing ? (
        <>
          <input
            className="rounded-md border border-line bg-graphite-900 px-2.5 py-1.5 text-sm text-ink-100 outline-none"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
          <input
            className="rounded-md border border-line bg-graphite-900 px-2.5 py-1.5 text-[12.5px] text-ink-300 outline-none"
            value={type}
            onChange={(e) => setType(e.target.value)}
          />
          <CapabilityCheckboxList capabilities={capabilities} selectedIds={selectedIds} onChange={setSelectedIds} />
          <div className="flex gap-2">
            <button
              className="rounded-md bg-amber px-3 py-1.5 text-[12.5px] font-semibold text-[#241a08] disabled:opacity-50"
              disabled={!name.trim() || !type.trim() || isUpdating}
              onClick={save}
            >
              Speichern
            </button>
            <button
              className="rounded-md border border-line px-3 py-1.5 text-[12.5px] text-ink-300 hover:text-ink-100"
              onClick={() => setIsEditing(false)}
            >
              Abbrechen
            </button>
          </div>
        </>
      ) : (
        <>
          <div className="flex items-start justify-between gap-2.5">
            <div>
              <div className="flex items-center gap-1.5">
                <div className="text-[13.5px] font-semibold">{technology.name}</div>
                {!technology.active && (
                  <span className="rounded-md bg-graphite-800 px-1.5 py-0.5 text-[10px] font-semibold text-ink-500">
                    Inaktiv
                  </span>
                )}
              </div>
              <div className="mt-0.5 text-[11px] font-semibold text-portfolio">{technology.type}</div>
            </div>
            <div className="flex h-8 w-8 flex-none items-center justify-center rounded-md bg-portfolio-dim text-portfolio">
              ◆
            </div>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {technology.capabilities.map((c) => (
              <span key={c} className="rounded-md border border-portfolio/35 bg-portfolio-dim px-2 py-0.5 text-[11px] font-semibold text-portfolio">
                {c}
              </span>
            ))}
            {technology.capabilities.length === 0 && (
              <span className="text-[11.5px] text-ink-600">Keine Capabilities zugeordnet.</span>
            )}
          </div>
          <div className="flex flex-wrap gap-3 text-[11.5px]">
            <button className="font-semibold text-amber hover:text-[#f0b355]" onClick={startEditing}>
              Bearbeiten
            </button>
            {technology.active && (
              <button
                className="font-semibold text-ember hover:opacity-80 disabled:opacity-50"
                onClick={() => onDeactivate(technology.id)}
                disabled={isUpdating}
              >
                Deaktivieren
              </button>
            )}
            <button
              className="font-semibold text-ink-400 hover:text-ink-100"
              onClick={() => setShowHistory((v) => !v)}
            >
              {showHistory ? 'Verlauf ausblenden' : 'Verlauf anzeigen'}
            </button>
          </div>
          {showHistory && (
            <div className="flex flex-col gap-1.5 border-t border-line-soft pt-3">
              {historyQuery.isLoading && <div className="text-[11.5px] text-ink-600">Lade …</div>}
              {historyQuery.data?.length === 0 && (
                <div className="text-[11.5px] text-ink-600">Keine Änderungen protokolliert.</div>
              )}
              {historyQuery.data?.map((entry) => (
                <div key={entry.id} className="text-[11.5px] text-ink-400">
                  <span className="font-mono text-ink-600">{new Date(entry.changed_at).toLocaleString('de-DE')}</span>
                  {' — '}
                  <strong className="text-ink-300">{entry.field_changed}</strong>: {entry.old_value || '—'} →{' '}
                  {entry.new_value || '—'}
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  )
}
