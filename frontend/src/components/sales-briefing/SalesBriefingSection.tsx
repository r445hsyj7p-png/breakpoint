import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'

import {
  getLatestSalesBriefing,
  markSalesBriefingReviewed,
  triggerSalesBriefing,
} from '../../lib/api'

const STATUS_LABEL: Record<string, string> = {
  pending: 'Wird generiert …',
  ready: 'Bereit',
  flagged_for_review: 'Zur Nachbearbeitung markiert',
  failed: 'Fehlgeschlagen',
}

export function SalesBriefingSection({ engagementId }: { engagementId: number }) {
  const queryClient = useQueryClient()
  const [reviewerName, setReviewerName] = useState('')

  const briefingQuery = useQuery({
    queryKey: ['sales-briefing', engagementId],
    queryFn: () => getLatestSalesBriefing(engagementId),
    refetchInterval: (query) => (query.state.data?.status === 'pending' ? 2000 : false),
  })

  const generateMutation = useMutation({
    mutationFn: () => triggerSalesBriefing(engagementId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sales-briefing', engagementId] })
    },
  })

  const reviewMutation = useMutation({
    mutationFn: (briefingId: number) => markSalesBriefingReviewed(briefingId, reviewerName || undefined),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sales-briefing', engagementId] })
      setReviewerName('')
    },
  })

  const briefing = briefingQuery.data ?? null

  return (
    <div className="rounded-lg border border-line bg-graphite-900 p-6">
      <div className="mb-4 flex items-center justify-between">
        <div className="text-[15px] font-semibold">Sales-Briefing</div>
        <button
          className="rounded-md bg-amber px-4 py-2 text-sm font-semibold text-[#241a08] hover:bg-[#f0b355] disabled:opacity-50"
          onClick={() => generateMutation.mutate()}
          disabled={generateMutation.isPending || briefing?.status === 'pending'}
        >
          Sales-Briefing generieren
        </button>
      </div>

      {generateMutation.isError && (
        <div className="mb-3 text-[12px] text-ember">
          Generierung fehlgeschlagen: {(generateMutation.error as Error).message}
        </div>
      )}

      {briefingQuery.isLoading && <div className="text-[12.5px] text-ink-600">Lade …</div>}

      {!briefingQuery.isLoading && !briefing && (
        <div className="text-[12.5px] text-ink-600">
          Noch kein Sales-Briefing generiert.
        </div>
      )}

      {briefing && (
        <div className="flex flex-col gap-4">
          <div className="flex items-center gap-2">
            <span
              className={`rounded-md px-2 py-0.5 text-[11px] font-semibold ${
                briefing.status === 'ready'
                  ? 'bg-portfolio-dim text-portfolio'
                  : briefing.status === 'pending'
                    ? 'bg-graphite-800 text-ink-400'
                    : briefing.status === 'flagged_for_review'
                      ? 'bg-amber/15 text-amber'
                      : 'bg-ember/15 text-ember'
              }`}
            >
              {STATUS_LABEL[briefing.status] ?? briefing.status}
            </span>
            {briefing.model_version && (
              <span className="text-[11px] text-ink-600">Modell: {briefing.model_version}</span>
            )}
          </div>

          {briefing.status === 'flagged_for_review' && (
            <div className="rounded-md border border-amber/40 bg-amber/10 px-3 py-2 text-[12px] text-amber">
              Dieses Briefing wurde markiert, weil möglicherweise technische Details (ATT&CK-IDs)
              enthalten sind. Bitte vor Kundenkontakt prüfen und ggf. anpassen.
            </div>
          )}

          {briefing.status === 'failed' && (
            <div className="rounded-md border border-ember/40 bg-ember/10 px-3 py-2 text-[12px] text-ember">
              Generierung fehlgeschlagen: {briefing.error_message}
            </div>
          )}

          {briefing.content && (
            <div className="flex flex-col gap-4">
              <div>
                <div className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-ink-500">
                  Executive Summary
                </div>
                <p className="text-[13px] text-ink-200">{briefing.content.executive_summary}</p>
              </div>

              <div className="flex flex-col gap-3">
                <div className="text-[11px] font-semibold uppercase tracking-wide text-ink-500">
                  Priorisierte Maßnahmen
                </div>
                {briefing.content.top_massnahmen.map((m, i) => (
                  <div key={i} className="rounded-md border border-line-soft bg-graphite-850 p-3.5">
                    <div className="text-[13px] font-semibold text-ink-100">{m.massnahme}</div>
                    <div className="mt-2 flex flex-col gap-1.5 text-[12.5px] text-ink-300">
                      <div>
                        <span className="font-semibold text-ink-400">Kundennutzen: </span>
                        {m.kunden_nutzen}
                      </div>
                      <div>
                        <span className="font-semibold text-ink-400">Risiko ohne Maßnahme: </span>
                        {m.risiko_ohne_massnahme}
                      </div>
                      <div>
                        <span className="font-semibold text-ink-400">Einwand-Antizipation: </span>
                        {m.einwand_antizipation}
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              <div>
                <div className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-ink-500">
                  Nächster Schritt
                </div>
                <p className="text-[13px] text-ink-200">{briefing.content.naechster_schritt}</p>
              </div>
            </div>
          )}

          {(briefing.status === 'ready' || briefing.status === 'flagged_for_review') && (
            <div className="flex flex-wrap items-center gap-2 border-t border-line-soft pt-3.5">
              {briefing.reviewed_at ? (
                <span className="text-[11.5px] text-ink-500">
                  Geprüft {briefing.reviewed_by ? `von ${briefing.reviewed_by} ` : ''}am{' '}
                  {new Date(briefing.reviewed_at).toLocaleString('de-DE')}
                </span>
              ) : (
                <>
                  <input
                    className="min-w-40 rounded-md border border-line bg-graphite-850 px-2.5 py-1.5 text-[12.5px] text-ink-100 outline-none placeholder:text-ink-600"
                    placeholder="Name (optional)"
                    value={reviewerName}
                    onChange={(e) => setReviewerName(e.target.value)}
                  />
                  <button
                    className="rounded-md border border-line px-3 py-1.5 text-[12.5px] font-semibold text-ink-300 hover:bg-graphite-800 hover:text-ink-100 disabled:opacity-50"
                    onClick={() => reviewMutation.mutate(briefing.id)}
                    disabled={reviewMutation.isPending}
                  >
                    Als geprüft freigeben
                  </button>
                </>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
