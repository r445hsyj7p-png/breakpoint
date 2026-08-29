import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render } from '@testing-library/react'
import type { ReactElement } from 'react'
import { MemoryRouter } from 'react-router-dom'

import { EngagementProvider } from '../lib/EngagementContext'

export function renderWithProviders(ui: ReactElement) {
  // Frischer QueryClient pro Test, sonst würde der Cache zwischen Tests
  // "leaken" und Ergebnisse von einem Test in den nächsten durchsickern.
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })

  return render(
    <QueryClientProvider client={queryClient}>
      <EngagementProvider>
        <MemoryRouter>{ui}</MemoryRouter>
      </EngagementProvider>
    </QueryClientProvider>,
  )
}
