import { del, get, patch, post } from './http'
import type { ListParams, Offer, Paginated } from './types'

export const offersApi = {
  list: (params?: ListParams) => get<Paginated<Offer>>('/offers/', params),
  get: (id: string) => get<Offer>(`/offers/${id}/`),
  create: (data: Partial<Offer>) => post<Offer>('/offers/', data),
  update: (id: string, data: Partial<Offer>) => patch<Offer>(`/offers/${id}/`, data),
  remove: (id: string) => del(`/offers/${id}/`),
  submitApproval: (id: string) => post<Offer>(`/offers/${id}/submit-approval/`, {}),
  approve: (id: string, data?: { comment?: string }) => post<Offer>(`/offers/${id}/approve/`, data),
  reject: (id: string, data?: { comment?: string }) => post<Record<string, unknown>>(`/offers/${id}/reject/`, data),
  send: (id: string) => post<Offer>(`/offers/${id}/send/`, {}),
  withdraw: (id: string) => del(`/offers/${id}/withdraw/`),
}
