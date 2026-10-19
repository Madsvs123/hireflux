import { del, get, patch, post } from './http'
import type { ListParams, Paginated } from './types'

// ---------------------------------------------------------------------------
// Compliance domain types (mirrors apps/compliance serializers)
// ---------------------------------------------------------------------------

export type PolicyType = 'privacy' | 'consent' | 'retention' | 'eeo'

export interface CompliancePolicy {
  id: string
  name: string
  policy_type: PolicyType
  version: number
  content_html: string
  is_active: boolean
  effective_at: string | null
  organization: string
  created_by: string | null
  updated_by: string | null
  created_at: string
  updated_at: string
}

export type ConsentStatus = 'granted' | 'withdrawn'

export interface ConsentRecord {
  id: string
  candidate: string | null
  candidate_name: string | null
  user: string | null
  user_email: string | null
  policy: string
  policy_name: string
  purpose: string
  status: ConsentStatus
  granted_at: string
  withdrawn_at: string | null
  source: string
  ip_address: string | null
  consent_version: number
  organization: string
  created_by: string | null
  updated_by: string | null
  created_at: string
  updated_at: string
}

export type RetentionAction = 'anonymize' | 'delete' | 'archive'

export interface DataRetentionPolicy {
  id: string
  data_type: string
  retention_days: number
  action: RetentionAction
  is_active: boolean
  notes: string
  organization: string
  created_by: string | null
  updated_by: string | null
  created_at: string
  updated_at: string
}

export interface EEODeclaration {
  id: string
  token: string
  candidate: string | null
  candidate_name: string | null
  job: string | null
  job_title: string | null
  gender: string
  race_ethnicity: string
  veteran_status: string
  disability_status: string
  submitted_at: string | null
  is_anonymous: boolean
  organization: string
  created_by: string | null
  updated_by: string | null
  created_at: string
  updated_at: string
}

export interface ComplianceNote {
  id: string
  candidate: string | null
  candidate_name: string | null
  user: string | null
  user_email: string | null
  category: string
  body: string
  organization: string
  created_by: string | null
  updated_by: string | null
  created_at: string
  updated_at: string
}

export type ExportStatus = 'pending' | 'processing' | 'completed' | 'failed'

export interface DataExportRequest {
  id: string
  candidate: string
  candidate_name: string
  requested_by: string | null
  requested_by_email: string | null
  status: ExportStatus
  requested_at: string
  completed_at: string | null
  export_file: string | null
  include_fields: string[]
  organization: string
  created_by: string | null
  updated_by: string | null
  created_at: string
  updated_at: string
}

export interface ComplianceOverview {
  consents: { granted: number; withdrawn: number }
  policies: { active: number; total: number; by_type: Record<string, number> }
  retention: { active_policies: number }
  exports: Record<string, number>
  eeo_declarations: number
}

// ---------------------------------------------------------------------------
// API clients
// ---------------------------------------------------------------------------

export const compliancePoliciesApi = {
  list: (params?: ListParams) =>
    get<Paginated<CompliancePolicy>>('/compliance-policies/', params),
  get: (id: string) => get<CompliancePolicy>(`/compliance-policies/${id}/`),
  create: (data: Partial<CompliancePolicy>) =>
    post<CompliancePolicy>('/compliance-policies/', data),
  update: (id: string, data: Partial<CompliancePolicy>) =>
    patch<CompliancePolicy>(`/compliance-policies/${id}/`, data),
  remove: (id: string) => del(`/compliance-policies/${id}/`),
  activate: (id: string) => patch<CompliancePolicy>(`/compliance-policies/${id}/activate/`),
}

export const consentRecordsApi = {
  list: (params?: ListParams) => get<Paginated<ConsentRecord>>('/consent-records/', params),
  get: (id: string) => get<ConsentRecord>(`/consent-records/${id}/`),
  grant: (data: {
    policy: string
    purpose?: string
    candidate_id?: string | null
    user_id?: string | null
    source?: string
    ip_address?: string | null
  }) => post<ConsentRecord>('/consent-records/grant/', data),
  withdraw: (id: string) => post<ConsentRecord>(`/consent-records/${id}/withdraw/`),
}

export const retentionPoliciesApi = {
  list: (params?: ListParams) =>
    get<Paginated<DataRetentionPolicy>>('/retention-policies/', params),
  get: (id: string) => get<DataRetentionPolicy>(`/retention-policies/${id}/`),
  create: (data: Partial<DataRetentionPolicy>) =>
    post<DataRetentionPolicy>('/retention-policies/', data),
  update: (id: string, data: Partial<DataRetentionPolicy>) =>
    patch<DataRetentionPolicy>(`/retention-policies/${id}/`, data),
  remove: (id: string) => del(`/retention-policies/${id}/`),
}

export const eeoDeclarationsApi = {
  list: (params?: ListParams) => get<Paginated<EEODeclaration>>('/eeo-declarations/', params),
  get: (id: string) => get<EEODeclaration>(`/eeo-declarations/${id}/`),
  create: (data: { candidate_id?: string | null; job_id?: string | null }) =>
    post<EEODeclaration>('/eeo-declarations/', data),
  update: (id: string, data: Partial<EEODeclaration>) =>
    patch<EEODeclaration>(`/eeo-declarations/${id}/`, data),
  remove: (id: string) => del(`/eeo-declarations/${id}/`),
  submit: (data: {
    token: string
    gender?: string
    race_ethnicity?: string
    veteran_status?: string
    disability_status?: string
  }) => post<EEODeclaration>('/eeo-declarations/submit/', data, { skipAuth: true, skipOrg: true }),
}

export const complianceNotesApi = {
  list: (params?: ListParams) => get<Paginated<ComplianceNote>>('/compliance-notes/', params),
  get: (id: string) => get<ComplianceNote>(`/compliance-notes/${id}/`),
  create: (data: { candidate_id?: string | null; category?: string; body?: string }) =>
    post<ComplianceNote>('/compliance-notes/', data),
  update: (id: string, data: Partial<ComplianceNote>) =>
    patch<ComplianceNote>(`/compliance-notes/${id}/`, data),
  remove: (id: string) => del(`/compliance-notes/${id}/`),
}

export const dataExportRequestsApi = {
  list: (params?: ListParams) =>
    get<Paginated<DataExportRequest>>('/data-export-requests/', params),
  get: (id: string) => get<DataExportRequest>(`/data-export-requests/${id}/`),
  create: (data: { candidate_id: string; include_fields?: string[] }) =>
    post<DataExportRequest>('/data-export-requests/', data),
  update: (id: string, data: Partial<DataExportRequest>) =>
    patch<DataExportRequest>(`/data-export-requests/${id}/`, data),
  remove: (id: string) => del(`/data-export-requests/${id}/`),
  fulfill: (id: string) => post<DataExportRequest>(`/data-export-requests/${id}/fulfill/`),
  download: (id: string) => get<unknown>(`/data-export-requests/${id}/download/`),
}

export const complianceApi = {
  overview: () => get<ComplianceOverview>('/compliance-overview/'),
}
