import { del, get, patch, post } from './http'
import type { ListParams, Paginated } from './types'

// ---------------------------------------------------------------------------
// Documents domain types (mirrors apps/documents serializers)
// ---------------------------------------------------------------------------

export interface DocumentCategory {
  id: string
  name: string
  description: string
  is_active: boolean
  organization: string
  created_by: string | null
  updated_by: string | null
  created_at: string
  updated_at: string
}

export interface DocumentTemplate {
  id: string
  category: string | null
  category_name: string | null
  name: string
  description: string
  body_html: string
  body_text: string
  variables: string[]
  default_currency: string
  is_active: boolean
  organization: string
  created_by: string | null
  updated_by: string | null
  created_at: string
  updated_at: string
}

export type GeneratedDocumentStatus = 'draft' | 'finalized' | 'void'

export interface GeneratedDocument {
  id: string
  template: string | null
  template_name: string | null
  title: string
  content_html: string
  content_text: string
  status: GeneratedDocumentStatus
  related_candidate: string | null
  related_candidate_name: string | null
  related_job: string | null
  related_job_title: string | null
  related_offer: string | null
  related_offer_title: string | null
  finalized_at: string | null
  finalized_by: string | null
  finalized_by_name: string | null
  organization: string
  created_by: string | null
  updated_by: string | null
  created_at: string
  updated_at: string
}

export type DocumentSignRequestStatus = 'pending' | 'signed' | 'declined' | 'voided'

export interface DocumentSignRequest {
  id: string
  token: string
  document: string
  document_title: string
  signer_name: string
  signer_email: string
  status: DocumentSignRequestStatus
  message: string
  signed_at: string | null
  sent_at: string | null
  expires_at: string | null
  signature_data: Record<string, unknown>
  signature_count: number
  organization: string
  created_by: string | null
  updated_by: string | null
  created_at: string
  updated_at: string
}

export interface DocumentSignature {
  id: string
  sign_request: string
  name: string
  email: string
  signature_svg: string
  ip_address: string | null
  signed_at: string
  organization: string
  created_by: string | null
  updated_by: string | null
  created_at: string
  updated_at: string
}

export interface RenderResult {
  title: string
  content_html: string
  content_text: string
}

export interface PublicSignDetail {
  sign_request: DocumentSignRequest
  document: GeneratedDocument
  signatures: DocumentSignature[]
}

// ---------------------------------------------------------------------------
// API clients
// ---------------------------------------------------------------------------

export const documentCategoriesApi = {
  list: (params?: ListParams) =>
    get<Paginated<DocumentCategory>>('/document-categories/', params),
  get: (id: string) => get<DocumentCategory>(`/document-categories/${id}/`),
  create: (data: Partial<DocumentCategory>) =>
    post<DocumentCategory>('/document-categories/', data),
  update: (id: string, data: Partial<DocumentCategory>) =>
    patch<DocumentCategory>(`/document-categories/${id}/`, data),
  remove: (id: string) => del(`/document-categories/${id}/`),
}

export const documentTemplatesApi = {
  list: (params?: ListParams) =>
    get<Paginated<DocumentTemplate>>('/document-templates/', params),
  get: (id: string) => get<DocumentTemplate>(`/document-templates/${id}/`),
  create: (data: Partial<DocumentTemplate>) =>
    post<DocumentTemplate>('/document-templates/', data),
  update: (id: string, data: Partial<DocumentTemplate>) =>
    patch<DocumentTemplate>(`/document-templates/${id}/`, data),
  remove: (id: string) => del(`/document-templates/${id}/`),
  render: (id: string, data?: { variables?: Record<string, string> }) =>
    post<RenderResult>(`/document-templates/${id}/render/`, data),
  duplicate: (id: string) => post<DocumentTemplate>(`/document-templates/duplicate/${id}/`),
}

export const generatedDocumentsApi = {
  list: (params?: ListParams) =>
    get<Paginated<GeneratedDocument>>('/generated-documents/', params),
  get: (id: string) => get<GeneratedDocument>(`/generated-documents/${id}/`),
  create: (data: {
    template_id?: string | null
    title?: string
    variables?: Record<string, string>
    related_candidate_id?: string | null
    related_job_id?: string | null
    related_offer_id?: string | null
    content_html?: string
    content_text?: string
  }) => post<GeneratedDocument>('/generated-documents/', data),
  update: (id: string, data: Partial<GeneratedDocument>) =>
    patch<GeneratedDocument>(`/generated-documents/${id}/`, data),
  remove: (id: string) => del(`/generated-documents/${id}/`),
  finalize: (id: string) => post<GeneratedDocument>(`/generated-documents/${id}/finalize/`),
  void: (id: string) => post<GeneratedDocument>(`/generated-documents/${id}/void/`),
  download: (id: string) => get<unknown>(`/generated-documents/${id}/download/`),
}

export const documentSignRequestsApi = {
  list: (params?: ListParams) =>
    get<Paginated<DocumentSignRequest>>('/document-sign-requests/', params),
  get: (id: string) => get<DocumentSignRequest>(`/document-sign-requests/${id}/`),
  create: (data: {
    document: string
    signer_name: string
    signer_email: string
    message?: string
  }) => post<DocumentSignRequest>('/document-sign-requests/', data),
  update: (id: string, data: Partial<DocumentSignRequest>) =>
    patch<DocumentSignRequest>(`/document-sign-requests/${id}/`, data),
  remove: (id: string) => del(`/document-sign-requests/${id}/`),
  send: (id: string) => post<DocumentSignRequest>(`/document-sign-requests/${id}/send/`),
  resend: (id: string) => post<DocumentSignRequest>(`/document-sign-requests/${id}/resend/`),
  void: (id: string) => post<DocumentSignRequest>(`/document-sign-requests/${id}/void/`),
}

export const publicSignApi = {
  detail: (token: string, opts?: { skipAuth?: boolean; skipOrg?: boolean }) =>
    get<PublicSignDetail>(`/public/sign/${token}/`, undefined),
  submit: (
    token: string,
    data: { name: string; email: string; signature_svg?: string },
    opts?: { skipAuth?: boolean; skipOrg?: boolean },
  ) => post<PublicSignDetail>(`/public/sign/${token}/submit/`, data, { skipAuth: true, skipOrg: true }),
}
