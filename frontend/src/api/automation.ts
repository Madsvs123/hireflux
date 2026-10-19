import { del, get, patch, post } from './http'
import type { ListParams, Paginated } from './types'

export type AutomationTrigger =
  | 'stage_change'
  | 'job_published'
  | 'candidate_created'
  | 'offer_accepted'
  | 'assessment_completed'
  | 'date'

export interface AutomationAction {
  type: 'send_email' | 'notify' | 'create_task' | 'move_stage' | 'update_field' | 'send_webhook'
  params?: Record<string, unknown>
}

export interface AutomationCondition {
  field: string
  operator: string
  value: unknown
  [key: string]: unknown
}

export type AutomationConditions = AutomationCondition[] | { operator: 'and' | 'or'; rules: AutomationCondition[] }

export interface AutomationRule {
  id: string
  name: string
  description: string
  trigger: AutomationTrigger
  trigger_config: Record<string, unknown>
  conditions: AutomationConditions
  actions: AutomationAction[]
  is_active: boolean
  run_count: number
  last_run_at: string | null
  created_by: string | null
  updated_by: string | null
  created_at: string
  updated_at: string
}

export type RuleExecutionStatus = 'matched' | 'skipped' | 'failed'

export interface RuleExecution {
  id: string
  rule: string
  rule_name: string
  trigger_event: string
  entity_type: string
  entity_id: string
  status: RuleExecutionStatus
  conditions_evaluated: Record<string, unknown>
  executed_at: string
  error: string
  created_at: string
  updated_at: string
}

export type RuleActionLogStatus = 'success' | 'skipped' | 'failed'

export interface RuleActionLog {
  id: string
  execution: string
  action_index: number
  action_type: string
  status: RuleActionLogStatus
  detail: Record<string, unknown>
  executed_at: string | null
  created_at: string
  updated_at: string
}

export interface TestRunResult {
  rule_id: string
  rule_name: string
  trigger_event: string
  conditions_evaluated: Record<string, unknown>
  matched: boolean
  actions: Array<{
    index: number
    type: string
    would_run: boolean
    params?: Record<string, unknown>
  }>
  skipped?: string
}

export interface AutomationEventInfo {
  triggers: string[]
  actions: string[]
  entity_types: string[]
}

export interface FireTriggerResult {
  results: Array<{ rule_id: string; queued?: boolean; status?: string; execution_id?: string }>
}

export const automationRulesApi = {
  list: (params?: ListParams) => get<Paginated<AutomationRule>>('/automation-rules/', params),
  get: (id: string) => get<AutomationRule>(`/automation-rules/${id}/`),
  create: (data: Partial<AutomationRule>) => post<AutomationRule>('/automation-rules/', data),
  update: (id: string, data: Partial<AutomationRule>) =>
    patch<AutomationRule>(`/automation-rules/${id}/`, data),
  remove: (id: string) => del(`/automation-rules/${id}/`),

  enable: (id: string) => post<AutomationRule>(`/automation-rules/${id}/enable/`),
  disable: (id: string) => post<AutomationRule>(`/automation-rules/${id}/disable/`),
  testRun: (id: string, data?: { entity_type?: string; entity_id?: string }) =>
    post<TestRunResult>(`/automation-rules/${id}/test-run/`, data),
  duplicate: (id: string) => post<AutomationRule>(`/automation-rules/${id}/duplicate/`),
}

export const ruleExecutionsApi = {
  list: (params?: ListParams) => get<Paginated<RuleExecution>>('/rule-executions/', params),
  get: (id: string) => get<RuleExecution>(`/rule-executions/${id}/`),

  retry: (id: string) => post<Record<string, unknown>>(`/rule-executions/${id}/retry/`),
}

export const ruleActionLogsApi = {
  // Filter by execution via params: { execution: <id> }
  list: (params?: ListParams) => get<Paginated<RuleActionLog>>('/rule-action-logs/', params),
  get: (id: string) => get<RuleActionLog>(`/rule-action-logs/${id}/`),
}

export const automationEventsApi = {
  info: () => get<AutomationEventInfo>('/automation-events/'),
  fire: (data: {
    event: string
    entity_type?: string
    entity_id?: string
    async_mode?: boolean
  }) => post<FireTriggerResult>('/automation-events/', data),
}
