import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'

import { listTechniques } from '../lib/api'
import { TACTIC_NAMES } from '../lib/tactics'

const STATUS_BADGE = {
  specific: 'bg-prevent-dim text-prevent',
  mitre_derived: 'bg-portfolio-dim text-portfolio',
  tactic_default: 'bg-detect-dim text-detect',
} as const

const STATUS_LABEL = {
  specific: 'Spezifisch gemappt',
  mitre_derived: 'MITRE-Mitigation',
  tactic_default: 'Taktik-Standard',
} as const

export function Techniques() {
  const [tactic, setTactic] = useState('')
  const [status, setStatus] = useState('')
  const [q, setQ] = useState('')
  const [includeDeprecated, setIncludeDeprecated] = useState(false)

  const { data, isLoading } = useQuery({
    queryKey: ['techniques', tactic, status, q, includeDeprecated],
    queryFn: () =>
      listTechniques({
        tactic: tactic || undefined,
        status: status || undefined,
        q: q || undefined,
        includeDeprecated,
      }),
  })

  return (
    <div className="flex flex-col gap-7">
      <div>
        <h1 className="font-display text-[22px] font-semibold">Alle Techniken</h1>
        <p className="mt-1 max-w-2xl text-[13px] text-ink-400">
          Filterbare Referenztabelle des ATT&amp;CK-Katalogs.
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-2.5">
        <select
          className="rounded-md border border-line bg-graphite-850 px-3 py-2 text-sm text-ink-100 outline-none"
          value={tactic}
          onChange={(e) => setTactic(e.target.value)}
        >
          <option value="">Alle Taktiken</option>
          {TACTIC_NAMES.map((name) => (
            <option key={name} value={name}>
              {name}
            </option>
          ))}
        </select>
        <select
          className="rounded-md border border-line bg-graphite-850 px-3 py-2 text-sm text-ink-100 outline-none"
          value={status}
          onChange={(e) => setStatus(e.target.value)}
        >
          <option value="">Alle Status</option>
          <option value="specific">Spezifisch gemappt</option>
          <option value="mitre_derived">MITRE-Mitigation</option>
          <option value="tactic_default">Taktik-Standard</option>
        </select>
        <input
          className="min-w-56 flex-1 rounded-md border border-line bg-graphite-850 px-3 py-2 text-sm text-ink-100 outline-none placeholder:text-ink-600"
          placeholder="Suche nach ID oder Name …"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
        <label className="flex items-center gap-1.5 text-[12px] text-ink-400">
          <input
            type="checkbox"
            checked={includeDeprecated}
            onChange={(e) => setIncludeDeprecated(e.target.checked)}
          />
          Deprecated anzeigen
        </label>
        <span className="ml-auto text-[12px] text-ink-400">
          {isLoading ? 'Lade …' : `${data?.total ?? 0} Zeilen`}
        </span>
      </div>

      <div className="max-h-[560px] overflow-y-auto rounded-lg border border-line">
        <table className="w-full border-collapse">
          <thead className="sticky top-0 bg-graphite-900">
            <tr className="text-left text-[11px] font-semibold tracking-wide text-ink-600 uppercase">
              <th className="px-3 py-2.5">T-Nummer</th>
              <th className="px-3 py-2.5">Name</th>
              <th className="px-3 py-2.5">Taktik</th>
              <th className="px-3 py-2.5">Status</th>
            </tr>
          </thead>
          <tbody>
            {data?.techniques.map((t) => (
              <tr key={t.technique_id} className="border-t border-line-soft hover:bg-graphite-850">
                <td className="px-3 py-3 font-mono text-[12.5px] font-semibold text-amber">{t.technique_id}</td>
                <td className="px-3 py-3 text-[13px]">{t.technique_name}</td>
                <td className="px-3 py-3 text-[12.5px] text-ink-400">{t.tactic_name}</td>
                <td className="px-3 py-3">
                  <span className={`rounded-full px-2.5 py-0.5 text-[11px] font-semibold ${STATUS_BADGE[t.mapping_source]}`}>
                    {STATUS_LABEL[t.mapping_source]}
                  </span>
                  {t.deprecated && (
                    <span className="ml-1.5 rounded-full bg-graphite-800 px-2.5 py-0.5 text-[11px] font-semibold text-ink-500">
                      Deprecated
                    </span>
                  )}
                </td>
              </tr>
            ))}
            {data?.techniques.length === 0 && (
              <tr>
                <td colSpan={4} className="px-3 py-8 text-center text-[12.5px] text-ink-600">
                  Keine Techniken gefunden.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
