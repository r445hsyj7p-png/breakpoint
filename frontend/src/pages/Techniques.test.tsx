import { screen, waitFor } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'

import { server } from '../test/mswServer'
import { renderWithProviders } from '../test/testUtils'
import { Techniques } from './Techniques'

const CATALOG_RESULT = {
  techniques: [
    {
      technique_id: 'T1078',
      technique_name: 'Valid Accounts',
      tactic_name: 'Initial Access',
      mapping_source: 'specific',
    },
    {
      technique_id: 'T1595',
      technique_name: 'Active Scanning',
      tactic_name: 'Reconnaissance',
      mapping_source: 'tactic_default',
    },
  ],
  total: 2,
}

describe('Techniques', () => {
  it('zeigt den Katalog und die Filter-Query-Parameter', async () => {
    const requestedPaths: string[] = []
    server.use(
      http.get('http://127.0.0.1:8000/api/techniques', ({ request }) => {
        requestedPaths.push(new URL(request.url).pathname)
        return HttpResponse.json(CATALOG_RESULT)
      }),
    )

    renderWithProviders(<Techniques />)

    await waitFor(() => expect(screen.getByText('Valid Accounts')).toBeInTheDocument())
    expect(screen.getByText('Active Scanning')).toBeInTheDocument()
    expect(screen.getByText('2 Zeilen')).toBeInTheDocument()
    expect(requestedPaths).toContain('/api/techniques')
  })

  it('zeigt mitre_derived-Techniken mit eigenem Status-Label (Regressionstest Schritt 6)', async () => {
    server.use(
      http.get('http://127.0.0.1:8000/api/techniques', () =>
        HttpResponse.json({
          techniques: [
            {
              technique_id: 'T1210',
              technique_name: 'Exploitation of Remote Services',
              tactic_name: 'Lateral Movement',
              mapping_source: 'mitre_derived',
            },
          ],
          total: 1,
        }),
      ),
    )

    renderWithProviders(<Techniques />)

    await waitFor(() => expect(screen.getByText('MITRE-Mitigation')).toBeInTheDocument())
  })

  it('zeigt einen Hinweis, wenn kein Ergebnis zur Filterkombination passt', async () => {
    server.use(
      http.get('http://127.0.0.1:8000/api/techniques', () =>
        HttpResponse.json({ techniques: [], total: 0 }),
      ),
    )

    renderWithProviders(<Techniques />)

    await waitFor(() => expect(screen.getByText('Keine Techniken gefunden.')).toBeInTheDocument())
  })
})
