import { del, get, patch, post } from './http'
import type { ListParams, Paginated } from './types'

export type ReportType =
  | 'hires'
  | 'pipeline'
  | 'source'
  | 'time_to_fill'
  | 'offer_acceptance'
  | 'interview'

export type ReportRunStatus = 'queued' | 'running' | 'completed' | 'failed'
export type ReportExportFormat = 'csv' | 'xlsx' | 'pdf'
export type DashboardWidgetType = 'summary' | 'bar' | 'line' | 'pie' | 'table' | 'recent'

export interface ReportDefinition {
  id: string
  organization: string
  name: string
  description: string
  report_type: ReportType
  params: Record<string, unknown>
  schedule_cron: string
  schedule_enabled: boolean
  is_public: boolean
  last_run_at: string | null
  created_by: string | null
  updated_by: string | null
  created_at: string
  updated_at: string
}

export interface ReportRun {
  id: string
  organization: string
  definition: string
  definition_name: string | null
  report_type: ReportType
  status: ReportRunStatus
  params_snapshot: Record<string, unknown>
  result_summary: Record<string, unknown> | null
  error: string | null
  started_at: string | null
  finished_at: string | null
  triggered_by: string | null
  created_by: string | null
  updated_by: string | null
  exports: string[]
  created_at: string
  updated_at: string
}

export interface ReportExport {
  id: string
  organization: string
  run: string
  run_status: string
  definition_name: string | null
  format: ReportExportFormat
  file: string | null
  size: number | null
  created_by: string | null
  updated_by: string | null
  created_at: string
  updated_at: string
}

export interface DashboardWidget {
  id: string
  organization: string
  title: string
  widget_type: DashboardWidgetType
  config: Record<string, unknown>
  position: number
  is_visible: boolean
  created_by: string | null
  updated_by: string | null
  created_at: string
  updated_at: string
}

/** Aggregated dataset returned by /report-data/<type>/ and preview. */
export interface ReportDataset {
  report_type?: ReportType
  period?: { from: string; to: string }
  [key: string]: unknown
}

export const reportsApi = {
  definitions: {
    list: (params?: ListParams) => get<Paginated<ReportDefinition>>('/report-definitions/', params),
    get: (id: string) => get<ReportDefinition>(`/report-definitions/${id}/`),
    create: (data: Partial<ReportDefinition>) =>
      post<ReportDefinition>('/report-definitions/', data),
    update: (id: string, data: Partial<ReportDefinition>) =>
      patch<ReportDefinition>(`/report-definitions/${id}/`, data),
    remove: (id: string) => del(`/report-definitions/${id}/`),
    runNow: (id: string, data?: { params?: Record<string, unknown> }) =>
      post<{ queued: boolean; run_id: string }>(`/report-definitions/${id}/run-now/`, data),
    toggleSchedule: (id: string, data?: { enabled?: boolean }) =>
      post<ReportDefinition>(`/report-definitions/${id}/toggle-schedule/`, data),
    preview: (id: string, data?: { params?: Record<string, unknown> }) =>
      get<{ preview: ReportDataset; report_type: ReportType }>(
        `/report-definitions/${id}/preview/`,
        data,
      ),
  },
  runs: {
    list: (params?: ListParams) => get<Paginated<ReportRun>>('/report-runs/', params),
    get: (id: string) => get<ReportRun>(`/report-runs/${id}/`),
    retry: (id: string) => post<ReportRun>(`/report-runs/${id}/retry/`),
  },
  exports: {
    list: (params?: ListParams) => get<Paginated<ReportExport>>('/report-exports/', params),
    get: (id: string) => get<ReportExport>(`/report-exports/${id}/`),
    // NOTE: the http helper parses JSON responses, so binary streaming is not
    // supported yet; the page falls back to opening the URL directly.
    download: (id: string) => get<unknown>(`/report-exports/${id}/download/`),
  },
  widgets: {
    list: (params?: ListParams) => get<Paginated<DashboardWidget>>('/dashboard-widgets/', params),
    get: (id: string) => get<DashboardWidget>(`/dashboard-widgets/${id}/`),
    create: (data: Partial<DashboardWidget>) =>
      post<DashboardWidget>('/dashboard-widgets/', data),
    update: (id: string, data: Partial<DashboardWidget>) =>
      patch<DashboardWidget>(`/dashboard-widgets/${id}/`, data),
    remove: (id: string) => del(`/dashboard-widgets/${id}/`),
    reorder: (data: { ids: string[] }) =>
      post<DashboardWidget[]>('/dashboard-widgets/reorder/', data),
  },
  data: (reportType: ReportType, params?: ListParams) =>
    get<ReportDataset>(`/report-data/${reportType}/`, params),
}
