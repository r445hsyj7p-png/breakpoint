import type { PrioritizedMeasure } from '../../lib/api'
import { CATEGORY_CLASS, CATEGORY_LABEL } from './pillStyles'

export function PrioritizedMeasuresTable({ measures }: { measures: PrioritizedMeasure[] }) {
  if (measures.length === 0) return null

  return (
    <table className="w-full border-collapse">
      <thead>
        <tr className="text-left text-[11px] font-semibold tracking-wide text-ink-600 uppercase">
          <th className="w-9 pb-2.5">#</th>
          <th className="pb-2.5">Maßnahme</th>
          <th className="pb-2.5">Kategorie</th>
          <th className="pb-2.5">Kettenabdeckung</th>
          <th className="pb-2.5">Betroffene Techniken</th>
        </tr>
      </thead>
      <tbody>
        {measures.map((m) => (
          <tr key={m.control_id} className="border-t border-line-soft hover:bg-graphite-850">
            <td className="py-3 font-mono text-[12.5px] text-ink-600">{String(m.priority_rank).padStart(2, '0')}</td>
            <td className="py-3 text-[13px] font-semibold">{m.label}</td>
            <td className={`py-3 text-[12.5px] font-medium ${CATEGORY_CLASS[m.category]}`}>{CATEGORY_LABEL[m.category]}</td>
            <td className="py-3 font-mono text-[12.5px] text-ink-300">{m.chain_coverage_count}</td>
            <td className="py-3 font-mono text-[11.5px] text-ink-400">{m.affected_technique_ids.join(', ')}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
