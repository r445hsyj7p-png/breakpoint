const stats = [
  { label: 'ATT&CK Techniques', value: '—' },
  { label: 'Sub-Techniques', value: '—' },
  { label: 'Angriffsketten', value: '—' },
  { label: 'Priorisierte Maßnahmen', value: '—' },
]

export function Dashboard() {
  return (
    <div className="flex flex-col gap-7">
      <div>
        <div className="mb-2 text-[11px] font-semibold tracking-wider text-amber uppercase">
          Kein aktives Engagement
        </div>
        <h1 className="font-display text-[27px] font-semibold tracking-tight">Dashboard</h1>
        <p className="mt-3 max-w-2xl text-[14px] leading-relaxed text-ink-300">
          Sobald ein Engagement angelegt und Techniken importiert wurden, erscheinen hier
          Coverage, Angriffskette und priorisierte Maßnahmen. In Schritt 1 ist dies noch eine
          statische Ansicht ohne Backend-Anbindung.
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
          Wird in Schritt 2 aus echten Engagement-Findings berechnet.
        </div>
      </div>
    </div>
  )
}
