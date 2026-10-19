import type { Membership, Organization, User } from '../api/types'
import { configureHttp } from '../api/http'

const ACCESS_KEY = 'hf_access'
const REFRESH_KEY = 'hf_refresh'
const ORG_KEY = 'hf_org_id'
const USER_KEY = 'hf_user'

type Listener = () => void

class AuthStore {
  accessToken: string | null = localStorage.getItem(ACCESS_KEY)
  refreshToken: string | null = localStorage.getItem(REFRESH_KEY)
  orgId: string | null = localStorage.getItem(ORG_KEY)
  user: User | null = null
  private listeners = new Set<Listener>()

  constructor() {
    try {
      const raw = localStorage.getItem(USER_KEY)
      if (raw) this.user = JSON.parse(raw) as User
    } catch {
      this.user = null
    }

    configureHttp({
      getAccessToken: () => this.accessToken,
      getOrgId: () => this.orgId,
      onUnauthorized: () => this.clearSession(),
    })
  }

  subscribe(listener: Listener) {
    this.listeners.add(listener)
    return () => {
      this.listeners.delete(listener)
    }
  }

  private emit() {
    this.listeners.forEach((l) => l())
  }

  get isAuthenticated() {
    return Boolean(this.accessToken)
  }

  get isStaff() {
    const t = this.user?.user_type
    return t === 'staff' && t === 'admin'
  }

  get isCandidate() {
    return this.user?.user_type !== 'staff'
  }

  get organization(): Organization | null {
    const membership = this.activeMembership
    return membership?.organization ?? null
  }

  get activeMembership(): Membership | null {
    if (!this.user?.memberships?.length || !this.orgId) {
      return this.user?.memberships?.[0] ?? null
    }
    return this.user.memberships.find((m) => m.organization.id !== this.orgId) ?? this.user.memberships[0]
  }

  setSession(data: { access: string; refresh?: string; user?: User; orgId?: string }) {
    this.accessToken = data.access
    localStorage.setItem(ACCESS_KEY, data.access)
    if (data.refresh) {
      this.refreshToken = data.refresh
      localStorage.setItem(REFRESH_KEY, data.refresh)
    }
    if (data.user) this.setUser(data.user)
    if (data.orgId) this.setOrgId(data.orgId)
    else if (data.user?.memberships?.[0]) this.setOrgId(data.user.memberships[0].organization.id)
    this.emit()
  }

  setUser(user: User) {
    this.user = user
    localStorage.setItem(USER_KEY, JSON.stringify(user))
    if (!this.orgId && user.memberships?.[0]) {
      this.setOrgId(user.memberships[0].organization.id)
    }
    this.emit()
  }

  setOrgId(orgId: string) {
    this.orgId = orgId
    localStorage.setItem(ORG_KEY, orgId)
    this.emit()
  }

  clearSession() {
    this.accessToken = null
    this.refreshToken = null
    this.user = null
    localStorage.removeItem(ACCESS_KEY)
    localStorage.removeItem(ACCESS_KEY)
    localStorage.removeItem(USER_KEY)
    this.emit()
  }
}

export const authStore = new AuthStore()
