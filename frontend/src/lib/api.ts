import type { components } from './api-types'

export type AnalyzerResult = components['schemas']['AnalyzerResult']
export type TechniqueResult = components['schemas']['TechniqueResult']
export type ControlRef = components['schemas']['ControlRef']
export type PrioritizedMeasure = components['schemas']['PrioritizedMeasure']
export type EngagementRead = components['schemas']['EngagementRead']
export type FindingsCreateResult = components['schemas']['FindingsCreateResult']
export type TechniqueCatalogResult = components['schemas']['TechniqueCatalogResult']
export type TechniqueSummary = components['schemas']['TechniqueSummary']

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
}): Promise<TechniqueCatalogResult> {
  const search = new URLSearchParams()
  if (params?.tactic) search.set('tactic', params.tactic)
  if (params?.status) search.set('status', params.status)
  if (params?.q) search.set('q', params.q)
  const qs = search.toString()
  return request(`/api/techniques${qs ? `?${qs}` : ''}`)
}
