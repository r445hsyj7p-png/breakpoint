import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'

import { server } from '../../test/mswServer'
import { renderWithProviders } from '../../test/testUtils'
import { MitreImport } from './MitreImport'

const DIFF_SNAPSHOT = {
  bundle_version: '17.0',
  new_techniques: [
    { technique_id: 'T9001', name: 'Synthetic New Technique', tactic_id: 'persistence', parent_technique_id: null, stix_id: 'attack-pattern--x' },
  ],
  updated_techniques: [],
  newly_deprecated_techniques: [],
  unmapped_tactic_phase_techniques: [],
  mitigation_candidates: [
    {
      technique_id: 'T9001',
      mitigations: [{ m_id: 'M1032', mitigation_name: 'Multi-factor Authentication', control_label: 'MFA erzwingen' }],
      capabilities: ['MFA'],
      control_labels: ['MFA erzwingen'],
      impact: 'mittel',
      effort: 'niedrig',
    },
  ],
  skipped_mitigations_without_crosswalk: [],
  conflicts: [],
}

function makeBatch(overrides: Partial<Record<string, unknown>> = {}) {
  return {
    id: 1,
    source: 'manual_upload',
    source_ref: 'test.json',
    bundle_version: null as string | null,
    status: 'diff_pending',
    triggered_by: null as string | null,
    diff_snapshot: null as typeof DIFF_SNAPSHOT | null,
    error_message: null as string | null,
    created_at: '2026-01-01T00:00:00Z',
    applied_at: null as string | null,
    rolled_back_at: null as string | null,
    ...overrides,
  }
}

describe('MitreImport', () => {
  it('lädt einen Bundle-Upload hoch und zeigt danach den berechneten Diff', async () => {
    let batches: ReturnType<typeof makeBatch>[] = []
    let uploadedBatch = makeBatch()

    server.use(
      http.get('http://127.0.0.1:8000/api/admin/mitre-import/batches', () => HttpResponse.json(batches)),
      http.post('http://127.0.0.1:8000/api/admin/mitre-import/upload', () => {
        uploadedBatch = makeBatch({
          status: 'diff_ready',
          diff_snapshot: DIFF_SNAPSHOT,
          bundle_version: '17.0',
        })
        batches = [uploadedBatch]
        return HttpResponse.json(makeBatch({ status: 'diff_pending' }), { status: 202 })
      }),
      http.get('http://127.0.0.1:8000/api/admin/mitre-import/batches/1', () => HttpResponse.json(uploadedBatch)),
    )

    renderWithProviders(<MitreImport />)

    const file = new File(['{}'], 'sample.json', { type: 'application/json' })
    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    const user = userEvent.setup()
    await user.upload(input, file)

    await waitFor(() => expect(screen.getByText('Synthetic New Technique')).toBeInTheDocument())
    expect(screen.getByText('MFA erzwingen')).toBeInTheDocument()
  })

  it('übernimmt eine ausgewählte Diff-Auswahl und aktualisiert den Batch-Status', async () => {
    let batches: ReturnType<typeof makeBatch>[] = []
    let currentBatch = makeBatch({ status: 'diff_ready', diff_snapshot: DIFF_SNAPSHOT, bundle_version: '17.0' })

    server.use(
      http.get('http://127.0.0.1:8000/api/admin/mitre-import/batches', () => HttpResponse.json(batches)),
      http.post('http://127.0.0.1:8000/api/admin/mitre-import/upload', () => {
        batches = [currentBatch]
        return HttpResponse.json(currentBatch, { status: 202 })
      }),
      http.get('http://127.0.0.1:8000/api/admin/mitre-import/batches/1', () => HttpResponse.json(currentBatch)),
      http.post('http://127.0.0.1:8000/api/admin/mitre-import/batches/1/apply', () => {
        currentBatch = { ...currentBatch, status: 'applied', applied_at: '2026-01-01T01:00:00Z' }
        batches = [currentBatch]
        return HttpResponse.json(currentBatch)
      }),
    )

    renderWithProviders(<MitreImport />)

    const file = new File(['{}'], 'sample.json', { type: 'application/json' })
    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    const user = userEvent.setup()
    await user.upload(input, file)

    await waitFor(() => expect(screen.getByText('Synthetic New Technique')).toBeInTheDocument())
    await user.click(screen.getByRole('button', { name: 'Auswahl übernehmen' }))

    await waitFor(() => expect(screen.getByText('Übernommen')).toBeInTheDocument())
  })
})
