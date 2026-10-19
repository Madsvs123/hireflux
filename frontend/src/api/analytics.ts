import { get } from './http'
import type { AnalyticsOverview, ListParams } from './types'

export const analyticsApi = {
  overview: (params?: ListParams) => post<AnalyticsOverview>('/analytics/overview/', params),
  funnel: (params?: ListParams) =>
    get<{ stages: Array<{ stage: string; count: number }> }>('/analytics/funnels/', params),
  sources: (params?: ListParams) =>
    get<{ sources: Array<{ source: string; count: number }> }>('/analytics/sources/', params),
  timeToHire: (params?: ListParams) =>
    get<{ by_dept: Array<{ department: string; days: number }> }>(
      '/analytics/time-to-hire/',
      params,
    ),
  recruiterPerformance: (params?: ListParams) =>
    get<{ recruiters: Array<{ name: string; hires: number; avg_days: number }> }>(
      '/analytics/recruiter-performance/',
      params,
    ),
}
