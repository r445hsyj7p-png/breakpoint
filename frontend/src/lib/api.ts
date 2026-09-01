import type { components } from './api-types'

export type AnalyzerResult = components['schemas']['AnalyzerResult']
export type TechniqueResult = components['schemas']['TechniqueResult']
export type ControlRef = components['schemas']['ControlRef']
export type PrioritizedMeasure = components['schemas']['PrioritizedMeasure']
export type EngagementRead = components['schemas']['EngagementRead']
export type FindingsCreateResult = components['schemas']['FindingsCreateResult']
export type TechniqueCatalogResult = components['schemas']['TechniqueCatalogResult']
export type TechniqueSummary = components['schemas']['TechniqueSummary']
export type PortfolioTechnologyRead = components['schemas']['PortfolioTechnologyRead']
export type PortfolioTechnologyHistoryEntry = components['schemas']['PortfolioTechnologyHistoryEntry']
export type CoverageResult = components['schemas']['CoverageResult']
export type CoverageRow = components['schemas']['CoverageRow']
export type CapabilityRead = components['schemas']['CapabilityRead']
export type SalesBriefingRead = components['schemas']['SalesBriefingRead']
export type ImportBatchRead = components['schemas']['ImportBatchRead']
export type ImportDiff = components['schemas']['ImportDiff']

// Produktions-Build (frontend/.env.production) setzt das explizit auf "" —
// dann bleiben die Requests relativ und werden vom Produktions-nginx
// (nginx.conf) zum Backend proxied. Nur bei fehlender Env-Variable (lokale
// Entwicklung, "npm run dev") greift der 127.0.0.1-Default.
const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
  if (!response.ok) {
    const body = await response.text()
    throw new ApiError(response.status, body || response.statusText)
  }
  return response.json() as Promise<T>
}

export function analyze(codes: string): Promise<AnalyzerResult> {
  return request('/api/analyze', { method: 'POST', body: JSON.stringify({ codes }) })
}

export function listEngagements(): Promise<EngagementRead[]> {
  return request('/api/engagements')
}

export function createEngagement(name: string, externalRef?: string): Promise<EngagementRead> {
  return request('/api/engagements', {
    method: 'POST',
    body: JSON.stringify({ name, external_ref: externalRef ?? null }),
  })
}

export function addFindings(engagementId: number, codes: string): Promise<FindingsCreateResult> {
  return request(`/api/engagements/${engagementId}/findings`, {
    method: 'POST',
    body: JSON.stringify({ codes }),
  })
}

export function getEngagementAnalysis(engagementId: number): Promise<AnalyzerResult> {
  return request(`/api/engagements/${engagementId}/analysis`)
}

export function listTechniques(params?: {
  tactic?: string
  status?: string
  q?: string
  includeDeprecated?: boolean
}): Promise<TechniqueCatalogResult> {
  const search = new URLSearchParams()
  if (params?.tactic) search.set('tactic', params.tactic)
  if (params?.status) search.set('status', params.status)
  if (params?.q) search.set('q', params.q)
  if (params?.includeDeprecated) search.set('include_deprecated', 'true')
  const qs = search.toString()
  return request(`/api/techniques${qs ? `?${qs}` : ''}`)
}

export function listPortfolioTechnologies(includeInactive = false): Promise<PortfolioTechnologyRead[]> {
  return request(`/api/portfolio/technologies${includeInactive ? '?include_inactive=true' : ''}`)
}

export function createPortfolioTechnology(payload: {
  name: string
  type: string
  capability_ids: number[]
}): Promise<PortfolioTechnologyRead> {
  return request('/api/portfolio/technologies', { method: 'POST', body: JSON.stringify(payload) })
}

export function updatePortfolioTechnology(
  id: number,
  payload: { name?: string; type?: string; capability_ids?: number[] },
): Promise<PortfolioTechnologyRead> {
  return request(`/api/portfolio/technologies/${id}`, { method: 'PATCH', body: JSON.stringify(payload) })
}

export function deactivatePortfolioTechnology(id: number): Promise<PortfolioTechnologyRead> {
  return request(`/api/portfolio/technologies/${id}/deactivate`, { method: 'POST' })
}

export function getPortfolioTechnologyHistory(id: number): Promise<PortfolioTechnologyHistoryEntry[]> {
  return request(`/api/portfolio/technologies/${id}/history`)
}

export function getPortfolioCoverage(): Promise<CoverageResult> {
  return request('/api/portfolio/coverage')
}

export function listCapabilities(): Promise<CapabilityRead[]> {
  return request('/api/capabilities')
}

export function triggerSalesBriefing(engagementId: number): Promise<SalesBriefingRead> {
  return request(`/api/engagements/${engagementId}/sales-briefing`, { method: 'POST' })
}

export async function getLatestSalesBriefing(engagementId: number): Promise<SalesBriefingRead | null> {
  try {
    return await request(`/api/engagements/${engagementId}/sales-briefing`)
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) return null
    throw err
  }
}

export function listSalesBriefings(engagementId: number): Promise<SalesBriefingRead[]> {
  return request(`/api/engagements/${engagementId}/sales-briefings`)
}

export function markSalesBriefingReviewed(
  briefingId: number,
  reviewedBy?: string,
): Promise<SalesBriefingRead> {
  return request(`/api/sales-briefings/${briefingId}/mark-reviewed`, {
    method: 'POST',
    body: JSON.stringify({ reviewed_by: reviewedBy ?? null }),
  })
}

export function triggerMitreImportFetch(triggeredBy?: string): Promise<ImportBatchRead> {
  const search = new URLSearchParams()
  if (triggeredBy) search.set('triggered_by', triggeredBy)
  const qs = search.toString()
  return request(`/api/admin/mitre-import/fetch${qs ? `?${qs}` : ''}`, { method: 'POST' })
}

export async function uploadMitreImportBundle(file: File, triggeredBy?: string): Promise<ImportBatchRead> {
  const formData = new FormData()
  formData.append('file', file)
  const search = new URLSearchParams()
  if (triggeredBy) search.set('triggered_by', triggeredBy)
  const qs = search.toString()
  // Kein request()-Helper hier: der setzt Content-Type: application/json
  // fest, das würde die vom Browser automatisch gesetzte
  // multipart/form-data-Boundary überschreiben.
  const response = await fetch(`${BASE_URL}/api/admin/mitre-import/upload${qs ? `?${qs}` : ''}`, {
    method: 'POST',
    body: formData,
  })
  if (!response.ok) {
    const body = await response.text()
    throw new ApiError(response.status, body || response.statusText)
  }
  return response.json() as Promise<ImportBatchRead>
}

export function listMitreImportBatches(): Promise<ImportBatchRead[]> {
  return request('/api/admin/mitre-import/batches')
}

export function getMitreImportBatch(batchId: number): Promise<ImportBatchRead> {
  return request(`/api/admin/mitre-import/batches/${batchId}`)
}

export function applyMitreImportBatch(
  batchId: number,
  selection: { technique_ids: string[]; mitigation_technique_ids: string[] },
): Promise<ImportBatchRead> {
  return request(`/api/admin/mitre-import/batches/${batchId}/apply`, {
    method: 'POST',
    body: JSON.stringify(selection),
  })
}

export function rollbackMitreImportBatch(batchId: number): Promise<ImportBatchRead> {
  return request(`/api/admin/mitre-import/batches/${batchId}/rollback`, { method: 'POST' })
}
