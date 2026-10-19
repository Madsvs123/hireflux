import { del, get, patch, post } from './http'
import type { ListParams, Paginated } from './types'

// ---------------------------------------------------------------------------
// Background checks domain types (mirrors apps/background_checks serializers)
// ---------------------------------------------------------------------------

export interface BackgroundCheckPackage {
  id: string
  name: string
  description: string
  check_types: string[]
  price: string
  turnaround_days: number
  is_active: boolean
  organization: string
  created_by: string | null
  updated_by: string | null
  created_at: string
  updated_at: string
}

export interface ScreeningProvider {
  id: string
  name: string
  key: string
  api_endpoint: string
  api_key_encrypted: string
  is_active: boolean
  supported_checks: string[]
  organization: string
  created_by: string | null
  updated_by: string | null
  created_at: string
  updated_at: string
}

export interface CheckLatestReport {
  id: string
  status: string
  summary: string
  findings: Array<Record<string, unknown>>
  received_at: string | null
  reviewed_at: string | null
}

export type BackgroundCheckRequestStatus =
  | 'draft'
  | 'submitted'
  | 'in_progress'
  | 'completed'
  | 'on_hold'
  | 'cancelled'

export interface BackgroundCheckRequest {
  id: string
  candidate: string
  candidate_name: string
  candidate_email_actual: string
  job: string | null
  job_title: string | null
  package: string | null
  package_name: string | null
  status: BackgroundCheckRequestStatus
  initiated_by: string | null
  submitted_at: string | null
  completed_at: string | null
  provider: string | null
  provider_name: string | null
  provider_ref: string
  candidate_email: string
  candidate_phone: string
  consent_given_at: string | null
  result_summary: Record<string, unknown>
  latest_report: CheckLatestReport | null
  organization: string
  created_by: string | null
  updated_by: string | null
  created_at: string
  updated_at: string
}

export type ReportStatus = 'pending' | 'clear' | 'consider' | 'flagged'

export interface BackgroundCheckReport {
  id: string
  request: string
  request_candidate: string
  status: ReportStatus
  summary: string
  findings: Array<Record<string, unknown>>
  report_file: string | null
  received_at: string | null
  reviewed_by: string | null
  reviewed_by_name: string | null
  reviewed_at: string | null
  organization: string
  created_by: string | null
  updated_by: string | null
  created_at: string
  updated_at: string
}

export type DisputeStatus = 'open' | 'under_review' | 'resolved' | 'rejected'

export interface CheckDispute {
  id: string
  report: string
  candidate: string
  candidate_name: string
  reason: string
  details: string
  status: DisputeStatus
  resolution: string
  resolved_by: string | null
  resolved_by_name: string | null
  resolved_at: string | null
  organization: string
  created_by: string | null
  updated_by: string | null
  created_at: string
  updated_at: string
}

export interface CheckStatusPayload {
  id: string
  status: string
  submitted_at: string | null
  completed_at: string | null
  provider_ref: string
  consent_given_at: string | null
  result_summary: Record<string, unknown>
  report: CheckLatestReport | null
}

export interface ProviderTestResult {
  ok: boolean
  status_code?: number
  latency_ms?: number
  error?: string
}

// ---------------------------------------------------------------------------
// API clients
// ---------------------------------------------------------------------------

export const backgroundCheckPackagesApi = {
  list: (params?: ListParams) =>
    get<Paginated<BackgroundCheckPackage>>('/background-check-packages/', params),
  get: (id: string) => get<BackgroundCheckPackage>(`/background-check-packages/${id}/`),
  create: (data: Partial<BackgroundCheckPackage>) =>
    post<BackgroundCheckPackage>('/background-check-packages/', data),
  update: (id: string, data: Partial<BackgroundCheckPackage>) =>
    patch<BackgroundCheckPackage>(`/background-check-packages/${id}/`, data),
  remove: (id: string) => del(`/background-check-packages/${id}/`),
}

export const screeningProvidersApi = {
  list: (params?: ListParams) =>
    get<Paginated<ScreeningProvider>>('/screening-providers/', params),
  get: (id: string) => get<ScreeningProvider>(`/screening-providers/${id}/`),
  create: (data: Partial<ScreeningProvider>) =>
    post<ScreeningProvider>('/screening-providers/', data),
  update: (id: string, data: Partial<ScreeningProvider>) =>
    patch<ScreeningProvider>(`/screening-providers/${id}/`, data),
  remove: (id: string) => del(`/screening-providers/${id}/`),
  test: (id: string) => get<ProviderTestResult>(`/screening-providers/${id}/test/`),
}

export const backgroundCheckRequestsApi = {
  list: (params?: ListParams) =>
    get<Paginated<BackgroundCheckRequest>>('/background-check-requests/', params),
  get: (id: string) => get<BackgroundCheckRequest>(`/background-check-requests/${id}/`),
  create: (data: {
    candidate: string
    job_id?: string | null
    package_id?: string | null
    candidate_email?: string
    candidate_phone?: string
  }) => post<BackgroundCheckRequest>('/background-check-requests/', data),
  update: (id: string, data: Partial<BackgroundCheckRequest>) =>
    patch<BackgroundCheckRequest>(`/background-check-requests/${id}/`, data),
  remove: (id: string) => del(`/background-check-requests/${id}/`),
  submit: (id: string) => post<BackgroundCheckRequest>(`/background-check-requests/${id}/submit/`),
  cancel: (id: string) => post<BackgroundCheckRequest>(`/background-check-requests/${id}/cancel/`),
  resend: (id: string) => post<BackgroundCheckRequest>(`/background-check-requests/${id}/resend/`),
  status: (id: string) => get<CheckStatusPayload>(`/background-check-requests/${id}/status/`),
}

export const backgroundCheckReportsApi = {
  list: (params?: ListParams) =>
    get<Paginated<BackgroundCheckReport>>('/background-check-reports/', params),
  get: (id: string) => get<BackgroundCheckReport>(`/background-check-reports/${id}/`),
  review: (
    id: string,
    data: {
      decision: ReportStatus
      summary?: string
      findings?: Array<Record<string, unknown>>
    },
  ) => post<BackgroundCheckReport>(`/background-check-reports/${id}/review/`, data),
}

export const checkDisputesApi = {
  list: (params?: ListParams) => get<Paginated<CheckDispute>>('/check-disputes/', params),
  get: (id: string) => get<CheckDispute>(`/check-disputes/${id}/`),
  create: (data: {
    report_id: string
    candidate_id: string
    reason: string
    details?: string
  }) => post<CheckDispute>('/check-disputes/', data),
  update: (id: string, data: Partial<CheckDispute>) =>
    patch<CheckDispute>(`/check-disputes/${id}/`, data),
  remove: (id: string) => del(`/check-disputes/${id}/`),
  resolve: (id: string, data?: { resolution?: string }) =>
    post<CheckDispute>(`/check-disputes/${id}/resolve/`, data),
  reject: (id: string, data?: { resolution?: string }) =>
    post<CheckDispute>(`/check-disputes/${id}/reject/`, data),
}

export const backgroundCheckWebhookApi = {
  callback: (providerKey: string, data: Record<string, unknown>) =>
    post<Record<string, unknown>>(`/webhook/background-check/${providerKey}/`, data, {
      skipAuth: true,
      skipOrg: true,
    }),
}
