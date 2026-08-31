import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Route, Routes } from 'react-router-dom'

import { AppLayout } from './components/AppLayout'
import { EngagementProvider } from './lib/EngagementContext'
import { MitreImport } from './pages/admin/MitreImport'
import { Analyzer } from './pages/Analyzer'
import { Dashboard } from './pages/Dashboard'
import { Engagements } from './pages/Engagements'
import { KnowledgeBase } from './pages/KnowledgeBase'
import { Portfolio } from './pages/Portfolio'
import { Reports } from './pages/Reports'
import { Techniques } from './pages/Techniques'

const queryClient = new QueryClient()

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <EngagementProvider>
        <BrowserRouter>
          <Routes>
            <Route element={<AppLayout />}>
              <Route index element={<Dashboard />} />
              <Route path="engagements" element={<Engagements />} />
              <Route path="analyzer" element={<Analyzer />} />
              <Route path="techniques" element={<Techniques />} />
              <Route path="portfolio" element={<Portfolio />} />
              <Route path="knowledge" element={<KnowledgeBase />} />
              <Route path="reports" element={<Reports />} />
              <Route path="admin/mitre-import" element={<MitreImport />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </EngagementProvider>
    </QueryClientProvider>
  )
}

export default App
