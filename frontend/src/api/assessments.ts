import { del, get, patch, post } from './http'
import type { AssessmentAssignment, AssessmentTemplate, ListParams, Paginated } from './types'

export const assessmentsApi = {
  listTemplates: (params?: ListParams) =>
    get<Paginated<AssessmentTemplate>>('/assessment-templates/', params),
  getTemplate: (id: string) => get<AssessmentTemplate>(`/assessment-templates/${id}/`),
  createTemplate: (data: Partial<AssessmentTemplate>) =>
    post<AssessmentTemplate>('/assessment-templates/', data),
  updateTemplate: (id: string, data: Partial<AssessmentTemplate>) =>
    patch<AssessmentTemplate>(`/assessment-templates/${id}/`, data),
  removeTemplate: (id: string) => del(`/assessment-templates/${id}/`),

  listAssignments: (params?: ListParams) =>
    get<Paginated<AssessmentAssignment>>('/assessment-assignments/', params),
  getAssignment: (id: string) => get<AssessmentAssignment>(`/assessment-assignments/${id}/`),
  createAssignment: (data: {
    template_id: string
    application_id: string
    due_at?: string
  }) => post<AssessmentAssignment>('/assessment-assignments/', data),
  updateAssignment: (id: string, data: Partial<AssessmentAssignment>) =>
    patch<AssessmentAssignment>(`/assessment-assignments/${id}/`, data),
  score: (id: string, data: { score: number; notes?: string }) =>
    patch<AssessmentAssignment>(`/assessment-assignments/${id}/score/`, data),
}
