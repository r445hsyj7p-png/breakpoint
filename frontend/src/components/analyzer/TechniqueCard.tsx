import type { TechniqueResult } from '../../lib/api'
import { CATEGORY_CLASS, CATEGORY_LABEL, EFFORT_CLASS, EFFORT_LABEL, IMPACT_CLASS, IMPACT_LABEL } from './pillStyles'

export function TechniqueCard({ technique }: { technique: TechniqueResult }) {
  const byCategory = {
    prevent: technique.controls.filter((c) => c.category === 'prevent'),
    detect: technique.controls.filter((c) => c.category === 'detect'),
    respond: technique.controls.filter((c) => c.category === 'respond'),
  }

  return (
    <div className="flex flex-col gap-2.5 rounded-md border border-line bg-graphite-850 p-4">
      <div className="flex items-center justify-between gap-2.5">
        <div>
          <div className="font-mono text-[12.5px] font-semibold text-amber">{technique.technique_id}</div>
          <div className="mt-0.5 text-[13px] font-semibold">{technique.technique_name}</div>
          <div className="text-[11px] text-ink-400">{technique.tactic_name}</div>
        </div>
        <span className={`rounded-full px-2.5 py-0.5 text-[11px] font-semibold whitespace-nowrap ${IMPACT_CLASS[technique.impact]}`}>
          {IMPACT_LABEL[technique.impact]}
        </span>
      </div>

      <span
        className={`inline-flex w-fit items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[11px] font-semibold ${
          technique.mapping_source === 'specific' ? 'bg-prevent-dim text-prevent' : 'bg-detect-dim text-detect'
        }`}
      >
        {technique.mapping_source === 'specific'
          ? technique.resolved_via_technique_id === technique.technique_id
            ? 'Spezifisches Mapping'
            : `Spezifisch (via ${technique.resolved_via_technique_id})`
          : 'Taktik-Standard'}
      </span>

      <div className="text-[11px] font-semibold tracking-wide text-ink-600 uppercase">Capabilities</div>
      <div className="flex flex-wrap gap-1.5">
        {technique.capabilities.map((c) => (
          <span key={c} className="rounded-md border border-line-soft bg-graphite-800 px-2 py-0.5 text-[11px] text-ink-300">
            {c}
          </span>
        ))}
      </div>

      <div className="text-[11px] font-semibold tracking-wide text-ink-600 uppercase">Portfolio-Fit</div>
      <div className="flex flex-wrap gap-1.5">
        {technique.portfolio_fit.length > 0 ? (
          technique.portfolio_fit.map((name) => (
            <span
              key={name}
              className="rounded-md border border-portfolio/35 bg-portfolio-dim px-2 py-0.5 text-[11px] font-semibold text-portfolio"
            >
              {name}
            </span>
          ))
        ) : (
          <span className="text-[11px] text-ink-600">Kein Portfolio-Fit</span>
        )}
      </div>

      <ul className="flex flex-col gap-1.5 text-[12.5px] text-ink-300">
        {(['prevent', 'detect', 'respond'] as const).map((category) =>
          byCategory[category].length ? (
            <li key={category} className="rounded-sm border border-line-soft bg-graphite-900 px-2.5 py-2">
              <strong className={CATEGORY_CLASS[category]}>{CATEGORY_LABEL[category]} — </strong>
              {byCategory[category].map((c) => c.label).join(', ')}
            </li>
          ) : null,
        )}
      </ul>

      <span className={`w-fit rounded-full px-2 py-0.5 text-[10.5px] font-semibold ${EFFORT_CLASS[technique.effort]}`}>
        Aufwand: {EFFORT_LABEL[technique.effort]}
      </span>
    </div>
  )
}
