import { useQuery } from '@tanstack/react-query'

import { listEngagements } from '../lib/api'
import { useEngagement } from '../lib/EngagementContext'

export function Topbar() {
  const { engagementId, setEngagementId } = useEngagement()
  const { data: engagements } = useQuery({ queryKey: ['engagements'], queryFn: listEngagements })

  return (
    <header className="sticky top-0 z-10 flex items-center justify-between border-b border-line bg-graphite-950 px-8 py-3.5">
      <div className="flex items-center gap-2.5 rounded-md border border-line bg-graphite-900 px-3 py-1.5 text-sm font-medium text-ink-100">
        <span className="h-1.5 w-1.5 flex-none rounded-full bg-amber" />
        <select
          className="bg-transparent outline-none"
          value={engagementId ?? ''}
          onChange={(e) => setEngagementId(e.target.value ? Number(e.target.value) : null)}
        >
          <option value="">Kein Engagement ausgewählt</option>
          {engagements?.map((e) => (
            <option key={e.id} value={e.id}>
              {e.name}
            </option>
          ))}
        </select>
      </div>
      <div className="flex items-center gap-3.5">
        <div className="flex h-[30px] w-[30px] items-center justify-center rounded-full border border-line bg-graphite-800 text-[11px] font-semibold text-ink-300">
          BP
        </div>
      </div>
    </header>
  )
}
