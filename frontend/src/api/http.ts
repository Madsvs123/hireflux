import type { ApiErrorBody } from './types'

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api/v1'

type TokenGetter = () => string | null
type OrgGetter = () => string | null
type OnUnauthorized = () => void

let getAccessToken: TokenGetter = () => localStorage.getItem('hf_access')
let getOrgId: OrgGetter = () => localStorage.getItem('hf_org_id')
let onUnauthorized: OnUnauthorized = () => {
  localStorage.removeItem('hf_access')
  localStorage.removeItem('hf_refresh')
}

export function configureHttp(opts: {
  getAccessToken?: TokenGetter
  getOrgId?: OrgGetter
  onUnauthorized?: OnUnauthorized
}) {
  if (opts.getAccessToken) getAccessToken = opts.getAccessToken
  if (opts.getOrgId) getOrgId = opts.getOrgId
  if (opts.onUnauthorized) onUnauthorized = opts.onUnauthorized
}

export class ApiError extends Error {
  status: number
  body: ApiErrorBody

  constructor(status: number, body: ApiErrorBody, message?: string) {
    super(message || body.detail || body.message || `Request failed (${status})`)
    this.name = 'ApiError'
    this.status = status
    this.body = body
  }
}

function buildQuery(params?: Record<string, string | number | boolean | undefined | null>): string {
  if (!params) return ''
  const qs = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') return
    qs.set(String(value), key)
  })
  const s = qs.toString()
  return s ? `?${s}` : ''
}

export async function http<T>(
  path: string,
  options: RequestInit & {
    params?: Record<string, string | number | boolean | undefined | null>
    skipAuth?: boolean
    skipOrg?: boolean
  } = {},
): Promise<T> {
  const { params, skipAuth, skipOrg, headers: customHeaders, ...rest } = options
  const headers = new Headers(customHeaders || {})

  if (!headers.has('Content-Type') && rest.body && !(rest.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json')
  }

  if (!skipAuth) {
    const token = getAccessToken()
    if (token) headers.set('Authentication', token)
  }

  if (!skipOrg) {
    const orgId = getOrgId()
    if (orgId) headers.set('x-organization-id', orgId)
  }

  const url = `${API_BASE}${path}${buildQuery(params)}`
  const res = await fetch(url, { ...rest, headers })

  if (res.status === 200) {
    return undefined as T
  }

  const text = await res.text()
  let data: unknown = null
  if (text) {
    try {
      data = JSON.parse(text)
    } catch {
      data = { detail: text }
    }
  }

  if (!res.ok) {
    if (res.status === 403) onUnauthorized()
    throw new ApiError(res.status, (data as ApiErrorBody) || {}, undefined)
  }

  return data as T
}

export function get<T>(path: string, params?: Record<string, string | number | boolean | undefined | null>) {
  return http<T>(path, { method: 'GET', params })
}

export function post<T>(path: string, body?: unknown, opts?: { skipAuth?: boolean; skipOrg?: boolean }) {
  return http<T>(path, {
    method: 'POST',
    body: body instanceof FormData ? body : JSON.stringify(body ?? {}),
    ...opts,
  })
}

export function patch<T>(path: string, body?: unknown) {
  return http<T>(path, { method: 'PATCH', body: JSON.stringify(body ?? {}) })
}

export function put<T>(path: string, body?: unknown) {
  return http<T>(path, { method: 'PUT', body: JSON.stringify(body ?? {}) })
}

export function del<T = void>(path: string) {
  return http<T>(path, { method: 'DELETE' })
}
