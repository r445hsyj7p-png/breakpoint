import type { ImportBatchRead } from '../../lib/api'

const STATUS_LABEL: Record<string, string> = {
  diff_pending: 'Wird berechnet …',
  diff_ready: 'Bereit zur Übernahme',
  applied: 'Übernommen',
  rolled_back: 'Zurückgerollt',
  failed: 'Fehlgeschlagen',
}

const STATUS_CLASS: Record<string, string> = {
  diff_pending: 'bg-graphite-800 text-ink-400',
  diff_ready: 'bg-detect-dim text-detect',
  applied: 'bg-prevent-dim text-prevent',
  rolled_back: 'bg-graphite-800 text-ink-400',
  failed: 'bg-ember-dim text-ember',
}

export function ImportBatchHistory({
  batches,
  selectedBatchId,
  latestAppliedBatchId,
  onSelect,
  onRollback,
  isRollingBack,
}: {
  batches: ImportBatchRead[]
  selectedBatchId: number | null
  latestAppliedBatchId: number | null
  onSelect: (id: number) => void
  onRollback: (id: number) => void
  isRollingBack: boolean
}) {
  return (
    <div className="flex flex-col gap-1.5">
      {batches.map((batch) => (
        <div
          key={batch.id}
          className={`flex items-center justify-between gap-3 rounded-md border px-3.5 py-2.5 text-[12.5px] ${
            selectedBatchId === batch.id
              ? 'border-amber/50 bg-graphite-800'
              : 'border-line-soft bg-graphite-850'
          }`}
        >
          <button className="flex items-center gap-3 text-left" onClick={() => onSelect(batch.id)}>
            <span className="text-ink-500">#{batch.id}</span>
            <span className="text-ink-300">{batch.source}</span>
            <span className="text-[11px] text-ink-600">{new Date(batch.created_at).toLocaleString('de-DE')}</span>
            {batch.triggered_by && <span className="text-[11px] text-ink-600">von {batch.triggered_by}</span>}
          </button>
          <div className="flex items-center gap-2.5">
            <span className={`rounded-md px-2 py-0.5 text-[11px] font-semibold ${STATUS_CLASS[batch.status] ?? ''}`}>
              {STATUS_LABEL[batch.status] ?? batch.status}
            </span>
            {batch.status === 'applied' && batch.id === latestAppliedBatchId && (
              <button
                className="text-[11px] font-semibold text-ember hover:opacity-80 disabled:opacity-50"
                disabled={isRollingBack}
                onClick={() => onRollback(batch.id)}
              >
                Rückgängig
              </button>
            )}
          </div>
        </div>
      ))}
      {batches.length === 0 && <div className="text-[12.5px] text-ink-600">Noch keine Imports durchgeführt.</div>}
    </div>
  )
}
