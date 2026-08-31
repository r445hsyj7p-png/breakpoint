import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'

import { server } from '../test/mswServer'
import { renderWithProviders } from '../test/testUtils'
import { Engagements } from './Engagements'

describe('Engagements', () => {
  it('deaktiviert den Anlegen-Button bei leerem Namen (analog zum Backend-422)', async () => {
    server.use(
      http.get('http://127.0.0.1:8000/api/engagements', () => HttpResponse.json([])),
    )

    renderWithProviders(<Engagements />)

    const submitButton = screen.getByRole('button', { name: 'Anlegen' })
    expect(submitButton).toBeDisabled()

    const user = userEvent.setup()
    await user.type(screen.getByPlaceholderText(/Red Team Assessment/), 'Neues Engagement')
    expect(submitButton).toBeEnabled()

    await user.clear(screen.getByPlaceholderText(/Red Team Assessment/))
    expect(submitButton).toBeDisabled()
  })

  it('listet bestehende Engagements auf', async () => {
    server.use(
      http.get('http://127.0.0.1:8000/api/engagements', () =>
        HttpResponse.json([{ id: 1, name: 'Red Team Assessment 2026', external_ref: null, status: 'offen' }]),
      ),
    )

    renderWithProviders(<Engagements />)

    await waitFor(() => expect(screen.getByText('Red Team Assessment 2026')).toBeInTheDocument())
  })

  it('zeigt "kein Sales-Briefing" für ein ausgewähltes Engagement ohne Briefing', async () => {
    server.use(
      http.get('http://127.0.0.1:8000/api/engagements', () =>
        HttpResponse.json([{ id: 1, name: 'Red Team Assessment 2026', external_ref: null, status: 'offen' }]),
      ),
      http.get('http://127.0.0.1:8000/api/engagements/1/analysis', () =>
        HttpResponse.json({ input_codes: [], techniques: [], unknown_codes: [], prioritized_measures: [] }),
      ),
      http.get('http://127.0.0.1:8000/api/engagements/1/sales-briefing', () =>
        HttpResponse.json({ detail: 'Noch kein Sales-Briefing für dieses Engagement' }, { status: 404 }),
      ),
    )

    renderWithProviders(<Engagements />)
    const user = userEvent.setup()
    await user.click(await screen.findByText('Red Team Assessment 2026'))

    await waitFor(() =>
      expect(screen.getByText('Noch kein Sales-Briefing generiert.')).toBeInTheDocument(),
    )
  })

  it('zeigt den Übergang von "kein Briefing" zu "ready" nach dem Generieren, ohne manuelles Neuladen', async () => {
    let hasBriefing = false
    server.use(
      http.get('http://127.0.0.1:8000/api/engagements', () =>
        HttpResponse.json([{ id: 1, name: 'Red Team Assessment 2026', external_ref: null, status: 'offen' }]),
      ),
      http.get('http://127.0.0.1:8000/api/engagements/1/analysis', () =>
        HttpResponse.json({ input_codes: [], techniques: [], unknown_codes: [], prioritized_measures: [] }),
      ),
      http.post('http://127.0.0.1:8000/api/engagements/1/sales-briefing', () => {
        hasBriefing = true
        return HttpResponse.json(
          { id: 1, engagement_id: 1, status: 'pending', model_version: null, content: null, error_message: null, created_at: '2026-01-01T00:00:00Z', generated_at: null, reviewed_by: null, reviewed_at: null },
          { status: 202 },
        )
      }),
      http.get('http://127.0.0.1:8000/api/engagements/1/sales-briefing', () => {
        if (!hasBriefing) {
          return HttpResponse.json({ detail: 'Noch kein Sales-Briefing für dieses Engagement' }, { status: 404 })
        }
        return HttpResponse.json({
          id: 1,
          engagement_id: 1,
          status: 'ready',
          model_version: 'gpt-4o-mini',
          content: {
            executive_summary: 'Zusammenfassung',
            top_massnahmen: [],
            naechster_schritt: 'Workshop planen',
          },
          error_message: null,
          created_at: '2026-01-01T00:00:00Z',
          generated_at: '2026-01-01T00:01:00Z',
          reviewed_by: null,
          reviewed_at: null,
        })
      }),
    )

    renderWithProviders(<Engagements />)
    const user = userEvent.setup()
    await user.click(await screen.findByText('Red Team Assessment 2026'))
    await waitFor(() => expect(screen.getByText('Noch kein Sales-Briefing generiert.')).toBeInTheDocument())

    await user.click(screen.getByRole('button', { name: 'Sales-Briefing generieren' }))

    await waitFor(() => expect(screen.getByText('Zusammenfassung')).toBeInTheDocument())
  })
})
