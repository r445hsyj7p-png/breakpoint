import { BrowserRouter, Route, Routes } from 'react-router-dom'

import { AppLayout } from './components/AppLayout'
import { Analyzer } from './pages/Analyzer'
import { Dashboard } from './pages/Dashboard'
import { Engagements } from './pages/Engagements'
import { KnowledgeBase } from './pages/KnowledgeBase'
import { Portfolio } from './pages/Portfolio'
import { Reports } from './pages/Reports'
import { Techniques } from './pages/Techniques'

function App() {
  return (
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
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
