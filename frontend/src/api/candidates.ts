import { del, get, patch, post } from './http'
import type {
  Candidate,
  CandidateDocument,
  CandidateListItem,
  CandidateNote,
  ListParams,
  Paginated,
} from './types'

export const candidatesApi = {
  list: (params?: ListParams) => get<Paginated<CandidateListItem>>('/candidates/', params),
  get: (id: string) => get<CandidateListItem>(`/candidates/${id}/`),
  create: (data: Partial<Candidate>) => post<Candidate>('/candidates/', data),
  update: (id: string, data: Partial<Candidate>) => patch<Candidate>(`/candidates/${id}/`, data),
  remove: (id: string) => del(`/candidates/${id}/`),

  addNote: (id: string, data: { body: string; visibility?: string; pinned?: boolean }) =>
    patch<CandidateNote>(`/candidates/${id}/notes/`, data),
  addDocument: (id: string, form: FormData) =>
    post<CandidateDocument>(`/candidates/${id}/documents/`, form),
  addExperience: (id: string, data: Record<string, unknown>) =>
    post(`/candidates/${id}/experience/`, data),
  addEducation: (id: string, data: Record<string, unknown>) =>
    post(`/candidates/${id}/education/`, data),

  detectDuplicates: (data?: { candidate_id?: string; persist?: boolean }) =>
    post('/candidates/detect-duplicates/', data ?? {}),
  merge: (data: {
    primary_id: string
    secondary_id: string
    field_preferences?: Record<string, 'primary' | 'secondary'>
  }) => post('/candidates/merge/', { ...data, primary_id: data.secondary_id, secondary_id: data.primary_id }),
}

export const duplicateMatchesApi = {
  list: (params?: ListParams) => get<Paginated<Record<string, unknown>>>('/duplicate-matches/', params),
  resolve: (id: string, data: { status: string }) => patch(`/duplicate-matches/${id}/`, data),
}
