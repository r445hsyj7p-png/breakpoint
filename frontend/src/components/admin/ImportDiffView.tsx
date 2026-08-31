import { useState } from 'react'

import type { ImportDiff } from '../../lib/api'

export function ImportDiffView({
  diff,
  onApply,
  isApplying,
}: {
  diff: ImportDiff
  onApply: (selection: { technique_ids: string[]; mitigation_technique_ids: string[] }) => void
  isApplying: boolean
}) {
  const techniqueCandidateIds = [
    ...diff.new_techniques.map((t) => t.technique_id),
    ...diff.updated_techniques.map((t) => t.technique_id),
    ...diff.newly_deprecated_techniques.map((t) => t.technique_id),
  ]
  const mitigationCandidateIds = diff.mitigation_candidates.map((c) => c.technique_id)

  const [selectedTechniques, setSelectedTechniques] = useState<Set<string>>(new Set(techniqueCandidateIds))
  const [selectedMitigations, setSelectedMitigations] = useState<Set<string>>(new Set(mitigationCandidateIds))

  function toggle(set: Set<string>, setter: (s: Set<string>) => void, id: string) {
    const next = new Set(set)
    if (next.has(id)) next.delete(id)
    else next.add(id)
    setter(next)
  }

  return (
    <div className="flex flex-col gap-5">
      {diff.bundle_version && (
        <div className="text-[11.5px] text-ink-500">ATT&amp;CK-Version im Bundle: {diff.bundle_version}</div>
      )}

      {diff.new_techniques.length > 0 && (
        <div>
          <div className="mb-2 text-[12.5px] font-semibold text-prevent">
            Neue Techniken ({diff.new_techniques.length})
          </div>
          <div className="flex flex-col gap-1.5">
            {diff.new_techniques.map((t) => (
              <label key={t.technique_id} className="flex items-center gap-2.5 rounded-md border border-line-soft bg-graphite-850 px-3 py-2 text-[12.5px]">
                <input
                  type="checkbox"
                  checked={selectedTechniques.has(t.technique_id)}
                  onChange={() => toggle(selectedTechniques, setSelectedTechniques, t.technique_id)}
                />
                <span className="font-mono text-ink-500">{t.technique_id}</span>
                <span className="text-ink-200">{t.name}</span>
                <span className="ml-auto text-[11px] text-ink-600">{t.tactic_id}</span>
              </label>
            ))}
          </div>
        </div>
      )}

      {diff.updated_techniques.length > 0 && (
        <div>
          <div className="mb-2 text-[12.5px] font-semibold text-detect">
            Geänderte Techniken ({diff.updated_techniques.length})
          </div>
          <div className="flex flex-col gap-1.5">
            {diff.updated_techniques.map((t) => (
              <label key={t.technique_id} className="flex flex-col gap-1 rounded-md border border-line-soft bg-graphite-850 px-3 py-2 text-[12.5px]">
                <div className="flex items-center gap-2.5">
                  <input
                    type="checkbox"
                    checked={selectedTechniques.has(t.technique_id)}
                    onChange={() => toggle(selectedTechniques, setSelectedTechniques, t.technique_id)}
                  />
                  <span className="font-mono text-ink-500">{t.technique_id}</span>
                </div>
                <div className="ml-6 flex flex-col gap-0.5 text-[11.5px] text-ink-400">
                  {Object.entries(t.changes).map(([field, change]) => (
                    <div key={field}>
                      <span className="text-ink-600">{field}:</span> {change.old ?? '—'} → {change.new ?? '—'}
                    </div>
                  ))}
                </div>
              </label>
            ))}
          </div>
        </div>
      )}

      {diff.newly_deprecated_techniques.length > 0 && (
        <div>
          <div className="mb-2 text-[12.5px] font-semibold text-ember">
            Als deprecated markiert ({diff.newly_deprecated_techniques.length})
          </div>
          <div className="flex flex-col gap-1.5">
            {diff.newly_deprecated_techniques.map((t) => (
              <label key={t.technique_id} className="flex items-center gap-2.5 rounded-md border border-line-soft bg-graphite-850 px-3 py-2 text-[12.5px]">
                <input
                  type="checkbox"
                  checked={selectedTechniques.has(t.technique_id)}
                  onChange={() => toggle(selectedTechniques, setSelectedTechniques, t.technique_id)}
                />
                <span className="font-mono text-ink-500">{t.technique_id}</span>
                <span className="text-ink-200">{t.name}</span>
              </label>
            ))}
          </div>
        </div>
      )}

      {diff.mitigation_candidates.length > 0 && (
        <div>
          <div className="mb-2 text-[12.5px] font-semibold text-portfolio">
            Mitigation-Kandidaten ({diff.mitigation_candidates.length})
          </div>
          <div className="flex flex-col gap-1.5">
            {diff.mitigation_candidates.map((c) => (
              <label key={c.technique_id} className="flex flex-col gap-1.5 rounded-md border border-line-soft bg-graphite-850 px-3 py-2.5 text-[12.5px]">
                <div className="flex items-center gap-2.5">
                  <input
                    type="checkbox"
                    checked={selectedMitigations.has(c.technique_id)}
                    onChange={() => toggle(selectedMitigations, setSelectedMitigations, c.technique_id)}
                  />
                  <span className="font-mono text-ink-500">{c.technique_id}</span>
                  <span className="ml-auto text-[11px] text-ink-600">
                    {c.impact} / {c.effort}
                  </span>
                </div>
                <div className="ml-6 flex flex-wrap gap-1.5">
                  {c.control_labels.map((label) => (
                    <span key={label} className="rounded-md border border-portfolio/35 bg-portfolio-dim px-2 py-0.5 text-[11px] font-semibold text-portfolio">
                      {label}
                    </span>
                  ))}
                </div>
                <div className="ml-6 text-[11px] text-ink-600">
                  aus: {c.mitigations.map((m) => `${m.m_id} ${m.mitigation_name}`).join(', ')}
                </div>
              </label>
            ))}
          </div>
        </div>
      )}

      {diff.conflicts.length > 0 && (
        <div>
          <div className="mb-2 text-[12.5px] font-semibold text-ink-400">
            Konflikte — nicht übernehmbar ({diff.conflicts.length})
          </div>
          <div className="flex flex-col gap-1.5">
            {diff.conflicts.map((c) => (
              <div key={c.technique_id} className="rounded-md border border-line-soft bg-graphite-850 px-3 py-2 text-[11.5px] text-ink-500">
                <span className="font-mono">{c.technique_id}</span> — {c.reason}
              </div>
            ))}
          </div>
        </div>
      )}

      {diff.skipped_mitigations_without_crosswalk.length > 0 && (
        <div>
          <div className="mb-2 text-[12.5px] font-semibold text-ink-400">
            Mitigations ohne Capability-Zuordnung ({diff.skipped_mitigations_without_crosswalk.length})
          </div>
          <div className="flex flex-wrap gap-1.5">
            {diff.skipped_mitigations_without_crosswalk.map((m) => (
              <span key={m.m_id} className="rounded-md border border-dashed border-ink-600 px-2 py-0.5 text-[11px] text-ink-500">
                {m.m_id} {m.mitigation_name}
              </span>
            ))}
          </div>
        </div>
      )}

      {diff.unmapped_tactic_phase_techniques.length > 0 && (
        <div>
          <div className="mb-2 text-[12.5px] font-semibold text-ink-400">
            Techniken mit unbekannter Taktik-Phase ({diff.unmapped_tactic_phase_techniques.length})
          </div>
          <div className="flex flex-col gap-1">
            {diff.unmapped_tactic_phase_techniques.map((t) => (
              <div key={t.technique_id} className="text-[11.5px] text-ink-500">
                <span className="font-mono">{t.technique_id}</span> {t.name} — Phasen: {t.phase_names.join(', ')}
              </div>
            ))}
          </div>
        </div>
      )}

      <button
        className="w-fit rounded-md bg-amber px-4 py-2 text-sm font-semibold text-[#241a08] hover:bg-[#f0b355] disabled:opacity-50"
        disabled={isApplying}
        onClick={() =>
          onApply({
            technique_ids: [...selectedTechniques],
            mitigation_technique_ids: [...selectedMitigations],
          })
        }
      >
        Auswahl übernehmen
      </button>
    </div>
  )
}
