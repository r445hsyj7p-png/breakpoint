export function Topbar() {
  return (
    <header className="sticky top-0 z-10 flex items-center justify-between border-b border-line bg-graphite-950 px-8 py-3.5">
      <button className="flex items-center gap-2.5 rounded-md border border-line bg-graphite-900 px-3 py-1.5 text-sm font-medium text-ink-100">
        <span className="h-1.5 w-1.5 flex-none rounded-full bg-amber" />
        Kein Engagement ausgewählt
      </button>
      <div className="flex items-center gap-3.5">
        <div className="flex h-[30px] w-[30px] items-center justify-center rounded-full border border-line bg-graphite-800 text-[11px] font-semibold text-ink-300">
          BP
        </div>
      </div>
    </header>
  )
}
