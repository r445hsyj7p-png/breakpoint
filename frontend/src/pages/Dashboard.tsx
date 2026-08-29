import { useQuery } from '@tanstack/react-query'

import { getEngagementAnalysis, listEngagements } from '../lib/api'
import { useEngagement } from '../lib/EngagementContext'

export function Dashboard() {
  const { engagementId } = useEngagement()

  const { data: engagements } = useQuery({ queryKey: ['engagements'], queryFn: listEngagements })
  const { data: analysis } = useQuery({
    queryKey: ['engagement-analysis', engagementId],
    queryFn: () => getEngagementAnalysis(engagementId!),
    enabled: engagementId !== null,
  })

  const engagement = engagements?.find((e) => e.id === engagementId)

  const subTechniqueCount = analysis?.techniques.filter((t) => t.technique_id.includes('.')).length ?? 0

  const stats = [
    { label: 'ATT&CK Techniques', value: analysis ? String(analysis.techniques.length) : '—' },
    { label: 'Sub-Techniques', value: analysis ? String(subTechniqueCount) : '—' },
    // Angriffsketten-Erkennung ist Teil der Visualisierungs-Komponente (Abschnitt 6,
    // Modul 5) und noch nicht gebaut — kein erfundener Wert, bewusst weiterhin "—".
    { label: 'Angriffsketten', value: '—' },
    {
      label: 'Priorisierte Maßnahmen',
      value: analysis ? String(analysis.prioritized_measures.length) : '—',
    },
  ]

  return (
    <div className="flex flex-col gap-7">
      <div>
        <div className="mb-2 text-[11px] font-semibold tracking-wider text-amber uppercase">
          {engagement ? `Engagement · ${engagement.name}` : 'Kein aktives Engagement'}
        </div>
        <h1 className="font-display text-[27px] font-semibold tracking-tight">Dashboard</h1>
        <p className="mt-3 max-w-2xl text-[14px] leading-relaxed text-ink-300">
          {engagement
            ? 'Kennzahlen aus der aktuellen Analyse des gewählten Engagements.'
            : 'Wähle oben in der Kopfzeile ein Engagement aus, um Kennzahlen aus dessen Analyse zu sehen.'}
        </p>

        <div className="mt-5 grid grid-cols-4 gap-px overflow-hidden rounded-lg border border-line bg-line">
          {stats.map((s) => (
            <div key={s.label} className="bg-graphite-900 px-5 py-4.5">
              <div className="font-display text-[26px] font-semibold">{s.value}</div>
              <div className="mt-1 text-xs text-ink-400">{s.label}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="rounded-lg border border-line bg-graphite-900 p-6">
        <div className="mb-4 text-[15px] font-semibold">ATT&amp;CK Coverage</div>
        <div className="text-[12.5px] text-ink-600">
          Wird in einem späteren Schritt aus Engagement-Findings je Taktik berechnet.
        </div>
      </div>
    </div>
  )
}
