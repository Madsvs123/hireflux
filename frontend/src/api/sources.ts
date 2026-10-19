import { del, get, patch, post } from './http'
import type { ListParams, Paginated } from './types'

export type SourceChannelType = 'job_board' | 'social' | 'agency' | 'referral' | 'direct' | 'other'

export type SourcingCampaignStatus = 'draft' | 'active' | 'paused' | 'completed'

export type CampaignRecipientStatus = 'queued' | 'sent' | 'opened' | 'replied' | 'opted_out'

export interface SourceChannel {
  id: string
  organization: string
  name: string
  channel_type: SourceChannelType
  url: string
  cost_per_post: string | null
  is_active: boolean
  notes: string
  created_by: string | null
  updated_by: string | null
  created_at: string
  updated_at: string
}

export interface SourcingCampaign {
  id: string
  organization: string
  name: string
  channel: string
  channel_name: string
  job: string | null
  job_title: string | null
  talent_pool: string | null
  talent_pool_name: string | null
  goal: string
  status: SourcingCampaignStatus
  started_at: string | null
  ended_at: string | null
  budget: string | null
  recipient_count: number
  created_by: string | null
  updated_by: string | null
  created_at: string
  updated_at: string
}

export interface CampaignRecipient {
  id: string
  organization: string
  campaign: string
  campaign_name: string
  candidate: string | null
  candidate_name: string | null
  email: string
  status: CampaignRecipientStatus
  sent_at: string | null
  created_by: string | null
  updated_by: string | null
  created_at: string
  updated_at: string
}

export interface CandidateSourceAttribution {
  id: string
  organization: string
  candidate: string
  candidate_name: string
  channel: string
  channel_name: string
  campaign: string | null
  campaign_name: string | null
  source_detail: string
  attribution_date: string
  utm_source: string
  utm_medium: string
  utm_campaign: string
  created_by: string | null
  updated_by: string | null
  created_at: string
  updated_at: string
}

export interface ChannelStatRow {
  channel_id: string
  channel: string
  channel_type: SourceChannelType
  is_active: boolean
  cost_per_post: string | null
  campaigns: number
  active_campaigns: number
  recipients: number
  attributions: number
}

export interface AttributionStats {
  period: { from: string; to: string }
  total_attributions: number
  channels: Array<{
    channel: string
    channel_type: SourceChannelType
    attributions: number
    campaigns: number
  }>
}

export const sourcesApi = {
  channels: {
    list: (params?: ListParams) => get<Paginated<SourceChannel>>('/source-channels/', params),
    get: (id: string) => get<SourceChannel>(`/source-channels/${id}/`),
    create: (data: Partial<SourceChannel>) => post<SourceChannel>('/source-channels/', data),
    update: (id: string, data: Partial<SourceChannel>) =>
      patch<SourceChannel>(`/source-channels/${id}/`, data),
    remove: (id: string) => del(`/source-channels/${id}/`),
    stats: () => get<ChannelStatRow[]>('/source-channels/stats/'),
  },
  campaigns: {
    list: (params?: ListParams) =>
      get<Paginated<SourcingCampaign>>('/sourcing-campaigns/', params),
    get: (id: string) => get<SourcingCampaign>(`/sourcing-campaigns/${id}/`),
    create: (data: Partial<SourcingCampaign>) =>
      post<SourcingCampaign>('/sourcing-campaigns/', data),
    update: (id: string, data: Partial<SourcingCampaign>) =>
      patch<SourcingCampaign>(`/sourcing-campaigns/${id}/`, data),
    remove: (id: string) => del(`/sourcing-campaigns/${id}/`),
    launch: (id: string) => post<SourcingCampaign>(`/sourcing-campaigns/${id}/launch/`),
    pause: (id: string) => post<SourcingCampaign>(`/sourcing-campaigns/${id}/pause/`),
    resume: (id: string) => post<SourcingCampaign>(`/sourcing-campaigns/${id}/resume/`),
    complete: (id: string) => post<SourcingCampaign>(`/sourcing-campaigns/${id}/complete/`),
    syncRecipients: (id: string) =>
      post<{ created: number; recipient_ids: string[] }>(
        `/sourcing-campaigns/${id}/sync-recipients/`,
      ),
  },
  recipients: {
    list: (params?: ListParams) => get<Paginated<CampaignRecipient>>('/campaign-recipients/', params),
    get: (id: string) => get<CampaignRecipient>(`/campaign-recipients/${id}/`),
    create: (data: Partial<CampaignRecipient>) =>
      post<CampaignRecipient>('/campaign-recipients/', data),
    update: (id: string, data: Partial<CampaignRecipient>) =>
      patch<CampaignRecipient>(`/campaign-recipients/${id}/`, data),
    remove: (id: string) => del(`/campaign-recipients/${id}/`),
    send: (id: string) => post<CampaignRecipient>(`/campaign-recipients/${id}/send/`),
    resend: (id: string) => post<CampaignRecipient>(`/campaign-recipients/${id}/resend/`),
    sendAll: (data: { campaign: string; force?: boolean }) =>
      post<{ queued: boolean; campaign_id: string; pending: number }>(
        '/campaign-recipients/send-all/',
        data,
      ),
  },
  attributions: {
    list: (params?: ListParams) =>
      get<Paginated<CandidateSourceAttribution>>('/source-attributions/', params),
    get: (id: string) => get<CandidateSourceAttribution>(`/source-attributions/${id}/`),
    stats: (params?: ListParams) =>
      get<AttributionStats>('/source-attributions/stats/', params),
  },
}
