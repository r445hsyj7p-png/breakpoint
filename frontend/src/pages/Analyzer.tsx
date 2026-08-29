import { useMutation } from '@tanstack/react-query'
import { useState } from 'react'

import { AnalyzerResultView } from '../components/analyzer/AnalyzerResultView'
import { analyze } from '../lib/api'

const EXAMPLE_CHAIN = 'T1566.001\nT1078\nT1021.001\nT1059.001'

export function Analyzer() {
  const [codes, setCodes] = useState('')
  const mutation = useMutation({ mutationFn: analyze })

  return (
    <div className="flex flex-col gap-7">
      <div>
        <h1 className="font-display text-[22px] font-semibold">ATT&amp;CK Analyzer</h1>
        <p className="mt-1 max-w-2xl text-[13px] text-ink-400">
          T-Nummern eingeben (Freitext, Komma- oder zeilengetrennt) und analysieren.
        </p>
      </div>

      <div className="flex flex-wrap items-start gap-3">
        <textarea
          className="min-h-[112px] flex-1 basis-90 resize-y rounded-md border border-line bg-graphite-850 p-3.5 font-mono text-[13px] leading-relaxed text-ink-100 outline-none placeholder:text-ink-600"
          placeholder="T1566.001, T1078, T1021.001 …"
          value={codes}
          onChange={(e) => setCodes(e.target.value)}
        />
        <div className="flex min-w-42 flex-col gap-2">
          <button
            className="flex items-center justify-center gap-2 rounded-md bg-amber px-4 py-2.5 text-sm font-semibold text-[#241a08] hover:bg-[#f0b355] disabled:opacity-50"
            onClick={() => mutation.mutate(codes)}
            disabled={mutation.isPending}
          >
            {mutation.isPending ? 'Analysiere …' : 'Analysieren'}
          </button>
          <button
            className="rounded-md border border-line bg-graphite-850 px-4 py-2.5 text-sm font-semibold text-ink-300 hover:bg-graphite-800 hover:text-ink-100"
            onClick={() => setCodes(EXAMPLE_CHAIN)}
          >
            Beispielkette laden
          </button>
        </div>
      </div>

      {mutation.isError && (
        <div className="rounded-md border border-ember/35 bg-ember-dim px-4 py-3 text-[12.5px] text-ink-100">
          Analyse fehlgeschlagen: {(mutation.error as Error).message}
        </div>
      )}

      {mutation.isSuccess && mutation.data.input_codes.length === 0 && (
        <div className="rounded-lg border border-line bg-graphite-900 p-10 text-center text-[12.5px] text-ink-600">
          Noch keine Analyse — T-Nummern oben eingeben und auf „Analysieren“ klicken.
        </div>
      )}

      {mutation.isSuccess && mutation.data.input_codes.length > 0 && (
        <AnalyzerResultView result={mutation.data} />
      )}
    </div>
  )
}
