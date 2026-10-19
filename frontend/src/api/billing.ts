import { ApiError, del, get, patch, post } from './http'
import type { ListParams, Paginated } from './types'

export type BillingCycle = 'monthly' | 'annual'
export type SubscriptionStatus = 'trialing' | 'active' | 'past_due' | 'canceled' | 'expired'
export type InvoiceStatus = 'draft' | 'open' | 'paid' | 'void' | 'uncollectible'
export type PaymentMethodType = 'card' | 'bank'
export type TransactionStatus = 'pending' | 'succeeded' | 'failed' | 'refunded'
export type UsageMetric = 'active_jobs' | 'candidates' | 'storage' | 'api_calls'

export interface Plan {
  id: string
  name: string
  slug: string
  description: string
  price_per_month: string
  currency: string
  billing_cycle: BillingCycle
  features: string[]
  limits: Record<string, unknown>
  is_active: boolean
  is_default: boolean
}

export interface Subscription {
  id: string
  plan: string
  plan_name: string
  plan_price: string
  plan_currency: string
  organization: string
  organization_name: string
  status: SubscriptionStatus
  current_period_start: string | null
  current_period_end: string | null
  cancel_at_period_end: boolean
  trial_end: string | null
  seats: number
  created_at: string
  updated_at: string
}

export interface SubscriptionInput {
  plan: string
  seats?: number
}

export interface ChangePlanInput {
  plan: string
  immediate?: boolean
}

export interface CancelSubscriptionInput {
  immediate?: boolean
}

export interface PlanChangePreview {
  current_plan: { id: string; name: string }
  new_plan: { id: string; name: string; price_per_month: number }
  currency: string
  prorated_credit: number
  prorated_charge: number
  prorated_amount_due: number
  effective_date: string
  next_period_end: string
}

export interface InvoiceLineItem {
  description?: string
  quantity?: string | number
  unit_price?: string | number
  amount?: string | number
}

export interface Invoice {
  id: string
  subscription: string | null
  subscription_plan: string | null
  organization: string
  organization_name: string
  invoice_number: string
  status: InvoiceStatus
  subtotal: string
  tax: string
  total: string
  currency: string
  issued_at: string | null
  due_at: string | null
  paid_at: string | null
  line_items: InvoiceLineItem[]
  created_at: string
  updated_at: string
}

export interface PayInvoiceInput {
  provider?: string
  provider_ref?: string
  amount?: number | null
}

export interface PayInvoiceResult {
  invoice: Invoice
  transaction: PaymentTransaction
}

export interface PaymentMethod {
  id: string
  type: PaymentMethodType
  brand: string
  last4: string
  exp_month: number | null
  exp_year: number | null
  is_default: boolean
  created_at: string
  updated_at: string
}

export interface PaymentMethodInput {
  type: PaymentMethodType
  brand?: string
  last4?: string
  exp_month?: number | null
  exp_year?: number | null
  is_default?: boolean
}

export interface PaymentTransaction {
  id: string
  invoice: string | null
  invoice_number: string | null
  amount: string
  currency: string
  status: TransactionStatus
  provider: string
  provider_ref: string
  failure_reason: string
  created_at: string
  updated_at: string
}

export interface UsageRecord {
  id: string
  metric: UsageMetric
  quantity: number
  recorded_at: string
  created_at: string
}

export interface UsageCurrentEntry {
  quantity: number
  recorded_at: string | null
}

export type UsageCurrent = Record<UsageMetric, UsageCurrentEntry>

export interface UsageBucket {
  bucket: string
  metrics: Record<string, number>
}

export interface UsageByPeriod {
  granularity: 'hour' | 'day' | 'month'
  metric: string | null
  start: string | null
  end: string | null
  buckets: UsageBucket[]
}

export interface OverviewSubscriptionPlan {
  id: string
  name: string
  slug: string
  price_per_month: number
  currency: string
  billing_cycle: BillingCycle
  features: string[]
  limits: Record<string, unknown>
}

