import { get, post, patch, del } from './http'
import type { CandidateJobMatch, ListParams, Paginated, ScreeningRun } from './types'

export const screeningApi = {
  listWeights: (params?: ListParams) => get<Paginated<Record<string, unknown>>>('/screening-weights/', params),
  createWeight: (data: Record<string, unknown>) => post('/screening-weights/', data),
  updateWeight: (id: string, data: Record<string, unknown>) => patch(`/screening-weights/${id}/`, data),
  removeWeight: (id: string) => del(`/screening-weights/${id}/`),

  listParses: (params?: ListParams) => get<Paginated<Record<string, unknown>>>('/resume-parses/', params),
  getParse: (id: string) => get(`/resume-parses/${id}/`),

  listMatches: (params?: ListParams) => get<Paginated<CandidateJobMatch>>('/candidate-matches/', params),
  runMatch: (data: { candidate?: string; job_id?: string }) => post('/candidate-matches/run/', data),

  listRuns: (params?: ListParams) => get<Paginated<ScreeningRun>>('/screening-runs/', params),
  startRun: (data: { job_id: string; applications?: string[] }) =>
    post('/screening-runs/', data),
}
