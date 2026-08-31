import type { CapabilityRead } from '../../lib/api'

export function CapabilityCheckboxList({
  capabilities,
  selectedIds,
  onChange,
}: {
  capabilities: CapabilityRead[]
  selectedIds: Set<number>
  onChange: (next: Set<number>) => void
}) {
  return (
    <div className="grid grid-cols-2 gap-x-4 gap-y-1.5 sm:grid-cols-3">
      {capabilities.map((c) => (
        <label key={c.id} className="flex items-center gap-2 text-[12.5px] text-ink-300">
          <input
            type="checkbox"
            checked={selectedIds.has(c.id)}
            onChange={(e) => {
              const next = new Set(selectedIds)
              if (e.target.checked) next.add(c.id)
              else next.delete(c.id)
              onChange(next)
            }}
          />
          {c.name}
        </label>
      ))}
    </div>
  )
}
