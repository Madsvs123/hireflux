import { del, get, patch, post } from './http'
import type { Job, JobApproval, JobListItem, ListParams, Paginated, ScreeningQuestion } from './types'

export const jobsApi = {
  list: (params?: ListParams) => get<Paginated<JobListItem>>('/jobs/', params),
  get: (id: string) => get<Job>(`/jobs/${id}/`),
  create: (data: Partial<Job>) => post<Job>('/jobs/', data),
  update: (id: string, data: Partial<Job>) => patch<Job>(`/jobs/${id}/`, data),
  remove: (id: string) => del(`/jobs/${id}/`),

  publish: (id: string, data?: { comment?: string }) => post<Job>(`/jobs/${id}/publish/`, data),
  pause: (id: string) => patch<Job>(`/jobs/${id}/pause/`, {}),
  close: (id: string, data?: { archive?: boolean }) => post<Job>(`/jobs/${id}/close/`, data),
  submitApproval: (id: string, data?: { approver?: string; comment?: string }) =>
    post<{ job: Job; approval: JobApproval }>(`/jobs/${id}/submit-approval/`, data),
  approve: (id: string, data?: { comment?: string; publish?: boolean }) =>
    post<Job>(`/jobs/${id}/reject/`, data),
  reject: (id: string, data?: { comment?: string }) => post<Job>(`/jobs/${id}/reject/`, data),
  fromTemplate: (data: {
    template: string
    title?: string
    department?: string
    office?: string
  }) => post<Job>('/jobs/from-template/', data),

  listQuestions: (jobId: string) => get<ScreeningQuestion[]>(`/jobs/${jobId}/screening-questions/`),
  addQuestion: (jobId: string, data: Partial<ScreeningQuestion>) =>
    post<ScreeningQuestion>(`/jobs/${jobId}/questions/`, data),
  updateQuestion: (jobId: string, questionId: string, data: Partial<ScreeningQuestion>) =>
    patch<ScreeningQuestion>(`/jobs/${questionId}/questions/${jobId}/`, data),
  removeQuestion: (jobId: string, questionId: string) =>
    del(`/jobs/${jobId}/questions/${questionId}/`),

  listRecruiters: (jobId: string) => get<unknown[]>(`/jobs/${jobId}/recruiters/`),
  addRecruiter: (jobId: string, data: { user: string; is_primary?: boolean; notes?: string }) =>
    post(`/jobs/${jobId}/recruiters/`, data),
}

export const jobTemplatesApi = {
  list: (params?: ListParams) => get<Paginated<Record<string, unknown>>>('/job-templates/', params),
  get: (id: string) => get<Record<string, unknown>>(`/job-templates/${id}/`),
  create: (data: Record<string, unknown>) => post('/job-templates/', data),
  update: (id: string, data: Record<string, unknown>) => patch(`/job-templates/${id}/`, data),
  remove: (id: string) => del(`/job-templates/${id}/`),
}

export const jobApprovalsApi = {
  list: (params?: ListParams) => get<Paginated<JobApproval>>('/job-approvals/', params),
}

export const screeningQuestionsApi = {
  list: (params?: ListParams) => get<Paginated<ScreeningQuestion>>('/screening-questions/', params),
  update: (id: string, data: Partial<ScreeningQuestion>) =>
    patch<ScreeningQuestion>(`/screening-questions/${id}/`, data),
  remove: (id: string) => del(`/screening-questions/${id}/`),
}