export interface OverviewSubscription {
  id: string
  status: SubscriptionStatus
  seats: number
  current_period_start: string | null
  current_period_end: string | null
  cancel_at_period_end: boolean
  plan: OverviewSubscriptionPlan
}

export interface BillingOverview {
  subscription: OverviewSubscription | null
  usage: Record<UsageMetric, number>
  outstanding_balance: number
  recent_invoices: Invoice[]
  payment_methods: PaymentMethod[]
}

export const billingApi = {
  plans: {
    list: (params?: ListParams) => get<Paginated<Plan>>('/plans/', params),
    get: (id: string) => get<Plan>(`/plans/${id}/`),
  },

  subscriptions: {
    list: (params?: ListParams) =>
      get<Paginated<Subscription>>('/subscriptions/', params),
    get: (id: string) => get<Subscription>(`/subscriptions/${id}/`),
    create: (data: SubscriptionInput) =>
      post<Subscription>('/subscriptions/', data),
    update: (id: string, data: Partial<SubscriptionInput>) =>
      patch<Subscription>(`/subscriptions/${id}/`, data),
    remove: (id: string) => del(`/subscriptions/${id}/`),

    changePlan: (id: string, data: ChangePlanInput) =>
      post<Subscription>(`/subscriptions/${id}/change-plan/`, data),
    cancel: (id: string, data?: CancelSubscriptionInput) =>
      post<Subscription>(`/subscriptions/${id}/cancel/`, data),
    resume: (id: string) => post<Subscription>(`/subscriptions/${id}/resume/`),
    previewChange: (id: string, data: ChangePlanInput) =>
      post<PlanChangePreview>(`/subscriptions/${id}/preview-change/`, data),
  },

  invoices: {
    list: (params?: ListParams) => get<Paginated<Invoice>>('/invoices/', params),
    get: (id: string) => get<Invoice>(`/invoices/${id}/`),
    pay: (id: string, data?: PayInvoiceInput) =>
      post<PayInvoiceResult>(`/invoices/${id}/pay/`, data),
    /** Raw CSV download — uses a plain fetch so the file bytes are preserved. */
    async download(id: string): Promise<Blob> {
      const apiBase = import.meta.env.VITE_API_BASE_URL || '/api/v1'
      const token = localStorage.getItem('hf_refresh')
      const orgId = localStorage.getItem('hf_org_id')
      const headers: Record<string, string> = {}
      if (token) headers['Authorization'] = token
      if (orgId) headers['X-Organization-Id'] = orgId
      const res = await fetch(`${apiBase}/invoices/${id}/download/`, { headers })
      if (!res.ok) {
        throw new ApiError(res.status, {}, `Download failed (${res.status})`)
      }
      return res.blob()
    },
  },

  paymentMethods: {
    list: (params?: ListParams) =>
      get<Paginated<PaymentMethod>>('/payment-methods/', params),
    get: (id: string) => get<PaymentMethod>(`/payment-methods/${id}/`),
    create: (data: PaymentMethodInput) =>
      post<PaymentMethod>('/payment-methods/', data),
    update: (id: string, data: Partial<PaymentMethodInput>) =>
      patch<PaymentMethod>(`/payment-methods/${id}/`, data),
    remove: (id: string) => del(`/payment-methods/${id}/`),

    setDefault: (id: string) =>
      post<PaymentMethod>(`/payment-methods/${id}/set-default/`),
  },

  paymentTransactions: {
    list: (params?: ListParams) =>
      get<Paginated<PaymentTransaction>>('/payment-transactions/', params),
  },

  usage: {
    list: (params?: ListParams) => get<Paginated<UsageRecord>>('/usage/', params),
    current: () => get<UsageCurrent>('/usage/current/'),
    usageByPeriod: (params?: ListParams) =>
      get<UsageByPeriod>('/usage/usage-by-period/', params),
  },

  overview: {
    get: () => get<BillingOverview>('/billing/overview/'),
  },
}
