import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useRef, useState } from 'react'

import { ImportBatchHistory } from '../../components/admin/ImportBatchHistory'
import { ImportDiffView } from '../../components/admin/ImportDiffView'
import {
  applyMitreImportBatch,
  getMitreImportBatch,
  listMitreImportBatches,
  rollbackMitreImportBatch,
  triggerMitreImportFetch,
  uploadMitreImportBundle,
} from '../../lib/api'

export function MitreImport() {
  const queryClient = useQueryClient()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [triggeredBy, setTriggeredBy] = useState('')
  const [selectedBatchId, setSelectedBatchId] = useState<number | null>(null)

  const batchesQuery = useQuery({ queryKey: ['mitre-import-batches'], queryFn: listMitreImportBatches })

  const batchQuery = useQuery({
    queryKey: ['mitre-import-batch', selectedBatchId],
    queryFn: () => getMitreImportBatch(selectedBatchId!),
    enabled: selectedBatchId !== null,
    refetchInterval: (query) => (query.state.data?.status === 'diff_pending' ? 2000 : false),
  })

  function invalidateAll() {
    queryClient.invalidateQueries({ queryKey: ['mitre-import-batches'] })
    queryClient.invalidateQueries({ queryKey: ['mitre-import-batch', selectedBatchId] })
  }

  const fetchMutation = useMutation({
    mutationFn: () => triggerMitreImportFetch(triggeredBy || undefined),
    onSuccess: (batch) => {
      setSelectedBatchId(batch.id)
      invalidateAll()
    },
  })

  const uploadMutation = useMutation({
    mutationFn: (file: File) => uploadMitreImportBundle(file, triggeredBy || undefined),
    onSuccess: (batch) => {
      setSelectedBatchId(batch.id)
      invalidateAll()
      if (fileInputRef.current) fileInputRef.current.value = ''
    },
  })

  const applyMutation = useMutation({
    mutationFn: (selection: { technique_ids: string[]; mitigation_technique_ids: string[] }) =>
      applyMitreImportBatch(selectedBatchId!, selection),
    onSuccess: invalidateAll,
  })

  const rollbackMutation = useMutation({
    mutationFn: (batchId: number) => rollbackMitreImportBatch(batchId),
    onSuccess: invalidateAll,
  })

  const batches = batchesQuery.data ?? []
  const latestAppliedBatchId = batches.find((b) => b.status === 'applied')?.id ?? null
  const batch = batchQuery.data

  return (
    <div className="flex flex-col gap-7">
      <div>
        <h1 className="font-display text-[22px] font-semibold">MITRE-Techniken-Import</h1>
        <p className="mt-1 max-w-2xl text-[13px] text-ink-400">
          Admin-gesteuerter Import des offiziellen ATT&amp;CK-STIX-Bundles: neue/geänderte Techniken plus
          automatisch abgeleitete Prevent-Mappings aus MITRE-Mitigations (M-Nummern). Nichts wird ohne
          explizite Auswahl übernommen — bestehende, händisch kuratierte Mappings werden nie überschrieben.
        </p>
      </div>

      <div className="rounded-lg border border-line bg-graphite-900 p-6">
        <div className="mb-4 text-[15px] font-semibold">Neuer Import</div>
        <div className="flex flex-wrap items-center gap-3">
          <input
            className="min-w-48 rounded-md border border-line bg-graphite-850 px-3 py-2 text-sm text-ink-100 outline-none placeholder:text-ink-600"
            placeholder="Name (optional)"
            value={triggeredBy}
            onChange={(e) => setTriggeredBy(e.target.value)}
          />
          <button
            className="rounded-md bg-amber px-4 py-2 text-sm font-semibold text-[#241a08] hover:bg-[#f0b355] disabled:opacity-50"
            disabled={fetchMutation.isPending}
            onClick={() => fetchMutation.mutate()}
          >
            Von GitHub laden
          </button>
          <span className="text-[12px] text-ink-500">oder</span>
          <input
            ref={fileInputRef}
            type="file"
            accept="application/json"
            className="text-[12.5px] text-ink-300"
            onChange={(e) => {
              const file = e.target.files?.[0]
              if (file) uploadMutation.mutate(file)
            }}
          />
        </div>
        {fetchMutation.isError && (
          <div className="mt-3 text-[12px] text-ember">
            Laden fehlgeschlagen: {(fetchMutation.error as Error).message}
          </div>
        )}
        {uploadMutation.isError && (
          <div className="mt-3 text-[12px] text-ember">
            Upload fehlgeschlagen: {(uploadMutation.error as Error).message}
          </div>
        )}
      </div>

      <div className="rounded-lg border border-line bg-graphite-900 p-6">
        <div className="mb-4 text-[15px] font-semibold">Import-Historie</div>
        <ImportBatchHistory
          batches={batches}
          selectedBatchId={selectedBatchId}
          latestAppliedBatchId={latestAppliedBatchId}
          onSelect={setSelectedBatchId}
          onRollback={(id) => rollbackMutation.mutate(id)}
          isRollingBack={rollbackMutation.isPending}
        />
        {rollbackMutation.isError && (
          <div className="mt-3 text-[12px] text-ember">
            Rückgängig machen fehlgeschlagen: {(rollbackMutation.error as Error).message}
          </div>
        )}
      </div>

      {selectedBatchId !== null && (
        <div className="rounded-lg border border-line bg-graphite-900 p-6">
          <div className="mb-4 text-[15px] font-semibold">Batch #{selectedBatchId}</div>

          {batchQuery.isLoading && <div className="text-[12.5px] text-ink-600">Lade …</div>}

          {batch?.status === 'diff_pending' && (
            <div className="text-[12.5px] text-ink-500">Diff wird im Hintergrund berechnet …</div>
          )}

          {batch?.status === 'failed' && (
            <div className="rounded-md border border-ember/40 bg-ember/10 px-3 py-2 text-[12px] text-ember">
              Import fehlgeschlagen: {batch.error_message}
            </div>
          )}

          {batch?.status === 'diff_ready' && batch.diff_snapshot && (
            <>
              <ImportDiffView
                diff={batch.diff_snapshot}
                onApply={(selection) => applyMutation.mutate(selection)}
                isApplying={applyMutation.isPending}
              />
              {applyMutation.isError && (
                <div className="mt-3 text-[12px] text-ember">
                  Übernehmen fehlgeschlagen: {(applyMutation.error as Error).message}
                </div>
              )}
            </>
          )}

          {(batch?.status === 'applied' || batch?.status === 'rolled_back') && (
            <div className="text-[12.5px] text-ink-400">
              {batch.status === 'applied'
                ? `Übernommen am ${batch.applied_at ? new Date(batch.applied_at).toLocaleString('de-DE') : '—'}.`
                : `Zurückgerollt am ${batch.rolled_back_at ? new Date(batch.rolled_back_at).toLocaleString('de-DE') : '—'}.`}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
