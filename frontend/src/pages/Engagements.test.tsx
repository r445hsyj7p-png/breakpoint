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
})
