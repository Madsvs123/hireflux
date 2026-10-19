import { get, post, patch } from './http'
import type {
  ApplicationListItem,
  AssessmentAssignment,
  CandidateDocument,
  Interview,
  JobListItem,
  ListParams,
  Message,
  MessageThread,
  Offer,
  Paginated,
} from './types'

/** Candidate-facing portal endpoints */
export const portalApi = {
  home: () =>
    get<{
      applications_count: number
      interviews_upcoming: number
      assessments_pending: number
      open_offers: number
    }>('/portal/home/'),

  myApplications: (params?: ListParams) =>
    get<Paginated<ApplicationListItem>>('/portal/applications/', params),
  myApplication: (id: string) => get(`/portal/applications/${id}/`),

  myInterviews: (params?: ListParams) => get<Paginated<Interview>>('/portal/interviews/', params),
  myAssessments: (params?: ListParams) =>
    get<Paginated<AssessmentAssignment>>('/portal/assessments/', params),
  submitAssessment: (id: string, answers: Record<string, unknown>) =>
    post(`/portal/assessments/${id}/submit/`, answers),

  myOffers: (params?: ListParams) => get<Paginated<Offer>>('/portal/offers/', params),
  respondOffer: (id: string, action: 'accept' | 'decline', note?: string) =>
    post(`/portal/offers/${id}/${action}/`, { note }),

  messages: (params?: ListParams) => get<Paginated<Message>>('/portal/messages/', params),
  sendMessage: (threadId: string, body: string) =>
    post<Message>(`/portal/messages/${threadId}/`, { message: body }),

  documents: (params?: ListParams) => get<Paginated<CandidateDocument>>('/portal/documents/', params),
  uploadDocument: (form: FormData) => post<CandidateDocument>('/portal/documents/', form),
  updateProfile: (data: Record<string, unknown>) => post('/portal/profile/', data),
}

/** Public career site */
export const careerApi = {
  listJobs: (params?: ListParams & { org?: string; slug?: string }) =>
    get<Paginated<JobListItem>>('/career/jobs/', params),
  getJob: (slugOrId: string, params?: { org?: string }) =>
    get<JobListItem & { description?: string; requirements?: string; responsibilities?: string; screening_questions?: unknown[] }>(
      `/career/jobs/${slugOrId}/`,
      params,
    ),
  apply: (data: {
    job_id: string
    first_name: string
    last_name: string
    email: string
    phone?: string
    cover_letter?: string
    answers?: Record<string, unknown>
    resume?: File
  }) => {
    const form = new FormData()
    Object.entries(data).forEach(([k, v]) => {
      if (v === undefined || v === null) return
      if (k === 'answers') form.append(k, JSON.stringify(v))
      else if (v instanceof File) form.append(k, v)
      else form.append(k, String(v))
    })
    return post('/career/jobs/apply/', form, { skipAuth: true, skipOrg: true })
  },
}
