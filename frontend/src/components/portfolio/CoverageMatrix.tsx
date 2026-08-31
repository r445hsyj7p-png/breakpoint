import type { CoverageResult } from '../../lib/api'

export function CoverageMatrix({ coverage, technologyNames }: { coverage: CoverageResult; technologyNames: string[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[600px] border-collapse">
        <thead>
          <tr>
            <th className="sticky left-0 border-b border-line bg-graphite-900 px-3 py-2 text-left text-[10.5px] font-semibold tracking-wide text-ink-400 uppercase">
              Capability
            </th>
            {technologyNames.map((name) => (
              <th
                key={name}
                className="border-b border-line px-3 py-2 text-center text-[10.5px] font-semibold tracking-wide whitespace-nowrap text-ink-400 uppercase"
              >
                {name}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {coverage.rows.map((row) => (
            <tr key={row.capability} className="border-t border-line-soft">
              <td className="sticky left-0 bg-graphite-900 px-3 py-2 text-[11.5px] text-ink-300">{row.capability}</td>
              {technologyNames.map((name) => (
                <td key={name} className="px-3 py-2 text-center text-[12px]">
                  {row.covering_technologies.includes(name) ? (
                    <span className="text-portfolio">●</span>
                  ) : (
                    <span className="text-ink-600">–</span>
                  )}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
