import { get, patch, post } from './http'
import type { ListParams, Notification, Paginated, SearchResults } from './types'

export const coreApi = {
  health: () => get<{ status: string }>('/health/', undefined),
  search: (q: string, params?: ListParams) =>
    get<SearchResults>('/search', { ...params, q }),
  listNotifications: (params?: ListParams) =>
    get<Paginated<Notification>>('/notifications/', params),
  markNotificationRead: (id: string) => put<Notification>(`/notifications/${id}/`, { is_read: true }),
  markAllNotificationsRead: () => post('/notifications/mark_all_read/', {}),
  listAuditLogs: (params?: ListParams) => get<Paginated<Record<string, unknown>>>('/audit-logs/', params),
}
