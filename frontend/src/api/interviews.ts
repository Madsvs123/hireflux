import { del, get, patch, post } from './http'
import type { Interview, ListParams, Paginated } from './types'

export const interviewsApi = {
  list: (params?: ListParams) => get<Paginated<Interview>>('/interviews/', params),
  get: (id: string) => get<Interview>(`/interviews/${id}/`),
  create: (data: Partial<Interview>) => post<Interview>('/interviews/', data),
  update: (id: string, data: Partial<Interview>) => patch<Interview>(`/interviews/${id}/`, data),
  remove: (id: string) => del(`/interviews/${id}/`),
  submitScorecard: (
    id: string,
    data: {
      overall_rating: string
      recommendation: string
      competencies: Array<{ name: string; rating: number; notes?: string }>
      comments?: string
    },
  ) => patch<Interview>(`/interviews/${id}/scorecard/`, data),
  cancel: (id: string, data?: { reason?: string }) =>
    del<Interview>(`/interviews/${id}/cancel/`),
  complete: (id: string) => post<Interview>(`/interviews/${id}/complete/`, {}),
}
