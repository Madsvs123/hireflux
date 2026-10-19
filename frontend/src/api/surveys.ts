import { del, get, patch, post } from './http'
import type { ListParams, Paginated } from './types'

export type SurveyType = 'candidate_experience' | 'onboarding' | 'eeo' | 'internal'

export type SurveyQuestionType = 'rating' | 'text' | 'choice' | 'bool'

export type SurveyInstanceStatus = 'draft' | 'sent' | 'partially_completed' | 'completed' | 'expired'

export type SurveyInvitationStatus = 'queued' | 'sent' | 'opened' | 'completed'

export interface SurveyTemplate {
  id: string
  organization: string
  name: string
  description: string
  survey_type: SurveyType
  is_active: boolean
  thank_you_message: string
  question_count: number
  created_by: string | null
  updated_by: string | null
  created_at: string
  updated_at: string
}

export interface SurveyQuestion {
  id: string
  organization: string
  template: string
  template_name: string
  question_text: string
  question_type: SurveyQuestionType
  options: string[]
  is_required: boolean
  order: number
  created_by: string | null
  updated_by: string | null
  created_at: string
  updated_at: string
}

export interface SurveyInstance {
  id: string
  organization: string
  template: string
  template_name: string
  candidate: string | null
  candidate_name: string | null
  job: string | null
  job_title: string | null
  status: SurveyInstanceStatus
  token: string
  sent_at: string | null
  completed_at: string | null
  anonymous: boolean
  response_count: number
  invitation_count: number
  created_by: string | null
  updated_by: string | null
  created_at: string
  updated_at: string
}

export interface SurveyResponse {
  id: string
  organization: string
  instance: string
  question: string
  question_text: string
  question_type: SurveyQuestionType
  answer: unknown
  answered_at: string
  created_by: string | null
  updated_by: string | null
  created_at: string
  updated_at: string
}

export interface SurveyInvitation {
  id: string
  organization: string
  instance: string
  email: string
  status: SurveyInvitationStatus
  sent_at: string | null
  completed_at: string | null
  created_by: string | null
  updated_by: string | null
  created_at: string
  updated_at: string
}

export interface PublicSurveyDetail {
  instance_id: string
  survey_name: string
  survey_type: SurveyType
  thank_you_message: string
  status: SurveyInstanceStatus
  anonymous: boolean
  questions: Array<{
    id: string
    question_text: string
    question_type: SurveyQuestionType
    options: string[]
    is_required: boolean
    order: number
  }>
}

export interface SurveyAnalytics {
  template_id: string
  template_name: string
  survey_type: SurveyType
  total_instances: number
  sent_instances: number
  completed_instances: number
  started_instances: number
  response_rate: number
  completion_rate: number
  questions: Array<{
    question_id: string
    question_text: string
    question_type: SurveyQuestionType
    response_count: number
    breakdown: Record<string, unknown>
  }>
}

export const surveysApi = {
  templates: {
    list: (params?: ListParams) => get<Paginated<SurveyTemplate>>('/survey-templates/', params),
    get: (id: string) => get<SurveyTemplate>(`/survey-templates/${id}/`),
    create: (data: Partial<SurveyTemplate>) => post<SurveyTemplate>('/survey-templates/', data),
    update: (id: string, data: Partial<SurveyTemplate>) =>
      patch<SurveyTemplate>(`/survey-templates/${id}/`, data),
    remove: (id: string) => del(`/survey-templates/${id}/`),
    duplicate: (id: string) =>
      post<SurveyTemplate>(`/survey-templates/${id}/duplicate/`, {}),
  },
  questions: {
    list: (params?: ListParams) => get<Paginated<SurveyQuestion>>('/survey-questions/', params),
    get: (id: string) => get<SurveyQuestion>(`/survey-questions/${id}/`),
    create: (data: Partial<SurveyQuestion>) => post<SurveyQuestion>('/survey-questions/', data),
    update: (id: string, data: Partial<SurveyQuestion>) =>
      patch<SurveyQuestion>(`/survey-questions/${id}/`, data),
    remove: (id: string) => del(`/survey-questions/${id}/`),
  },
  instances: {
    list: (params?: ListParams) => get<Paginated<SurveyInstance>>('/survey-instances/', params),
    get: (id: string) => get<SurveyInstance>(`/survey-instances/${id}/`),
    create: (data: Partial<SurveyInstance>) => post<SurveyInstance>('/survey-instances/', data),
    update: (id: string, data: Partial<SurveyInstance>) =>
      patch<SurveyInstance>(`/survey-instances/${id}/`, data),
    remove: (id: string) => del(`/survey-instances/${id}/`),
    send: (id: string) => post<SurveyInstance>(`/survey-instances/${id}/send/`, {}),
    sendReminder: (id: string) =>
      post<SurveyInstance>(`/survey-instances/${id}/send-reminder/`, {}),
    close: (id: string) => post<SurveyInstance>(`/survey-instances/${id}/close/`, {}),
  },
  responses: {
    list: (params?: ListParams) => get<Paginated<SurveyResponse>>('/survey-responses/', params),
    get: (id: string) => get<SurveyResponse>(`/survey-responses/${id}/`),
    submit: (data: { instance_id?: string; question_id: string; answer: unknown }) =>
      post<SurveyResponse>('/survey-responses/submit/', data),
  },
  invitations: {
    list: (params?: ListParams) => get<Paginated<SurveyInvitation>>('/survey-invitations/', params),
    get: (id: string) => get<SurveyInvitation>(`/survey-invitations/${id}/`),
    create: (data: Partial<SurveyInvitation>) =>
      post<SurveyInvitation>('/survey-invitations/', data),
    update: (id: string, data: Partial<SurveyInvitation>) =>
      patch<SurveyInvitation>(`/survey-invitations/${id}/`, data),
    remove: (id: string) => del(`/survey-invitations/${id}/`),
  },
  analytics: (templateId: string) =>
    get<SurveyAnalytics>('/survey-analytics/', { template: templateId }),
  public: {
    detail: (token: string) => get<PublicSurveyDetail>(`/public/surveys/${token}/`),
    submit: (token: string, data: { question_id: string; answer: unknown }) =>
      post<{ ok: boolean; response_id: string; instance_status: string }>(
        `/public/surveys/${token}/submit/`,
        data,
        { skipAuth: true, skipOrg: true },
      ),
  },
}
