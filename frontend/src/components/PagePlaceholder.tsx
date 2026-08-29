export function PagePlaceholder({ title, description }: { title: string; description: string }) {
  return (
    <div>
      <h1 className="font-display text-[22px] font-semibold">{title}</h1>
      <p className="mt-1 max-w-2xl text-[13px] text-ink-400">{description}</p>
      <div className="mt-6 rounded-lg border border-dashed border-line bg-graphite-900 p-10 text-center text-[12.5px] text-ink-600">
        Wird in einem späteren Schritt an das Backend angebunden (siehe
        docs/projektauftrag.md, Abschnitt 11).
      </div>
    </div>
  )
}
