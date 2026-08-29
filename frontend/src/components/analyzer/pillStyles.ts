import type { AnalyzerResult } from '../../lib/api'

type Impact = AnalyzerResult['techniques'][number]['impact']
type Effort = AnalyzerResult['techniques'][number]['effort']

export const IMPACT_LABEL: Record<Impact, string> = {
  niedrig: 'Niedrig',
  mittel: 'Mittel',
  hoch: 'Hoch',
  sehr_hoch: 'Sehr hoch',
}

export const EFFORT_LABEL: Record<Effort, string> = {
  niedrig: 'Niedrig',
  mittel: 'Mittel',
  hoch: 'Hoch',
}

export const IMPACT_CLASS: Record<Impact, string> = {
  sehr_hoch: 'bg-ember-dim text-ember',
  hoch: 'bg-amber-dim text-amber',
  mittel: 'bg-detect-dim text-detect',
  niedrig: 'bg-prevent-dim text-prevent',
}

export const EFFORT_CLASS: Record<Effort, string> = {
  niedrig: 'bg-prevent-dim text-prevent',
  mittel: 'bg-graphite-800 text-ink-300',
  hoch: 'bg-ember-dim text-ember',
}

export const CATEGORY_LABEL = { prevent: 'Prevent', detect: 'Detect', respond: 'Respond' } as const

export const CATEGORY_CLASS = {
  prevent: 'text-prevent',
  detect: 'text-detect',
  respond: 'text-respond',
} as const
