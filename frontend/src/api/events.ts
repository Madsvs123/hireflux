import { del, get, patch, post } from './http'
import type { ListParams, Paginated } from './types'

export type RecruitingEventType = 'career_fair' | 'webinar' | 'campus' | 'onsite' | 'other'
export type RecruitingEventStatus = 'draft' | 'scheduled' | 'ongoing' | 'completed' | 'cancelled'

export interface RecruitingEvent {
  id: string
  name: string
  event_type: RecruitingEventType
  description: string
  location: string
  is_virtual: boolean
  start_at: string
  end_at: string | null
  capacity: number | null
  status: RecruitingEventStatus
  cover_image: string | null
  session_count: number
  registration_count: number
  created_by: string | null
  updated_by: string | null
  created_at: string
  updated_at: string
}

export interface EventSession {
  id: string
  event: string
  title: string
  speaker: string
  start_at: string
  end_at: string | null
  description: string
  room: string
  created_by: string | null
  updated_by: string | null
  created_at: string
  updated_at: string
}

export type EventRegistrationStatus =
  | 'registered'
  | 'attended'
  | 'no_show'
  | 'cancelled'
  | 'waitlisted'

export interface EventRegistration {
  id: string
  event: string
  event_name: string
  candidate: string | null
  candidate_name: string
  email: string
  first_name: string
  last_name: string
  status: EventRegistrationStatus
  registered_at: string
  checked_in_at: string | null
  created_by: string | null
  updated_by: string | null
  created_at: string
  updated_at: string
}

export type EventTaskStatus = 'pending' | 'in_progress' | 'completed' | 'cancelled'

export interface EventTask {
  id: string
  event: string
  event_name: string
  title: string
  assignee: string | null
  due_at: string | null
  status: EventTaskStatus
  notes: string
  created_by: string | null
  updated_by: string | null
  created_at: string
  updated_at: string
}

export interface CheckInManyResult {
  checked_in: string[]
  skipped: Array<{ id: string; reason: string }>
  errors: Array<{ id: string; reason: string }>
}

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api/v1'

/**
 * Download the event registrations CSV. The endpoint returns a file (not JSON),
 * so this bypasses the JSON-parsing http helpers.
 */
export async function downloadRegistrationsCsv(eventId: string) {
  const headers: Record<string, string> = {}
  const token = localStorage.getItem('hf_access')
  const orgId = localStorage.getItem('hf_org_id')
  if (token) headers['Authorization'] = token
  if (orgId) headers['X-Organization-Id'] = orgId
  const res = await fetch(`${API_BASE}/events/${eventId}/export/`, { headers })
  if (!res.ok) throw new Error(`Export failed (${res.status})`)
  const blob = await res.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `event-${eventId}-registrations.csv`
  a.click()
  URL.revokeObjectURL(url)
}

export const eventsApi = {
  list: (params?: ListParams) => get<Paginated<RecruitingEvent>>('/events/', params),
  get: (id: string) => get<RecruitingEvent>(`/events/${id}/`),
  create: (data: Partial<RecruitingEvent>) => post<RecruitingEvent>('/events/', data),
  update: (id: string, data: Partial<RecruitingEvent>) =>
    patch<RecruitingEvent>(`/events/${id}/`, data),
  remove: (id: string) => del(`/events/${id}/`),

  publish: (id: string) => post<RecruitingEvent>(`/events/${id}/publish/`),
  cancel: (id: string) => post<RecruitingEvent>(`/events/${id}/cancel/`),
  complete: (id: string) => post<RecruitingEvent>(`/events/${id}/complete/`),

  // Nested sessions: list + create under an event
  listSessions: (eventId: string) => get<EventSession[]>(`/events/${eventId}/sessions/`),
  addSession: (eventId: string, data: Partial<EventSession>) =>
    post<EventSession>(`/events/${eventId}/sessions/`, data),

  // Nested registrations: paginated, filterable by status
  listRegistrations: (eventId: string, params?: ListParams) =>
    get<Paginated<EventRegistration>>(`/events/${eventId}/registrations/`, params),

  exportRegistrations: (eventId: string) => downloadRegistrationsCsv(eventId),
}

export const eventSessionsApi = {
  list: (params?: ListParams) => get<Paginated<EventSession>>('/event-sessions/', params),
  get: (id: string) => get<EventSession>(`/event-sessions/${id}/`),
  create: (data: Partial<EventSession>) => post<EventSession>('/event-sessions/', data),
  update: (id: string, data: Partial<EventSession>) =>
    patch<EventSession>(`/event-sessions/${id}/`, data),
  remove: (id: string) => del(`/event-sessions/${id}/`),
}

export const eventRegistrationsApi = {
  list: (params?: ListParams) =>
    get<Paginated<EventRegistration>>('/event-registrations/', params),
  get: (id: string) => get<EventRegistration>(`/event-registrations/${id}/`),
  create: (data: Partial<EventRegistration>) =>
    post<EventRegistration>('/event-registrations/', data),
  update: (id: string, data: Partial<EventRegistration>) =>
    patch<EventRegistration>(`/event-registrations/${id}/`, data),
  remove: (id: string) => del(`/event-registrations/${id}/`),

  checkIn: (id: string) => post<EventRegistration>(`/event-registrations/${id}/checkin/`),
  checkInMany: (registrationIds: string[]) =>
    post<CheckInManyResult>('/event-registrations/check-in-many/', { ids: registrationIds }),
  cancelRegistration: (id: string) =>
    post<EventRegistration>(`/event-registrations/${id}/cancel/`),
  waitlist: (id: string) => post<EventRegistration>(`/event-registrations/${id}/waitlist/`),
}

export const eventTasksApi = {
  list: (params?: ListParams) => get<Paginated<EventTask>>('/event-tasks/', params),
  get: (id: string) => get<EventTask>(`/event-tasks/${id}/`),
  create: (data: Partial<EventTask>) => post<EventTask>('/event-tasks/', data),
  update: (id: string, data: Partial<EventTask>) => patch<EventTask>(`/event-tasks/${id}/`, data),
  remove: (id: string) => del(`/event-tasks/${id}/`),

  complete: (id: string) => post<EventTask>(`/event-tasks/${id}/complete/`),
}
