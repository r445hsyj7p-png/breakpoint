import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'

import { AnalyzerResultView } from '../components/analyzer/AnalyzerResultView'
import { SalesBriefingSection } from '../components/sales-briefing/SalesBriefingSection'
import { addFindings, createEngagement, getEngagementAnalysis, listEngagements } from '../lib/api'
import { useEngagement } from '../lib/EngagementContext'

export function Engagements() {
  const queryClient = useQueryClient()
  const { engagementId, setEngagementId } = useEngagement()
  const [newName, setNewName] = useState('')
  const [findingsInput, setFindingsInput] = useState('')

  const { data: engagements, isLoading } = useQuery({ queryKey: ['engagements'], queryFn: listEngagements })

  const createMutation = useMutation({
    mutationFn: () => createEngagement(newName),
    onSuccess: (created) => {
      queryClient.invalidateQueries({ queryKey: ['engagements'] })
      setEngagementId(created.id)
      setNewName('')
    },
  })

  const findingsMutation = useMutation({
    mutationFn: ({ engagementId: targetId, codes }: { engagementId: number; codes: string }) =>
      addFindings(targetId, codes),
    // Verwendet die Engagement-ID aus den Mutation-Variablen, nicht aus dem
    // äußeren Closure-Scope: TanStack Query bindet onSuccess bei jedem
    // Render neu, sonst würde ein Engagement-Wechsel während der laufenden
    // Anfrage die Analyse des FALSCHEN (neu ausgewählten) Engagements
    // invalidieren statt der des Engagements, für das die Findings
    // tatsächlich hinzugefügt wurden.
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['engagement-analysis', variables.engagementId] })
      setFindingsInput('')
    },
  })

  const analysisQuery = useQuery({
    queryKey: ['engagement-analysis', engagementId],
    queryFn: () => getEngagementAnalysis(engagementId!),
    enabled: engagementId !== null,
  })

  return (
    <div className="flex flex-col gap-7">
      <div>
        <h1 className="font-display text-[22px] font-semibold">Engagements</h1>
        <p className="mt-1 max-w-2xl text-[13px] text-ink-400">
          Red-Team-/Pentest-Engagements anlegen und T-Nummern dagegen sammeln.
        </p>
      </div>

      <div className="rounded-lg border border-line bg-graphite-900 p-6">
        <div className="mb-4 text-[15px] font-semibold">Neues Engagement</div>
        <form
          className="flex flex-wrap items-center gap-3"
          onSubmit={(e) => {
            e.preventDefault()
            if (newName.trim()) createMutation.mutate()
          }}
        >
          <input
            className="min-w-64 flex-1 rounded-md border border-line bg-graphite-850 px-3 py-2 text-sm text-ink-100 outline-none placeholder:text-ink-600"
            placeholder="z. B. Red Team Assessment 2026"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
          />
          <button
            type="submit"
            className="rounded-md bg-amber px-4 py-2 text-sm font-semibold text-[#241a08] hover:bg-[#f0b355] disabled:opacity-50"
            disabled={!newName.trim() || createMutation.isPending}
          >
            Anlegen
          </button>
        </form>
        {createMutation.isError && (
          <div className="mt-3 text-[12px] text-ember">
            Anlegen fehlgeschlagen: {(createMutation.error as Error).message}
          </div>
        )}
      </div>

      <div className="rounded-lg border border-line bg-graphite-900 p-6">
        <div className="mb-4 text-[15px] font-semibold">Bestehende Engagements</div>
        {isLoading && <div className="text-[12.5px] text-ink-600">Lade …</div>}
        {engagements?.length === 0 && (
          <div className="text-[12.5px] text-ink-600">Noch keine Engagements angelegt.</div>
        )}
        <div className="flex flex-col gap-1.5">
          {engagements?.map((e) => (
            <button
              key={e.id}
              onClick={() => setEngagementId(e.id)}
              className={`flex items-center justify-between rounded-md border px-3.5 py-2.5 text-left text-sm ${
                engagementId === e.id
                  ? 'border-amber/50 bg-graphite-800 text-ink-100'
                  : 'border-line-soft bg-graphite-850 text-ink-300 hover:bg-graphite-800'
              }`}
            >
              <span>{e.name}</span>
              <span className="text-[11px] text-ink-600">{e.status}</span>
            </button>
          ))}
        </div>
      </div>

      {engagementId !== null && (
        <div className="rounded-lg border border-line bg-graphite-900 p-6">
          <div className="mb-4 text-[15px] font-semibold">T-Nummern hinzufügen</div>
          <form
            className="flex flex-wrap items-start gap-3"
            onSubmit={(e) => {
              e.preventDefault()
              if (findingsInput.trim()) {
                findingsMutation.mutate({ engagementId: engagementId!, codes: findingsInput })
              }
            }}
          >
            <input
              className="min-w-64 flex-1 rounded-md border border-line bg-graphite-850 px-3 py-2 font-mono text-[13px] text-ink-100 outline-none placeholder:text-ink-600"
              placeholder="T1566.001, T1078 …"
              value={findingsInput}
              onChange={(e) => setFindingsInput(e.target.value)}
            />
            <button
              type="submit"
              className="rounded-md border border-line bg-graphite-850 px-4 py-2 text-sm font-semibold text-ink-300 hover:bg-graphite-800 hover:text-ink-100 disabled:opacity-50"
              disabled={!findingsInput.trim() || findingsMutation.isPending}
            >
              Hinzufügen
            </button>
          </form>
          {findingsMutation.isSuccess && findingsMutation.data.unknown_codes.length > 0 && (
            <div className="mt-3 text-[12px] text-ember">
              Nicht erkannt: {findingsMutation.data.unknown_codes.join(', ')}
            </div>
          )}
          {findingsMutation.isError && (
            <div className="mt-3 text-[12px] text-ember">
              Hinzufügen fehlgeschlagen: {(findingsMutation.error as Error).message}
            </div>
          )}
        </div>
      )}

      {engagementId !== null && analysisQuery.data && <AnalyzerResultView result={analysisQuery.data} />}

      {engagementId !== null && <SalesBriefingSection engagementId={engagementId} />}
    </div>
  )
}
