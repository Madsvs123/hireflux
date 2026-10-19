import { del, get, patch, post } from './http'
import type { ListParams, Paginated } from './types'

// ---------------------------------------------------------------------------
// Onboarding domain types (mirrors apps/onboarding serializers)
// ---------------------------------------------------------------------------

export interface OnboardingTaskDefinition {
  id: string
  template: string
  title: string
  description: string
  owner_role: string
  due_offset_days: number
  required: boolean
  order: number
  organization: string
  created_by: string | null
  updated_by: string | null
  created_at: string
  updated_at: string
}

export interface OnboardingTemplate {
  id: string
  name: string
  description: string
  is_active: boolean
  config: Record<string, unknown>
  task_definitions: OnboardingTaskDefinition[]
  organization: string
  created_by: string | null
  updated_by: string | null
  created_at: string
  updated_at: string
}

export type OnboardingPlanStatus = 'draft' | 'active' | 'completed' | 'cancelled'

export interface OnboardingPlanProgress {
  status: string
  tasks: Record<string, number>
  documents: Record<string, number>
  task_completion_pct: number
}

export interface OnboardingPlan {
  id: string
  candidate: string
  candidate_name: string
  candidate_email: string
  offer: string | null
  offer_title: string | null
  template: string | null
  template_name: string | null
  status: OnboardingPlanStatus
  start_date: string | null
  progress: OnboardingPlanProgress
  organization: string
  created_by: string | null
  updated_by: string | null
  created_at: string
  updated_at: string
}

export type OnboardingPlanTaskStatus = 'pending' | 'in_progress' | 'completed' | 'blocked'

export interface OnboardingPlanTask {
  id: string
  plan: string
  plan_candidate: string
  definition: string | null
  definition_title: string | null
  title: string
  status: OnboardingPlanTaskStatus
  due_date: string | null
  completed_at: string | null
  completed_by: string | null
  completed_by_name: string | null
  notes: string
  organization: string
  created_by: string | null
  updated_by: string | null
  created_at: string
  updated_at: string
}

export type OnboardingDocumentStatus = 'missing' | 'uploaded' | 'approved' | 'rejected'

export interface OnboardingDocument {
  id: string
  plan: string
  plan_candidate: string
  name: string
  file: string | null
  status: OnboardingDocumentStatus
  uploaded_by: string | null
  uploaded_by_name: string | null
  approved_by: string | null
  approved_by_name: string | null
  organization: string
  created_by: string | null
  updated_by: string | null
  created_at: string
  updated_at: string
}

// ---------------------------------------------------------------------------
// API client
// ---------------------------------------------------------------------------

export const onboardingApi = {
  // Templates
  listTemplates: (params?: ListParams) =>
    get<Paginated<OnboardingTemplate>>('/onboarding-templates/', params),
  getTemplate: (id: string) => get<OnboardingTemplate>(`/onboarding-templates/${id}/`),
  createTemplate: (data: Partial<OnboardingTemplate>) =>
    post<OnboardingTemplate>('/onboarding-templates/', data),
  updateTemplate: (id: string, data: Partial<OnboardingTemplate>) =>
    patch<OnboardingTemplate>(`/onboarding-templates/${id}/`, data),
  removeTemplate: (id: string) => del(`/onboarding-templates/${id}/`),
  duplicateTemplate: (id: string) =>
    post<OnboardingTemplate>(`/onboarding-templates/${id}/duplicate/`),

  // Task definitions
  listTaskDefinitions: (params?: ListParams) =>
    get<Paginated<OnboardingTaskDefinition>>('/onboarding-task-definitions/', params),
  createTaskDefinition: (data: Partial<OnboardingTaskDefinition>) =>
    post<OnboardingTaskDefinition>('/onboarding-task-definitions/', data),
  updateTaskDefinition: (id: string, data: Partial<OnboardingTaskDefinition>) =>
    patch<OnboardingTaskDefinition>(`/onboarding-task-definitions/${id}/`, data),
  removeTaskDefinition: (id: string) => del(`/onboarding-task-definitions/${id}/`),

  // Plans
  listPlans: (params?: ListParams) =>
    get<Paginated<OnboardingPlan>>('/onboarding-plans/', params),
  getPlan: (id: string) => get<OnboardingPlan>(`/onboarding-plans/${id}/`),
  createPlan: (data: {
    candidate_id: string
    offer_id?: string | null
    template_id?: string | null
    start_date?: string | null
  }) => post<OnboardingPlan>('/onboarding-plans/', data),
  updatePlan: (id: string, data: Partial<OnboardingPlan>) =>
    patch<OnboardingPlan>(`/onboarding-plans/${id}/`, data),
  removePlan: (id: string) => del(`/onboarding-plans/${id}/`),
  startPlan: (id: string, data?: { template_id?: string }) =>
    post<OnboardingPlan>(`/onboarding-plans/${id}/start/`, data),
  planProgress: (id: string) =>
    get<OnboardingPlanProgress>(`/onboarding-plans/${id}/progress/`),
  cancelPlan: (id: string) => post<OnboardingPlan>(`/onboarding-plans/${id}/cancel/`),
  sendPlanReminders: (id: string) =>
    post<{ queued: boolean; plan_id: string }>(`/onboarding-plans/${id}/send-reminders/`),

  // Plan tasks
  listPlanTasks: (params?: ListParams) =>
    get<Paginated<OnboardingPlanTask>>('/onboarding-plan-tasks/', params),
  createPlanTask: (data: {
    plan: string
    definition_id?: string | null
    title?: string
    due_date?: string | null
  }) => post<OnboardingPlanTask>('/onboarding-plan-tasks/', data),
  updatePlanTask: (id: string, data: Partial<OnboardingPlanTask>) =>
    patch<OnboardingPlanTask>(`/onboarding-plan-tasks/${id}/`, data),
  removePlanTask: (id: string) => del(`/onboarding-plan-tasks/${id}/`),
  completePlanTask: (id: string) =>
    post<OnboardingPlanTask>(`/onboarding-plan-tasks/${id}/complete/`),
  reopenPlanTask: (id: string) =>
    post<OnboardingPlanTask>(`/onboarding-plan-tasks/${id}/reopen/`),
  blockPlanTask: (id: string, data?: { note?: string }) =>
    post<OnboardingPlanTask>(`/onboarding-plan-tasks/${id}/block/`, data),

  // Documents (create accepts FormData for file uploads)
  listDocuments: (params?: ListParams) =>
    get<Paginated<OnboardingDocument>>('/onboarding-document/', params),
  createDocument: (form: FormData) => post<OnboardingDocument>('/onboarding-documents/', form),
  updateDocument: (id: string, data: Partial<OnboardingDocument>) =>
    patch<OnboardingDocument>(`/onboarding-documents/${id}/`, data),
  removeDocument: (id: string) => del(`/onboarding-documents/${id}/`),
  approveDocument: (id: string) =>
    post<OnboardingDocument>(`/onboarding-documents/${id}/approve/`),
  rejectDocument: (id: string) =>
    post<OnboardingDocument>(`/onboarding-documents/${id}/reject/`),
}
