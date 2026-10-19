import { del, get, patch, post } from './http'
import type { ListParams, Paginated } from './types'

export type CalendarProvider = 'google' | 'outlook'

export interface CalendarAccount {
  id: string
  user: string
  provider: CalendarProvider
  email: string
  calendar_id: string
  is_primary: boolean
  sync_enabled: boolean
  last_synced_at: string | null
  created_by: string | null
  updated_by: string | null
  created_at: string
  updated_at: string
}

export interface AvailabilityRule {
  id: string
  user: string
  title: string
  days_of_week: number[]
  start_time: string
  end_time: string
  timezone: string
  buffer_minutes: number
  is_active: boolean
  created_by: string | null
  updated_by: string | null
  created_at: string
  updated_at: string
}

export type InterviewSlotStatus = 'available' | 'booked' | 'held' | 'expired'

export interface InterviewSlot {
  id: string
  availability_rule: string | null
  user: string
  start_at: string
  end_at: string
  status: InterviewSlotStatus
  held_until: string | null
  booking_request: string | null
  created_by: string | null
  updated_by: string | null
  created_at: string
  updated_at: string
}

export interface SchedulingLink {
  id: string
  name: string
  slug: string
  owner: string
  job: string | null
  duration_minutes: number
  start_date: string | null
  end_date: string | null
  availability_rules: string[]
  timezone: string
  is_active: boolean
  booking_count: number
  created_by: string | null
  updated_by: string | null
  created_at: string
  updated_at: string
}

export type BookingRequestStatus = 'pending' | 'confirmed' | 'cancelled' | 'declined'

export interface BookingRequest {
  id: string
  scheduling_link: string
  link_name: string
  candidate: string | null
  candidate_name: string
  name: string
  email: string
  requested_slot_start: string
  status: BookingRequestStatus
  confirmation_token: string
  confirmed_at: string | null
  meeting_url: string
  notes: string
  created_by: string | null
  updated_by: string | null
  created_at: string
  updated_at: string
}

export interface BulkGenerateResult {
  created: number
  skipped: number
  [key: string]: unknown
}

export interface PublicSchedulingPayload {
  slug: string
  name: string
  owner: { id: string; name: string }
  job_title: string | null
  duration_minutes: number
  timezone: string
  slots: Array<{ start_at: string; end_at: string }>
}

export interface PublicBookingResponse {
  status: string
  confirmation_token: string
  requested_slot_start: string
  expires_at: string
}

export const calendarAccountsApi = {
  list: (params?: ListParams) => get<Paginated<CalendarAccount>>('/calendar-accounts/', params),
  get: (id: string) => get<CalendarAccount>(`/calendar-accounts/${id}/`),
  create: (data: Partial<CalendarAccount>) => post<CalendarAccount>('/calendar-accounts/', data),
  update: (id: string, data: Partial<CalendarAccount>) =>
    patch<CalendarAccount>(`/calendar-accounts/${id}/`, data),
  remove: (id: string) => del(`/calendar-accounts/${id}/`),

  connect: (id: string) => post<Record<string, unknown>>(`/calendar-accounts/${id}/connect/`),
  sync: (id: string) => post<{ queued: boolean; account_id: string }>(`/calendar-accounts/${id}/sync/`),
  disconnect: (id: string) => post<CalendarAccount>(`/calendar-accounts/${id}/disconnect/`),
}

export const availabilityRulesApi = {
  list: (params?: ListParams) => get<Paginated<AvailabilityRule>>('/availability-rules/', params),
  get: (id: string) => get<AvailabilityRule>(`/availability-rules/${id}/`),
  create: (data: Partial<AvailabilityRule>) => post<AvailabilityRule>('/availability-rules/', data),
  update: (id: string, data: Partial<AvailabilityRule>) =>
    patch<AvailabilityRule>(`/availability-rules/${id}/`, data),
  remove: (id: string) => del(`/availability-rules/${id}/`),
}

export const interviewSlotsApi = {
  // Read-only list; supports start_date / end_date / user / status filters
  list: (params?: ListParams) => get<Paginated<InterviewSlot>>('/interview-slots/', params),
  get: (id: string) => get<InterviewSlot>(`/interview-slots/${id}/`),

  bulkGenerate: (data: {
    user: string
    start_date: string
    end_date: string
    duration_minutes?: number
    rule_ids?: string[]
  }) => post<BulkGenerateResult>('/interview-slots/bulk-generate/', data),
  hold: (id: string, data: { hold_minutes?: number }) =>
    post<InterviewSlot>(`/interview-slots/${id}/hold/`, data),
  release: (id: string) => post<InterviewSlot>(`/interview-slots/${id}/release/`),
  cancelSlot: (id: string) => post<InterviewSlot>(`/interview-slots/${id}/cancel/`),
}

export const schedulingLinksApi = {
  list: (params?: ListParams) => get<Paginated<SchedulingLink>>('/scheduling-links/', params),
  get: (id: string) => get<SchedulingLink>(`/scheduling-links/${id}/`),
  create: (data: Partial<SchedulingLink>) => post<SchedulingLink>('/scheduling-links/', data),
  update: (id: string, data: Partial<SchedulingLink>) =>
    patch<SchedulingLink>(`/scheduling-links/${id}/`, data),
  remove: (id: string) => del(`/scheduling-links/${id}/`),

  duplicate: (id: string) => post<SchedulingLink>(`/scheduling-links/duplicate/${id}/`),
}

export const bookingRequestsApi = {
  list: (params?: ListParams) => get<Paginated<BookingRequest>>('/booking-requests/', params),
  get: (id: string) => get<BookingRequest>(`/booking-requests/${id}/`),
  create: (data: Partial<BookingRequest>) => post<BookingRequest>('/booking-requests/', data),
  update: (id: string, data: Partial<BookingRequest>) =>
    patch<BookingRequest>(`/booking-requests/${id}/`, data),
  remove: (id: string) => del(`/booking-requests/${id}/`),

  confirm: (id: string) => patch<BookingRequest>(`/booking-requests/${id}/confirm/`),
  cancelBooking: (id: string) => post<BookingRequest>(`/booking-requests/${id}/cancel/`),
  decline: (id: string) => post<BookingRequest>(`/booking-requests/${id}/decline/`),
}

export const publicSchedulingApi = {
  // Anonymous endpoints (auth headers are harmless if present)
  slots: (slug: string) => get<PublicSchedulingPayload>(`/public/scheduling/${slug}/`),
  book: (slug: string, data: { name: string; email: string; requested_slot_start: string; notes?: string }) =>
    post<PublicBookingResponse>(`/public/scheduling/${slug}/book/`, data),
}
