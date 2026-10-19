import { del, get, patch, post } from './http'
import type { ListParams, Paginated } from './types'

export type IntegrationCategory = 'calendar' | 'communication' | 'hris' | 'ats' | 'other'
export type IntegrationAuthType = 'oauth2' | 'api_key' | 'none'
export type ConnectionStatus = 'connected' | 'disconnected' | 'error'
export type DeliveryStatus = 'pending' | 'success' | 'failed'

export interface IntegrationProvider {
  id: string
  key: string
  name: string
  category: IntegrationCategory
  description: string
  auth_type: IntegrationAuthType
  config_schema: Record<string, unknown>
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface IntegrationConnection {
  id: string
  provider: string
  provider_name: string
  provider_key: string
  provider_auth_type: IntegrationAuthType
  name: string
  status: ConnectionStatus
  config: Record<string, unknown>
  last_synced_at: string | null
  last_error: string
  connected_by: string | null
  created_at: string
  updated_at: string
}

export interface IntegrationConnectionInput {
  provider: string
  name: string
  credentials?: Record<string, unknown>
  config?: Record<string, unknown>
}

export interface ConnectResult {
  connected: boolean
  provider: string
  authorization_url?: string
}

export interface TestResult {
  ok: boolean
  message: string
  status: ConnectionStatus
}

export interface IntegrationConfig {
  id: string
  connection: string
  connection_name: string
  key: string
  value: unknown
  is_secret: boolean
  created_at: string
  updated_at: string
}

export interface IntegrationConfigInput {
  connection_id: string
  key: string
  value: unknown
  is_secret?: boolean
}

export interface WebhookEndpoint {
  id: string
  name: string
  url: string
  events: string[]
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface WebhookEndpointInput {
  name: string
  url: string
  events?: string[]
  is_active?: boolean
  secret?: string
}

export interface WebhookEndpointCreateResult extends WebhookEndpoint {
  /** Signing secret — returned once at creation. */
  secret: string
}

export interface RotateSecretResult {
  id: string
  secret: string
}

export interface FireEventInput {
  event: string
  endpoint_id?: string | null
  payload?: Record<string, unknown>
}

export interface FireEventResult {
  queued: number
  delivery_ids: string[]
}

export interface WebhookDelivery {
  id: string
  endpoint: string
  endpoint_name: string
  endpoint_url: string
  event: string
  payload: unknown
  status: DeliveryStatus
  request_headers: Record<string, unknown>
  response_status: number | null
  response_body: string
  attempts: number
  next_attempt_at: string | null
  created_at: string
  updated_at: string
}

export interface RetryFailedResult {
  queued: number
}

export interface ApiKey {
  id: string
  name: string
  key_prefix: string
  scopes: string[]
  is_active: boolean
  expires_at: string | null
  last_used_at: string | null
  created_at: string
  updated_at: string
}

export interface ApiKeyInput {
  name: string
  scopes?: string[]
  is_active?: boolean
  expires_at?: string | null
}

/** API key material (plaintext) is only returned on create/regenerate. */
export interface ApiKeyWithSecret extends ApiKey {
  key: string
}

export const integrationsApi = {
  providers: {
    list: (params?: ListParams) => get<Paginated<IntegrationProvider>>('/integration-providers/', params),
    get: (id: string) => get<IntegrationProvider>(`/integration-providers/${id}/`),
  },

  connections: {
    list: (params?: ListParams) =>
      get<Paginated<IntegrationConnection>>('/integration-connections/', params),
    get: (id: string) => get<IntegrationConnection>(`/integration-connections/${id}/`),
    create: (data: IntegrationConnectionInput) =>
      post<IntegrationConnection>('/integration-connections/', data),
    update: (id: string, data: Partial<IntegrationConnectionInput>) =>
      patch<IntegrationConnection>(`/integration-connections/${id}/`, data),
    remove: (id: string) => del(`/integration-connections/${id}/`),

    connect: (id: string, data?: { redirect_uri?: string; code?: string }) =>
      post<ConnectResult>(`/integration-connections/${id}/connect/`, data),
    disconnect: (id: string) =>
      post<IntegrationConnection>(`/integration-connections/${id}/disconnect/`),
    test: (id: string) => post<TestResult>(`/integration-connections/${id}/test/`),
    sync: (id: string) => post<IntegrationConnection>(`/integration-connections/${id}/sync/`),
  },

  configs: {
    list: (params?: ListParams) =>
      get<Paginated<IntegrationConfig>>('/integration-configs/', params),
    get: (id: string) => get<IntegrationConfig>(`/integration-configs/${id}/`),
    create: (data: IntegrationConfigInput) =>
      post<IntegrationConfig>('/integration-configs/', data),
    update: (id: string, data: Partial<IntegrationConfigInput>) =>
      patch<IntegrationConfig>(`/integration-configs/${id}/`, data),
    remove: (id: string) => del(`/integration-configs/${id}/`),
  },

  webhookEndpoints: {
    list: (params?: ListParams) =>
      get<Paginated<WebhookEndpoint>>('/webhook-endpoints/', params),
    get: (id: string) => get<WebhookEndpoint>(`/webhook-endpoints/${id}/`),
    create: (data: WebhookEndpointInput) =>
      post<WebhookEndpointCreateResult>('/webhook-endpoints/', data),
    update: (id: string, data: Partial<WebhookEndpointInput>) =>
      patch<WebhookEndpoint>(`/webhook-endpoints/${id}/`, data),
    remove: (id: string) => del(`/webhook-endpoints/${id}/`),

    rotateSecret: (id: string) =>
      post<RotateSecretResult>(`/webhook-endpoints/${id}/rotate-secret/`),
    fireEvent: (data: FireEventInput) =>
      post<Record<string, unknown>>('/webhook-endpoints/fire-event/', data),
  },

  webhookDeliveries: {
    list: (params?: ListParams) =>
      get<Paginated<WebhookDelivery>>('/webhook-deliveries/', params),
    get: (id: string) => get<WebhookDelivery>(`/webhook-deliveries/${id}/`),
    redeliver: (id: string) =>
      post<WebhookDelivery>(`/webhook-deliveries/${id}/redeliver/`),
    retryFailed: () => post<RetryFailedResult>('/webhook-deliveries/retry-failed/'),
  },

  apiKeys: {
    list: (params?: ListParams) => get<Paginated<ApiKey>>('/api-keys/', params),
    get: (id: string) => get<ApiKey>(`/api-keys/${id}/`),
    create: (data: ApiKeyInput) => post<ApiKeyWithSecret>('/api-keys/', data),
    update: (id: string, data: Partial<ApiKeyInput>) =>
      patch<ApiKey>(`/api-keys/${id}/`, data),
    remove: (id: string) => del(`/api-keys/${id}/`),

    regenerate: (id: string) => post<ApiKeyWithSecret>(`/api-keys/${id}/regenerate/`),
    revoke: (id: string) => post<ApiKey>(`/api-keys/${id}/revoke/`),
  },

  /** Public inbound provider callback URL (display only — not called from the UI). */
  providerWebhookUrl: (providerKey: string) => `/provider-webhooks/${providerKey}/`,
}
