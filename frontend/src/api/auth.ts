import { del, get, post, patch } from './http'
import type { LoginResponse, RegisterPayload, User, Invitation, Membership, Role, Paginated, ListParams } from './types'

export const authApi = {
  login: (email: string, password: string) =>
    post<LoginResponse>('/auth/login/', { email, password }, { skipAuth: true, skipOrg: true }),

  refresh: (refresh: string) =>
    post<{ access: string }>('/auth/refresh/', { token: refresh }, { skipAuth: true, skipOrg: true }),

  logout: (refresh?: string) => post<void>('/auth/logout', { refresh }),

  register: (payload: RegisterPayload) =>
    post<{ user: User; organization: { id: string; name: string }; membership: Membership }>(
      '/auth/register/',
      payload,
      { skipAuth: true, skipOrg: true },
    ),

  me: () => get<User>('/auth/me/'),

  updateMe: (data: Partial<User>) => post<User>('/auth/me/', data),

  forgotPassword: (email: string) =>
    post<{ detail: string }>('/auth/forgot-password/', { email }, { skipAuth: true, skipOrg: true }),

  resetPassword: (token: string, password: string) =>
    post<{ detail: string }>('/auth/reset-password/', { token, password }, { skipAuth: true, skipOrg: true }),

  verifyEmail: (token: string) =>
    post<{ detail: string }>('/auth/verify_email/', { token }, { skipAuth: true, skipOrg: true }),

  acceptInvite: (data: {
    token: string
    password?: string
    first_name?: string
    last_name?: string
  }) =>
    post<LoginResponse>('/auth/accept-invite/', data, { skipAuth: true, skipOrg: true }),
}

export const rolesApi = {
  list: (params?: ListParams) => get<Paginated<Role>>('/roles/', params),
  get: (id: string) => get<Role>(`/roles/${id}/`,
  create: (data: Partial<Role>) => post<Role>('/roles/', data),
  update: (id: string, data: Partial<Role>) => patch<Role>(`/roles/${id}/`, data),
  remove: (id: string) => del(`/roles/${id}/`),
}

export const membersApi = {
  list: (params?: ListParams) => get<Paginated<Membership>>('/members/', params),
  get: (id: string) => get<Membership>(`/members/${id}/`),
  update: (id: string, data: { role_id?: string | null; title?: string; is_active?: boolean }) =>
    patch<Membership>(`/members/${id}/`, data),
}

export const invitationsApi = {
  list: (params?: ListParams) => get<Paginated<Invitation>>('/invitations/', params),
  create: (data: { email: string; role?: string | null; message?: string }) =>
    post<Invitation>('/invitations/', data),
  remove: (id: string) => del(`/invitations/${id}/`),
}
