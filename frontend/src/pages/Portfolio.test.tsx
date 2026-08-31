import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'

import { server } from '../test/mswServer'
import { renderWithProviders } from '../test/testUtils'
import { Portfolio } from './Portfolio'

const CAPABILITIES = [
  { id: 1, name: 'MFA' },
  { id: 2, name: 'EDR' },
]

function mockBaseEndpoints(overrides?: { technologies?: unknown[]; coverage?: unknown }) {
  server.use(
    http.get('http://127.0.0.1:8000/api/portfolio/technologies', () =>
      HttpResponse.json(overrides?.technologies ?? []),
    ),
    http.get('http://127.0.0.1:8000/api/capabilities', () => HttpResponse.json(CAPABILITIES)),
    http.get('http://127.0.0.1:8000/api/portfolio/coverage', () =>
      HttpResponse.json(
        overrides?.coverage ?? {
          rows: [
            { capability: 'MFA', covering_technologies: [] },
            { capability: 'EDR', covering_technologies: [] },
          ],
          gaps: ['MFA', 'EDR'],
        },
      ),
    ),
  )
}

describe('Portfolio', () => {
  it('deaktiviert den Anlegen-Button, bis Name und Typ ausgefüllt sind', async () => {
    mockBaseEndpoints()
    renderWithProviders(<Portfolio />)

    await waitFor(() => expect(screen.getAllByText('MFA').length).toBeGreaterThan(0))

    const submitButton = screen.getByRole('button', { name: 'Anlegen' })
    expect(submitButton).toBeDisabled()

    const user = userEvent.setup()
    await user.type(screen.getByPlaceholderText('Name, z. B. Okta'), 'Okta')
    expect(submitButton).toBeDisabled()

    await user.type(screen.getByPlaceholderText('Typ, z. B. Identity'), 'Identity')
    expect(submitButton).toBeEnabled()
  })

  it('zeigt die Coverage-Matrix und das Gap-Panel', async () => {
    mockBaseEndpoints({
      technologies: [{ id: 1, name: 'Okta', type: 'Identity', active: true, capabilities: ['MFA'] }],
      coverage: {
        rows: [
          { capability: 'MFA', covering_technologies: ['Okta'] },
          { capability: 'EDR', covering_technologies: [] },
        ],
        gaps: ['EDR'],
      },
    })

    renderWithProviders(<Portfolio />)

    await waitFor(() => expect(screen.getAllByText('Okta').length).toBeGreaterThan(0))
    // "Okta" erscheint als Spaltenkopf der Coverage-Matrix (Technologie-Name)
    expect(screen.getByRole('columnheader', { name: 'Okta' })).toBeInTheDocument()
    // Gap-Panel zeigt EDR (ungedeckt), aber nicht MFA (gedeckt durch Okta)
    // .closest('div') träfe nur die Titel-Zeile selbst — der eine Ebene
    // umschließende Container enthält Titel und Gap-Chips gemeinsam.
    const gapPanel = screen.getByText('⚠ Ungedeckte Capabilities — kein Portfolio-Fit').parentElement!
    expect(gapPanel).toHaveTextContent('EDR')
    expect(gapPanel).not.toHaveTextContent('MFA')
  })

  it('zeigt deaktivierte Technologien erst nach "Inaktive anzeigen" (Regressionstest Schritt 6)', async () => {
    server.use(
      http.get('http://127.0.0.1:8000/api/portfolio/technologies', ({ request }) => {
        const includeInactive = new URL(request.url).searchParams.get('include_inactive') === 'true'
        const technologies = includeInactive
          ? [{ id: 1, name: 'Okta', type: 'Identity', active: false, capabilities: ['MFA'] }]
          : []
        return HttpResponse.json(technologies)
      }),
      http.get('http://127.0.0.1:8000/api/capabilities', () => HttpResponse.json(CAPABILITIES)),
      http.get('http://127.0.0.1:8000/api/portfolio/coverage', () =>
        HttpResponse.json({
          rows: [
            { capability: 'MFA', covering_technologies: [] },
            { capability: 'EDR', covering_technologies: [] },
          ],
          gaps: ['MFA', 'EDR'],
        }),
      ),
    )

    renderWithProviders(<Portfolio />)
    const user = userEvent.setup()

    await waitFor(() => expect(screen.getByText('Noch keine Portfolio-Technologien angelegt.')).toBeInTheDocument())

    await user.click(screen.getByRole('checkbox', { name: 'Inaktive anzeigen' }))

    // "Okta" erscheint sowohl auf der TechnologyCard als auch als
    // Spaltenkopf der Coverage-Matrix — deshalb getAllByText statt
    // getByText (das bei mehreren Treffern wirft).
    await waitFor(() => expect(screen.getAllByText('Okta').length).toBeGreaterThan(0))
    expect(screen.getByText('Inaktiv')).toBeInTheDocument()
    // Ein bereits deaktivierter Eintrag darf keinen erneuten "Deaktivieren"-Link mehr zeigen.
    expect(screen.queryByText('Deaktivieren')).not.toBeInTheDocument()
  })
})
