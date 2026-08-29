import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'

import { server } from '../test/mswServer'
import { renderWithProviders } from '../test/testUtils'
import { Analyzer } from './Analyzer'

const SAMPLE_RESULT = {
  input_codes: ['T1078'],
  techniques: [
    {
      technique_id: 'T1078',
      technique_name: 'Valid Accounts',
      tactic_name: 'Initial Access',
      mapping_source: 'specific',
      resolved_via_technique_id: 'T1078',
      impact: 'sehr_hoch',
      effort: 'mittel',
      capabilities: ['MFA'],
      controls: [{ id: 1, category: 'prevent', label: 'MFA erzwingen' }],
      portfolio_fit: [],
    },
  ],
  unknown_codes: [],
  prioritized_measures: [
    {
      control_id: 1,
      category: 'prevent',
      label: 'MFA erzwingen',
      priority_rank: 1,
      chain_coverage_count: 1,
      affected_technique_ids: ['T1078'],
    },
  ],
}

describe('Analyzer', () => {
  it('sendet die eingegebenen Codes und zeigt das Analyseergebnis', async () => {
    server.use(
      http.post('http://127.0.0.1:8000/api/analyze', async ({ request }) => {
        const body = (await request.json()) as { codes: string }
        expect(body.codes).toBe('T1078')
        return HttpResponse.json(SAMPLE_RESULT)
      }),
    )

    renderWithProviders(<Analyzer />)
    const user = userEvent.setup()

    await user.type(screen.getByPlaceholderText(/T1566.001/), 'T1078')
    await user.click(screen.getByRole('button', { name: 'Analysieren' }))

    await waitFor(() => expect(screen.getByText('Valid Accounts')).toBeInTheDocument())
    expect(screen.getByText('Priorisierte Maßnahmen')).toBeInTheDocument()
  })

  it('zeigt eine Fehlermeldung, wenn die Analyse fehlschlägt', async () => {
    server.use(
      http.post('http://127.0.0.1:8000/api/analyze', () =>
        HttpResponse.text('Internal Server Error', { status: 500 }),
      ),
    )

    renderWithProviders(<Analyzer />)
    const user = userEvent.setup()

    await user.type(screen.getByPlaceholderText(/T1566.001/), 'T1078')
    await user.click(screen.getByRole('button', { name: 'Analysieren' }))

    await waitFor(() => expect(screen.getByText(/Analyse fehlgeschlagen/)).toBeInTheDocument())
  })
})
