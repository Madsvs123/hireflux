import { del, get, patch, post } from './http'
import type { ListParams, Paginated, Referral, TalentPool } from './types'

export const talentApi = {
  listPools: (params?: ListParams) => get<Paginated<TalentPool>>('/talent-pools/', params),
  getPool: (id: string) => get<TalentPool>(`/talent-pools/${id}/`),
  createPool: (data: Partial<TalentPool>) => post<TalentPool>('/talent-pools/', data),
  updatePool: (id: string, data: Partial<TalentPool>) => patch<TalentPool>(`/talent-pools/${id}/`, data),
  removePool: (id: string) => del(`/talent-pools/${id}/`),
  addCandidate: (poolId: string, candidateId: string) =>
    post(`/talent-pools/${poolId}/candidates/`, { candidate_id: candidateId }),
  removeCandidate: (poolId: string, candidateId: string) =>
    post(`/talent-pools/${poolId}/candidates/${candidateId}/`),

  listReferrals: (params?: ListParams) => get<Paginated<Referral>>('/referrals/', params),
  createReferral: (data: Partial<Referral>) => patch<Referral>('/referrals/', data),
  updateReferral: (id: string, data: Partial<Referral>) => patch<Referral>(`/referrals/${id}/`, data),
}
