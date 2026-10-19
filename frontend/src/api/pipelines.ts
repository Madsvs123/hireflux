import { del, get, patch, post } from './http'
import type {
  Application,
  ApplicationListItem,
  BoardColumn,
  ListParams,
  Paginated,
  PipelineStage,
  PipelineTemplate,
} from './types'

export const pipelineTemplatesApi = {
  list: (params?: ListParams) => get<Paginated<PipelineTemplate>>('/pipeline-templates/', params),
  get: (id: string) => get<PipelineTemplate>(`/pipeline-templates/${id}/`),
  create: (data: Partial<PipelineTemplate>) => post<PipelineTemplate>('/pipeline-templates/', data),
  update: (id: string, data: Partial<PipelineTemplate>) =>
    patch<PipelineTemplate>(`/pipeline-templates/${id}/`, data),
  remove: (id: string) => del(`/pipeline-templates/${id}/`),
  seedDefault: (force = false) =>
    post<PipelineTemplate>('/pipeline-templates/seed-default/', { force }),
  listStages: (id: string) => get<PipelineStage[]>(`/pipeline-templates/${id}/stages/`),
  addStage: (id: string, data: Partial<PipelineStage>) =>
    post<PipelineStage>(`/pipeline-templates/${id}/stages/`, data),
}

export const pipelineStagesApi = {
  list: (params?: ListParams) => get<Paginated<PipelineStage>>('/pipeline-stages/', params),
  update: (id: string, data: Partial<PipelineStage>) =>
    patch<PipelineStage>(`/pipeline-stages/${id}/`, data),
  remove: (id: string) => del(`/pipeline-stages/${id}/`),
}

export const applicationsApi = {
  list: (params?: ListParams) => get<Paginated<ApplicationListItem>>('/applications/', params),
  get: (id: string) => get<Application>(`/applications/${id}/`),
  create: (data: {
    job_id: string
    candidate_id: string
    answers?: Record<string, unknown>
    cover_letter?: string
    source?: string
  }) => post<Application>('/applications/', data),
  move: (id: string, data: { stage_id: string; note?: string; rejection_reason?: string }) =>
    patch<Application>(`/applications/${id}/move/`, data),
  board: (params?: { job?: string; template?: string }) =>
    get<BoardColumn[] | { columns: BoardColumn[] }>('/applications/board/', params),
  bulkMove: (data: { ids: string[]; stage_id: string; note?: string }) =>
    post('/applications/bulk-move/', data),
  bulkReject: (data: { application_ids: string[]; reason?: string; stage_id?: string }) =>
    post('/applications/bulk-reject/', data),
  bulkTag: (data: {
    application_ids: string[]
    tags: string[]
    mode?: 'add' | 'replace' | 'remove'
  }) => post('/applications/bulk-tag/', data),
  history: (id: string) => post(`/applications/${id}/history/`),
  activities: (id: string) => get(`/applications/${id}/activities/`),
  reject: (id: string, data?: { reason?: string }) =>
    post<Application>(`/applications/${id}/reject/`, data),
}
