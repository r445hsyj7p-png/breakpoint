import type { AnalyzerResult } from '../../lib/api'
import { PrioritizedMeasuresTable } from './PrioritizedMeasuresTable'
import { TechniqueCard } from './TechniqueCard'

export function AnalyzerResultView({ result }: { result: AnalyzerResult }) {
  const specificCount = result.techniques.filter((t) => t.mapping_source === 'specific').length
  const tacticDefaultCount = result.techniques.length - specificCount

  return (
    <div className="flex flex-col gap-7">
      <div className="grid grid-cols-3 gap-px overflow-hidden rounded-lg border border-line bg-line">
        <div className="bg-graphite-900 px-5 py-4.5">
          <div className="font-display text-[26px] font-semibold">{result.input_codes.length}</div>
          <div className="mt-1 text-xs text-ink-400">Eingegebene Techniken</div>
        </div>
        <div className="bg-graphite-900 px-5 py-4.5">
          <div className="font-display text-[26px] font-semibold">{specificCount}</div>
          <div className="mt-1 text-xs text-ink-400">Spezifisch gemappt</div>
        </div>
        <div className="bg-graphite-900 px-5 py-4.5">
          <div className="font-display text-[26px] font-semibold">{tacticDefaultCount}</div>
          <div className="mt-1 text-xs text-ink-400">Taktik-Standard</div>
        </div>
      </div>

      {result.unknown_codes.length > 0 && (
        <div className="rounded-md border border-ember/35 bg-ember-dim px-4 py-3 text-[12.5px] text-ink-100">
          <strong className="text-ember">Nicht erkannt:</strong>{' '}
          {result.unknown_codes.join(', ')} — bitte T-Nummern auf Tippfehler prüfen.
        </div>
      )}

      {result.techniques.length > 0 && (
        <div className="rounded-lg border border-line bg-graphite-900 p-6">
          <div className="mb-4 text-[15px] font-semibold">Technik-Details</div>
          <div className="grid grid-cols-[repeat(auto-fill,minmax(320px,1fr))] gap-3.5">
            {result.techniques.map((t) => (
              <TechniqueCard key={t.technique_id} technique={t} />
            ))}
          </div>
        </div>
      )}

      {result.prioritized_measures.length > 0 && (
        <div className="rounded-lg border border-line bg-graphite-900 p-6">
          <div className="mb-1 text-[15px] font-semibold">Priorisierte Maßnahmen</div>
          <div className="mb-4 text-xs text-ink-400">Sortiert nach Kettenabdeckung, dann Impact, dann Aufwand</div>
          <PrioritizedMeasuresTable measures={result.prioritized_measures} />
        </div>
      )}
    </div>
  )
}
