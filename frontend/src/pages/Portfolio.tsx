import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'

import { CapabilityCheckboxList } from '../components/portfolio/CapabilityCheckboxList'
import { CoverageMatrix } from '../components/portfolio/CoverageMatrix'
import { TechnologyCard } from '../components/portfolio/TechnologyCard'
import {
  createPortfolioTechnology,
  deactivatePortfolioTechnology,
  getPortfolioCoverage,
  listCapabilities,
  listPortfolioTechnologies,
  updatePortfolioTechnology,
} from '../lib/api'

export function Portfolio() {
  const queryClient = useQueryClient()
  const [newName, setNewName] = useState('')
  const [newType, setNewType] = useState('')
  const [newCapabilityIds, setNewCapabilityIds] = useState<Set<number>>(new Set())

  const technologiesQuery = useQuery({ queryKey: ['portfolio-technologies'], queryFn: () => listPortfolioTechnologies() })
  const capabilitiesQuery = useQuery({ queryKey: ['capabilities'], queryFn: listCapabilities })
  const coverageQuery = useQuery({ queryKey: ['portfolio-coverage'], queryFn: getPortfolioCoverage })

  function invalidateAll() {
    queryClient.invalidateQueries({ queryKey: ['portfolio-technologies'] })
    queryClient.invalidateQueries({ queryKey: ['portfolio-coverage'] })
  }

  const createMutation = useMutation({
    mutationFn: () =>
      createPortfolioTechnology({ name: newName, type: newType, capability_ids: [...newCapabilityIds] }),
    onSuccess: () => {
      invalidateAll()
      setNewName('')
      setNewType('')
      setNewCapabilityIds(new Set())
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: { name: string; type: string; capability_ids: number[] } }) =>
      updatePortfolioTechnology(id, payload),
    onSuccess: invalidateAll,
  })

  const deactivateMutation = useMutation({
    mutationFn: (id: number) => deactivatePortfolioTechnology(id),
    onSuccess: invalidateAll,
  })

  const technologyNames = technologiesQuery.data?.map((t) => t.name) ?? []

  return (
    <div className="flex flex-col gap-7">
      <div>
        <h1 className="font-display text-[22px] font-semibold">Technologie-Mapping</h1>
        <p className="mt-1 max-w-2xl text-[13px] text-ink-400">
          Zweite Ebene der Übersetzung: welche eigenen Technologien decken eine Security Capability
          tatsächlich ab. Die Empfehlung selbst bleibt herstellerneutral — dies ist die optionale
          Zuordnung dahinter.
        </p>
      </div>

      <div className="rounded-lg border border-line bg-graphite-900 p-6">
        <div className="mb-4 text-[15px] font-semibold">Neue Technologie</div>
        <form
          className="flex flex-col gap-3"
          onSubmit={(e) => {
            e.preventDefault()
            if (newName.trim() && newType.trim()) createMutation.mutate()
          }}
        >
          <div className="flex flex-wrap gap-3">
            <input
              className="min-w-56 flex-1 rounded-md border border-line bg-graphite-850 px-3 py-2 text-sm text-ink-100 outline-none placeholder:text-ink-600"
              placeholder="Name, z. B. Okta"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
            />
            <input
              className="min-w-56 flex-1 rounded-md border border-line bg-graphite-850 px-3 py-2 text-sm text-ink-100 outline-none placeholder:text-ink-600"
              placeholder="Typ, z. B. Identity"
              value={newType}
              onChange={(e) => setNewType(e.target.value)}
            />
          </div>
          {capabilitiesQuery.data && (
            <CapabilityCheckboxList
              capabilities={capabilitiesQuery.data}
              selectedIds={newCapabilityIds}
              onChange={setNewCapabilityIds}
            />
          )}
          <button
            type="submit"
            className="w-fit rounded-md bg-amber px-4 py-2 text-sm font-semibold text-[#241a08] hover:bg-[#f0b355] disabled:opacity-50"
            disabled={!newName.trim() || !newType.trim() || createMutation.isPending}
          >
            Anlegen
          </button>
          {createMutation.isError && (
            <div className="text-[12px] text-ember">Anlegen fehlgeschlagen: {(createMutation.error as Error).message}</div>
          )}
        </form>
      </div>

      <div className="rounded-lg border border-line bg-graphite-900 p-6">
        <div className="mb-1 text-[15px] font-semibold">Portfolio-Technologien</div>
        <div className="mb-4 text-xs text-ink-400">
          {technologiesQuery.data?.length ?? 0} Technologien / Services, zugeordnet zu Security Capabilities
        </div>
        <div className="grid grid-cols-[repeat(auto-fill,minmax(280px,1fr))] gap-3.5">
          {technologiesQuery.data?.map((t) => (
            <TechnologyCard
              key={t.id}
              technology={t}
              capabilities={capabilitiesQuery.data ?? []}
              isUpdating={updateMutation.isPending || deactivateMutation.isPending}
              onUpdate={(id, payload) => updateMutation.mutate({ id, payload })}
              onDeactivate={(id) => deactivateMutation.mutate(id)}
            />
          ))}
          {technologiesQuery.data?.length === 0 && (
            <div className="text-[12.5px] text-ink-600">Noch keine Portfolio-Technologien angelegt.</div>
          )}
        </div>
        {updateMutation.isError && (
          <div className="mt-3 text-[12px] text-ember">
            Bearbeiten fehlgeschlagen: {(updateMutation.error as Error).message}
          </div>
        )}
        {deactivateMutation.isError && (
          <div className="mt-3 text-[12px] text-ember">
            Deaktivieren fehlgeschlagen: {(deactivateMutation.error as Error).message}
          </div>
        )}
      </div>

      <div className="rounded-lg border border-line bg-graphite-900 p-6">
        <div className="mb-1 text-[15px] font-semibold">Coverage-Matrix</div>
        <div className="mb-4 text-xs text-ink-400">Welche Capability wird durch welche Portfolio-Technologie abgedeckt</div>
        {coverageQuery.data && <CoverageMatrix coverage={coverageQuery.data} technologyNames={technologyNames} />}
      </div>

      <div className="rounded-md border border-ember/30 bg-ember-dim p-4">
        <div className="mb-2 text-[12.5px] font-semibold text-[#F5B7A8]">
          ⚠ Ungedeckte Capabilities — kein Portfolio-Fit
        </div>
        <div className="flex flex-wrap gap-1.5">
          {coverageQuery.data?.gaps.map((gap) => (
            <span key={gap} className="rounded-md border border-dashed border-ink-600 px-2 py-0.5 text-[11px] text-ink-400">
              {gap}
            </span>
          ))}
          {coverageQuery.data?.gaps.length === 0 && (
            <span className="text-[11.5px] text-ink-300">Keine Lücken — vollständige Abdeckung</span>
          )}
        </div>
      </div>
    </div>
  )
}
