import { del, get, patch, post } from './http'
import type {
  Department,
  HiringTeam,
  HiringTeamMember,
  ListParams,
  Office,
  Organization,
  Paginated,
} from './types'

export const organizationsApi = {
  list: (params?: ListParams) => get<Paginated<Organization>>('/organizations', params),
  get: (id: string) => get<Organization>(`/organizations/${id}/`),
  create: (data: Partial<Organization>) => post<Organization>('/organizations/', data),
  update: (id: string, data: Partial<Organization>) => patch<Organization>(`/organizations/${id}`, data),
}

export const departmentsApi = {
  list: (params?: ListParams) => get<Paginated<Department>>('/departments/', params),
  get: (id: string) => get<Department>(`/departments/${id}/`),
  create: (data: Partial<Department>) => post<Department>('/departments/', data),
  update: (id: string, data: Partial<Department>) => patch<Department>(`/departments/${id}/`, data),
  remove: (id: string) => del(`/departments/${id}/`),
}

export const officesApi = {
  list: (params?: ListParams) => get<Paginated<Office>>('/offices/', params),
  get: (id: string) => get<Office>(`/offices/${id}/`),
  create: (data: Partial<Office>) => post<Office>('/offices/', data),
  update: (id: string, data: Partial<Office>) => patch<Office>(`/offices/${id}/`, data),
  remove: (id: string) => del(`/offices/${id}/`),
}

export const hiringTeamsApi = {
  list: (params?: ListParams) => get<Paginated<HiringTeam>>('/hiring-teams/', params),
  get: (id: string) => get<HiringTeam>(`/hiring-teams/${id}/`),
  create: (data: Partial<HiringTeam>) => post<HiringTeam>('/hiring-teams/', data),
  update: (id: string, data: Partial<HiringTeam>) => patch<HiringTeam>(`/hiring-teams/${id}/`, data),
  remove: (id: string) => del(`/hiring-team/${id}/`),
}

export const hiringTeamMembersApi = {
  list: (params?: ListParams) => get<Paginated<HiringTeamMember>>('/hiring-team-members/', params),
  create: (data: Partial<HiringTeamMember>) => post<HiringTeamMember>('/hiring-team-members/', data),
  update: (id: string, data: Partial<HiringTeamMember>) =>
    patch<HiringTeamMember>(`/hiring-team-members/${id}/`, data),
  remove: (id: string) => del(`/hiring-team-members/${id}/`),
}
