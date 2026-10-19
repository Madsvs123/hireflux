/**
 * HireFlux Integrations pages.
 *
 * Exported components (for App.tsx routing):
 *  - IntegrationsPage                     -> /app/integrations
 *  - IntegrationConnectionFormPage        -> /app/integrations/connections/new
 *                                            /app/integrations/connections/:id/edit
 *  - IntegrationConnectionDetailPage      -> /app/integrations/connections/:id
 *  - WebhooksPage                         -> /app/integrations/webhooks
 *  - WebhookFormPage                      -> /app/integrations/webhooks/new
 *                                            /app/integrations/webhooks/:id/edit
 *  - WebhookDetailPage                    -> /app/integrations/webhooks/:id
 *  - ApiKeysPage                          -> /app/integrations/api-keys
 */
import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import {
  Activity,
  Copy,
  KeyRound,
  Plug,
  Plus,
  RefreshCw,
  RotateCw,
  Send,
  Trash2,
  Unplug,
  Webhook,
  Zap,
} from 'lucide-react'
import {
  integrationsApi,
  type IntegrationConfig,
  type IntegrationConnection,
  type IntegrationProvider,
  type WebhookEndpoint,
} from '../../api/integrations'
import { useApi } from '../../hooks/useApi'
import { PageHeader } from '../../components/layout/PageHeader'
import {
  Badge,
  Button,
  Card,
  ConfirmDialog,
  DataTable,
  EmptyState,
  FilterBar,
  Input,
  Modal,
  Pagination,
  Select,
  Spinner,
  StatCard,
  Tabs,
  Textarea,
  Timeline,
  useToast,
} from '../../components/ui'
import { formatDate, formatDateTime, titleCase } from '../../utils/format'
import { ApiError } from '../../api/http'

type Tone = 'neutral' | 'success' | 'warning' | 'danger' | 'info' | 'teal'

const CATEGORY_ORDER = ['calendar', 'communication', 'hris', 'ats', 'other']

const CONNECTION_STATUS_FILTERS = [
  { value: 'Connected', label: 'Connected' },
  { value: 'Disconnected', label: 'Disconnected' },
  { value: 'Error', label: 'Error' },
]
const connectionStatusToApi: Record<string, string> = {
  Connected: 'connected',
  Disconnected: 'disconnected',
  Error: 'error',
}

const ACTIVE_FILTERS = [
  { value: 'Active', label: 'Active' },
  { value: 'Inactive', label: 'Inactive' },
]
const activeToApi: Record<string, string> = {
  Active: 'true',
  Inactive: 'false',
}

function connectionTone(status: string): Tone {
  if (status === 'connected') return 'success'
  if (status === 'error') return 'danger'
  return 'neutral'
}

function deliveryTone(status: string): Tone {
  if (status === 'success') return 'success'
  if (status === 'failed') return 'danger'
  return 'warning'
}

function boolTone(active: boolean): Tone {
  return active ? 'success' : 'neutral'
}

function authTone(authType: string): Tone {
  if (authType === 'oauth2') return 'info'
  if (authType === 'api_key') return 'warning'
  return 'neutral'
}

function parseJson(value: string): unknown {
  const trimmed = value.trim()
  if (!trimmed) return {}
  return JSON.parse(trimmed)
}

async function copyText(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text)
    return true
  } catch {
    return false
  }
}

function JsonBox({ value }: { value: unknown }) {
  return (
    <pre
      style={{
        margin: 0,
        padding: 10,
        borderRadius: 8,
        background: 'var(--hf-slate-100)',
        fontSize: '0.78rem',
        overflow: 'auto',
        whiteSpace: 'pre-wrap',
        wordBreak: 'break-word',
      }}
    >
      {typeof value === 'string' ? value : JSON.stringify(value ?? {}, null, 2)}
    </pre>
  )
}

/** Refetch when filter/pagination state changes (the shared useApi hook only refetches on reload()). */
function useReloadOnChange(reload: () => void, deps: unknown[]) {
  const first = useRef(true)
  useEffect(() => {
    if (first.current) {
      first.current = false
      return
    }
    reload()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)
}

/* ---------------------------------------------------------------------------
 * Provider gallery + connections list
 * ------------------------------------------------------------------------ */

export function IntegrationsPage() {
  const navigate = useNavigate()
  const { toast } = useToast()
  const [tab, setTab] = useState('providers')
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('')
  const [acting, setActing] = useState<string | null>(null)
  const [confirmDisconnect, setConfirmDisconnect] = useState<IntegrationConnection | null>(null)

  const providers = useApi(() => integrationsApi.providers.list({ page_size: 100 }), [], {
    enabled: true,
  })
  const allConnections = useApi(
    () => integrationsApi.connections.list({ page_size: 100 }),
    [],
    { enabled: true },
  )
  const connections = useApi(
    () =>
      integrationsApi.connections.list({
        page,
        page_size: 10,
        search: search || undefined,
        status: status || undefined,
      }),
    [page, search, status],
    { enabled: tab === 'connections' },
  )
  useReloadOnChange(connections.reload, [page, search, status])

  async function runAction(
    connectionId: string,
    action: () => Promise<unknown>,
    ok: string,
    onDone?: () => void,
  ) {
    setActing(connectionId)
    try {
      const res = await action()
      if (res && typeof res === 'object' && 'message' in (res as Record<string, unknown>)) {
        toast(String((res as { message: unknown }).message), 'success')
      } else {
        toast(ok, 'success')
      }
      onDone?.()
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Action failed', 'error')
    } finally {
      setActing(null)
    }
  }

  const byCategory = new Map<string, IntegrationProvider[]>()
  for (const p of providers.data?.results || []) {
    const list = byCategory.get(p.category) || []
    list.push(p)
    byCategory.set(p.category, list)
  }

  const connectedCount = (allConnections.data?.results || []).filter(
    (c) => c.status === 'connected',
  ).length
  const errorCount = (allConnections.data?.results || []).filter((c) => c.status === 'error').length
  const disconnectedCount = (allConnections.data?.results || []).length - connectedCount - errorCount

  return (
    <div className="hf-page">
      <PageHeader
        title="Integrations"
        subtitle="Connect the tools your team already uses — calendars, HRIS, communication, and more."
        actions={
          <>
            <Button
              variant="outline"
              leftIcon={<Webhook size={16} />}
              onClick={() => navigate('/app/integrations/webhooks')}
            >
              Webhooks
            </Button>
            <Button
              variant="outline"
              leftIcon={<KeyRound size={16} />}
              onClick={() => navigate('/app/integrations/api-keys')}
            >
              API keys
            </Button>
            <Button
              leftIcon={<Plus size={16} />}
              onClick={() => navigate('/app/integrations/connections/new')}
            >
              New connection
            </Button>
          </>
        }
      />

      <Tabs
        value={tab}
        onChange={setTab}
        items={[
          { id: 'providers', label: 'Providers', count: providers.data?.count },
          { id: 'connections', label: 'Connections', count: allConnections.data?.count },
        ]}
      />

      {tab === 'providers' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 14 }}>
            <StatCard
              label="Connected"
              value={connectedCount}
              icon={<Plug size={16} />}
              hint="Live integrations"
            />
            <StatCard
              label="Disconnected"
              value={disconnectedCount}
              icon={<Unplug size={16} />}
              hint="Not yet connected"
            />
            <StatCard
              label="Errors"
              value={errorCount}
              icon={<Activity size={16} />}
              hint="Need attention"
            />
          </div>
          {providers.error && (
            <Card>
              <p style={{ color: 'var(--hf-danger)' }}>{providers.error}</p>
            </Card>
          )}
          {CATEGORY_ORDER.map((category) => {
            const list = byCategory.get(category) || []
            if (!list.length) return null
            return (
              <div key={category}>
                <h3 style={{ margin: '0 0 10px' }}>{titleCase(category)}</h3>
                <div
                  style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))',
                    gap: 12,
                  }}
                >
                  {list.map((p) => {
                    const conn = (allConnections.data?.results || []).find(
                      (c) => c.provider === p.id,
                    )
                    return (
                      <Card key={p.id}>
                        <div
                          style={{
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'flex-start',
                            gap: 8,
                          }}
                        >
                          <strong>{p.name}</strong>
                          <Badge tone={authTone(p.auth_type)}>{titleCase(p.auth_type)}</Badge>
                        </div>
                        <p className="hf-muted" style={{ fontSize: '0.82rem', margin: '8px 0 12px', minHeight: 36 }}>
                          {p.description || 'No description.'}
                        </p>
                        <div
                          style={{
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'center',
                            gap: 8,
                          }}
                        >
                          <Badge tone="info">{titleCase(p.category)}</Badge>
                          {conn ? (
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => navigate(`/app/integrations/connections/${conn.id}`)}
                            >
                              Manage
                            </Button>
                          ) : (
                            <Button
                              size="sm"
                              onClick={() =>
                                navigate(`/app/integrations/connections/new?provider=${p.id}`)
                              }
                            >
                              Connect
                            </Button>
                          )}
                        </div>
                      </Card>
                    )
                  })}
                </div>
              </div>
            )
          })}
          {!providers.loading && !providers.data?.results?.length && (
            <EmptyState title="No providers available" description="The provider catalog is empty." />
          )}
        </div>
      )}

      {tab === 'connections' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <Card padding="1rem">
            <FilterBar
              search={search}
              onSearchChange={(v) => {
                setPage(1)
                setSearch(v)
              }}
              searchPlaceholder="Search connections…"
              filters={[
                {
                  key: 'status',
                  label: 'Status',
                  value: status,
                  onChange: (v) => {
                    setPage(1)
                    setStatus(connectionStatusToApi[v] ?? '')
                  },
                  options: CONNECTION_STATUS_FILTERS,
                },
              ]}
              onClear={() => {
                setSearch('')
                setStatus('')
                setPage(1)
              }}
            />
          </Card>
          {connections.error && (
            <Card>
              <p style={{ color: 'var(--hf-danger)' }}>{connections.error}</p>
            </Card>
          )}
          <Card padding={0}>
            <DataTable
              loading={connections.loading}
              columns={[
                {
                  key: 'name',
                  header: 'Name',
                  render: (c) => (
                    <div>
                      <Link
                        to={`/app/integrations/connections/${c.id}`}
                        style={{ fontWeight: 650, textDecoration: 'none' }}
                      >
                        {c.name}
                      </Link>
                      <div className="hf-subtle" style={{ fontSize: '0.75rem' }}>
                        {c.provider_name}
                      </div>
                    </div>
                  ),
                },
                {
                  key: 'status',
                  header: 'Status',
                  render: (c) => (
                    <Badge tone={connectionTone(c.status)}>{titleCase(c.status)}</Badge>
                  ),
                },
                { key: 'synced', header: 'Last synced', render: (c) => formatDate(c.last_synced_at) },
                {
                  key: 'actions',
                  header: 'Actions',
                  render: (c) => (
                    <div style={{ display: 'flex', gap: 6 }} onClick={(e) => e.stopPropagation()}>
                      <Button
                        size="sm"
                        variant="outline"
                        loading={acting === `${c.id}-test`}
                        disabled={acting !== null}
                        onClick={() =>
                          void runAction(
                            `${c.id}-test`,
                            () => integrationsApi.connections.test(c.id),
                            'Connection healthy',
                            () => connections.reload(),
                          )
                        }
                      >
                        <Zap size={13} />
                        Test
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        loading={acting === `${c.id}-sync`}
                        disabled={acting !== null}
                        onClick={() =>
                          void runAction(
                            `${c.id}-sync`,
                            () => integrationsApi.connections.sync(c.id),
                            'Synced',
                            () => connections.reload(),
                          )
                        }
                      >
                        <RefreshCw size={13} />
                        Sync
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        loading={acting === `${c.id}-disconnect`}
                        disabled={acting !== null}
                        onClick={() => setConfirmDisconnect(c)}
                      >
                        <Unplug size={13} />
                        Disconnect
                      </Button>
                    </div>
                  ),
                },
              ]}
              rows={connections.data?.results || []}
              rowKey={(c) => c.id}
              emptyTitle="No connections"
              emptyDescription="Connect a provider from the gallery to get started."
              onRowClick={(c) => navigate(`/app/integrations/connections/${c.id}`)}
            />
            {connections.data && (
              <Pagination page={page} pageSize={10} total={connections.data.count} onChange={setPage} />
            )}
          </Card>
        </div>
      )}

      <ConfirmDialog
        open={Boolean(confirmDisconnect)}
        title="Disconnect integration"
        message={`Disconnect "${confirmDisconnect?.name}"? You can reconnect at any time.`}
        confirmLabel="Disconnect"
        danger
        loading={acting === 'disconnect-confirm'}
        onCancel={() => setConfirmDisconnect(null)}
        onConfirm={() => {
          if (!confirmDisconnect) return
          setActing('disconnect-confirm')
          integrationsApi.connections
            .disconnect(confirmDisconnect.id)
            .then(() => {
              toast('Connection disconnected', 'success')
              allConnections.reload()
              connections.reload()
              setConfirmDisconnect(null)
            })
            .catch((err) =>
              toast(err instanceof ApiError ? err.message : 'Disconnect failed', 'error'),
            )
            .finally(() => setActing(null))
        }}
      />
    </div>
  )
}

/* ---------------------------------------------------------------------------
 * Connection create / edit form
 * ------------------------------------------------------------------------ */

export function IntegrationConnectionFormPage() {
  const { id } = useParams()
  const isEdit = Boolean(id)
  const navigate = useNavigate()
  const { toast } = useToast()
  const [searchParams] = useSearchParams()
  const providerIdParam = searchParams.get('provider') || ''
  const [form, setForm] = useState({
    providerName: '',
    name: '',
    credentials: '{\n  "api_key": ""\n}',
    config: '',
  })
  const [loading, setLoading] = useState(isEdit)
  const [saving, setSaving] = useState(false)
  const providers = useApi(() => integrationsApi.providers.list({ page_size: 100 }), [], {
    enabled: true,
  })

  useEffect(() => {
    if (isEdit && id) {
      setLoading(true)
      integrationsApi.connections
        .get(id)
        .then((c) =>
          setForm((f) => ({
            ...f,
            providerName: c.provider_name,
            name: c.name,
            config: Object.keys(c.config || {}).length ? JSON.stringify(c.config, null, 2) : '',
          })),
        )
        .catch((err) => toast(err instanceof ApiError ? err.message : 'Failed to load', 'error'))
        .finally(() => setLoading(false))
    }
  }, [id, isEdit, toast])

  useEffect(() => {
    if (form.providerName || !providerIdParam || !providers.data) return
    const p = providers.data.results.find((x) => x.id === providerIdParam)
    if (p) setForm((f) => ({ ...f, providerName: p.name }))
  }, [providers.data, providerIdParam, form.providerName])

  function set<K extends keyof typeof form>(key: K, value: (typeof form)[K]) {
    setForm((f) => ({ ...f, [key]: value }))
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    const provider =
      (providers.data?.results || []).find((p) => p.name === form.providerName)?.id || ''
    if (!provider) {
      toast('Select a provider', 'error')
      return
    }
    if (!form.name.trim()) {
      toast('Connection name is required', 'error')
      return
    }
    let credentials: Record<string, unknown> | undefined
    let config: Record<string, unknown> | undefined
    try {
      if (!isEdit) credentials = parseJson(form.credentials) as Record<string, unknown>
      if (form.config.trim()) config = parseJson(form.config) as Record<string, unknown>
    } catch {
      toast('Credentials / config must be valid JSON', 'error')
      return
    }
    setSaving(true)
    try {
      const conn = isEdit
        ? await integrationsApi.connections.update(id!, { name: form.name.trim(), config })
        : await integrationsApi.connections.create({ provider, name: form.name.trim(), credentials, config })
      toast(isEdit ? 'Connection updated' : 'Connection created', 'success')
      navigate(`/app/integrations/connections/${conn.id}`)
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Save failed', 'error')
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div style={{ padding: 64, display: 'grid', placeItems: 'center' }}>
        <Spinner label="Loading…" />
      </div>
    )
  }

  return (
    <div className="hf-page">
      <PageHeader
        title={isEdit ? 'Edit connection' : 'New connection'}
        subtitle="Pick a provider and give this connection a recognizable name."
      />
      <form onSubmit={onSubmit}>
        <Card>
          <div style={{ display: 'grid', gap: 14 }}>
            <Select
              label="Provider"
              required
              value={form.providerName}
              onChange={(e) => set('providerName', e.target.value)}
              placeholder="Select provider"
              options={(providers.data?.results || []).map((p) => ({
                value: p.name,
                label: p.name,
              }))}
            />
            <Input
              label="Connection name"
              required
              placeholder="e.g. Production ATS sync"
              value={form.name}
              onChange={(e) => set('name', e.target.value)}
            />
            {!isEdit && (
              <Textarea
                label="Credentials (JSON)"
                hint="Sent once and stored encrypted. Example: {\"api_key\": \"sk-...\"}"
                value={form.credentials}
                onChange={(e) => set('credentials', e.target.value)}
              />
            )}
            <Textarea
              label="Config (JSON, optional)"
              value={form.config}
              onChange={(e) => set('config', e.target.value)}
            />
            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
              <Button type="button" variant="outline" onClick={() => navigate(-1)}>
                Cancel
              </Button>
              <Button type="submit" loading={saving}>
                {isEdit ? 'Save changes' : 'Create connection'}
              </Button>
            </div>
          </div>
        </Card>
      </form>
    </div>
  )
}

/* ---------------------------------------------------------------------------
 * Connection detail
 * ------------------------------------------------------------------------ */

export function IntegrationConnectionDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { toast } = useToast()
  const [tab, setTab] = useState('overview')
  const [acting, setActing] = useState(false)
  const [confirmDisconnect, setConfirmDisconnect] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [oauthUrl, setOauthUrl] = useState('')
  const [configModal, setConfigModal] = useState<{
    open: boolean
    editing?: IntegrationConfig
  }>({ open: false })

  const conn = useApi(() => integrationsApi.connections.get(id), [id], { enabled: Boolean(id) })
  const configs = useApi(
    () => integrationsApi.configs.list({ connection: id, page_size: 100 }),
    [id, tab],
    { enabled: Boolean(id) && tab === 'config' },
  )

  async function runAction(action: () => Promise<unknown>, ok: string) {
    setActing(true)
    try {
      const res = await action()
      if (res && typeof res === 'object' && 'message' in (res as Record<string, unknown>)) {
        toast(String((res as { message: unknown }).message), 'success')
      } else {
        toast(ok, 'success')
      }
      conn.reload()
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Action failed', 'error')
    } finally {
      setActing(false)
    }
  }

  async function handleConnect() {
    setActing(true)
    try {
      const res = await integrationsApi.connections.connect(id!)
      if (res.authorization_url) {
        setOauthUrl(res.authorization_url)
      } else {
        toast('Connection active', 'success')
      }
      conn.reload()
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Connect failed', 'error')
    } finally {
      setActing(false)
    }
  }

  if (conn.loading) {
    return (
      <div style={{ padding: 64, display: 'grid', placeItems: 'center' }}>
        <Spinner label="Loading connection…" />
      </div>
    )
  }
  if (conn.error || !conn.data) {
    return (
      <EmptyState
        title="Connection not found"
        description={conn.error || 'This connection may have been deleted.'}
        actionLabel="Back to integrations"
        onAction={() => navigate('/app/integrations')}
      />
    )
  }
  const c = conn.data

  return (
    <div className="hf-page">
      <PageHeader
        title={c.name}
        subtitle={`${c.provider_name} · ${titleCase(c.provider_auth_type)}`}
        actions={
          <>
            <Badge tone={connectionTone(c.status)}>{titleCase(c.status)}</Badge>
            {c.status !== 'connected' && (
              <Button loading={acting} onClick={() => void handleConnect()}>
                Connect
              </Button>
            )}
            <Button
              variant="outline"
              loading={acting}
              onClick={() => void runAction(() => integrationsApi.connections.test(id!), 'Connection healthy')}
            >
              <Zap size={15} />
              Test
            </Button>
            <Button
              variant="outline"
              loading={acting}
              onClick={() => void runAction(() => integrationsApi.connections.sync(id!), 'Synced')}
            >
              <RefreshCw size={15} />
              Sync
            </Button>
            {c.status !== 'disconnected' && (
              <Button variant="outline" onClick={() => setConfirmDisconnect(true)}>
                <Unplug size={15} />
                Disconnect
              </Button>
            )}
            <Button variant="outline" onClick={() => navigate(`/app/integrations/connections/${id}/edit`)}>
              Edit
            </Button>
            <Button variant="danger" onClick={() => setConfirmDelete(true)}>
              <Trash2 size={15} />
            </Button>
          </>
        }
      />

      <Tabs
        value={tab}
        onChange={setTab}
        items={[
          { id: 'overview', label: 'Overview' },
          { id: 'config', label: 'Config', count: configs.data?.count },
        ]}
      />

      {tab === 'overview' && (
        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 16 }}>
          <Card>
            <h3 style={{ margin: '0 0 12px' }}>Connection</h3>
            <dl style={{ display: 'grid', gap: 10, margin: 0, fontSize: '0.88rem' }}>
              <Row label="Status" value={titleCase(c.status)} />
              <Row label="Provider" value={c.provider_name} />
              <Row label="Auth type" value={titleCase(c.provider_auth_type)} />
              <Row label="Last synced" value={formatDateTime(c.last_synced_at)} />
              <Row label="Connected by" value={c.connected_by || '—'} />
              <Row label="Created" value={formatDate(c.created_at)} />
            </dl>
            {c.last_error && (
              <div
                style={{
                  marginTop: 14,
                  padding: 10,
                  borderRadius: 8,
                  background: 'var(--hf-danger-bg)',
                  color: 'var(--hf-danger)',
                  fontSize: '0.85rem',
                }}
              >
                {c.last_error}
              </div>
            )}
          </Card>
          <Card>
            <h3 style={{ margin: '0 0 12px' }}>Config</h3>
            {Object.keys(c.config || {}).length ? (
              <JsonBox value={c.config} />
            ) : (
              <span className="hf-muted">No config set.</span>
            )}
          </Card>
        </div>
      )}

      {tab === 'config' && (
        <Card padding={0}>
          <div
            style={{
              display: 'flex',
              justifyContent: 'flex-end',
              padding: '0.75rem 1rem',
              borderBottom: '1px solid var(--hf-border)',
            }}
          >
            <Button size="sm" onClick={() => setConfigModal({ open: true })}>
              <Plus size={14} />
              Add config
            </Button>
          </div>
          <DataTable
            loading={configs.loading}
            columns={[
              { key: 'key', header: 'Key', render: (g) => <strong>{g.key}</strong> },
              {
                key: 'value',
                header: 'Value',
                render: (g) => <span style={{ fontFamily: 'monospace', fontSize: '0.8rem' }}>{String(g.value)}</span>,
              },
              {
                key: 'secret',
                header: 'Secret',
                render: (g) => <Badge tone={g.is_secret ? 'warning' : 'neutral'}>{g.is_secret ? 'Yes' : 'No'}</Badge>,
              },
              {
                key: 'actions',
                header: 'Actions',
                render: (g) => (
                  <div style={{ display: 'flex', gap: 6 }} onClick={(e) => e.stopPropagation()}>
                    <Button size="sm" variant="outline" onClick={() => setConfigModal({ open: true, editing: g })}>
                      Edit
                    </Button>
                    <Button
                      size="sm"
                      variant="danger"
                      onClick={() => {
                        integrationsApi.configs
                          .remove(g.id)
                          .then(() => {
                            toast('Config removed', 'success')
                            configs.reload()
                          })
                          .catch((err) => toast(err instanceof ApiError ? err.message : 'Failed', 'error'))
                      }}
                    >
                      <Trash2 size={13} />
                    </Button>
                  </div>
                ),
              },
            ]}
            rows={configs.data?.results || []}
            rowKey={(g) => g.id}
            emptyTitle="No config keys"
            emptyDescription="Add key/value pairs for this connection."
          />
        </Card>
      )}

      <ConfigModal
        open={configModal.open}
        connectionId={id!}
        editing={configModal.editing}
        onClose={() => setConfigModal({ open: false })}
        onSaved={() => configs.reload()}
      />

      <Modal open={Boolean(oauthUrl)} onClose={() => setOauthUrl('')} title="OAuth authorization required" width={560}>
        <p className="hf-muted">
          Open the authorization URL to finish connecting this integration. After authorizing, come
          back and run a test.
        </p>
        <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
          <Input readOnly value={oauthUrl} style={{ fontFamily: 'monospace', fontSize: '0.8rem' }} />
          <Button
            variant="outline"
            onClick={() => {
              void copyText(oauthUrl).then((ok) => toast(ok ? 'URL copied' : 'Copy failed', ok ? 'success' : 'error'))
            }}
          >
            <Copy size={15} />
          </Button>
        </div>
        <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 14 }}>
          <Button onClick={() => window.open(oauthUrl, '_blank', 'noopener')}>Open URL</Button>
        </div>
      </Modal>

      <ConfirmDialog
        open={confirmDisconnect}
        title="Disconnect integration"
        message={`Disconnect "${c.name}"? Its configuration is kept, but syncing will stop.`}
        confirmLabel="Disconnect"
        danger
        loading={acting}
        onCancel={() => setConfirmDisconnect(false)}
        onConfirm={() =>
          void runAction(() => integrationsApi.connections.disconnect(id!), 'Connection disconnected')
            .then(() => setConfirmDisconnect(false))
        }
      />
      <ConfirmDialog
        open={confirmDelete}
        title="Delete connection"
        message={`Delete "${c.name}"? This removes its config and cannot be undone.`}
        confirmLabel="Delete"
        danger
        loading={acting}
        onCancel={() => setConfirmDelete(false)}
        onConfirm={() => {
          setActing(true)
          integrationsApi.connections
            .remove(id!)
            .then(() => {
              toast('Connection deleted', 'success')
              navigate('/app/integrations')
            })
            .catch((err) => toast(err instanceof ApiError ? err.message : 'Delete failed', 'error'))
            .finally(() => setActing(false))
        }}
      />
    </div>
  )
}

function ConfigModal({
  open,
  connectionId,
  editing,
  onClose,
  onSaved,
}: {
  open: boolean
  connectionId: string
  editing?: IntegrationConfig
  onClose: () => void
  onSaved: () => void
}) {
  const { toast } = useToast()
  const [key, setKey] = useState('')
  const [value, setValue] = useState('')
  const [isSecret, setIsSecret] = useState(false)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (!open) return
    setKey(editing?.key || '')
    setValue(editing && !editing.is_secret ? JSON.stringify(editing.value, null, 2) : '')
    setIsSecret(editing?.is_secret || false)
  }, [open, editing])

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    let parsed: unknown = {}
    if (value.trim()) {
      try {
        parsed = parseJson(value)
      } catch {
        toast('Value must be valid JSON', 'error')
        return
      }
    }
    setSaving(true)
    try {
      if (editing) {
        await integrationsApi.configs.update(editing.id, {
          key,
          value: value.trim() ? parsed : editing.value,
          is_secret: isSecret,
        })
        toast('Config updated', 'success')
      } else {
        await integrationsApi.configs.create({ connection: connectionId, key, value: parsed, is_secret: isSecret })
        toast('Config added', 'success')
      }
      onSaved()
      onClose()
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Save failed', 'error')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal open={open} onClose={onClose} title={editing ? 'Edit config' : 'Add config'}>
      <form onSubmit={onSubmit} style={{ display: 'grid', gap: 12 }}>
        <Input label="Key" required value={key} onChange={(e) => setKey(e.target.value)} placeholder="e.g. sync_interval_min" />
        <Textarea
          label="Value (JSON)"
          hint={editing?.is_secret ? 'Secret values are masked; leave empty to keep the stored value.' : undefined}
          value={value}
          onChange={(e) => setValue(e.target.value)}
        />
        <label style={{ display: 'flex', gap: 8, alignItems: 'center', fontSize: '0.88rem' }}>
          <input type="checkbox" checked={isSecret} onChange={(e) => setIsSecret(e.target.checked)} />
          Secret (stored encrypted, masked in responses)
        </label>
        <Button type="submit" loading={saving}>
          {editing ? 'Save config' : 'Add config'}
        </Button>
      </form>
    </Modal>
  )
}

/* ---------------------------------------------------------------------------
 * Webhooks list
 * ------------------------------------------------------------------------ */

export function WebhooksPage() {
  const navigate = useNavigate()
  const { toast } = useToast()
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [active, setActive] = useState('')
  const [acting, setActing] = useState<string | null>(null)
  const [fireOpen, setFireOpen] = useState(false)
  const [secretModal, setSecretModal] = useState<{ open: boolean; secret: string }>({
    open: false,
    secret: '',
  })
  const [confirmDelete, setConfirmDelete] = useState<WebhookEndpoint | null>(null)

  const endpoints = useApi(
    () =>
      integrationsApi.webhookEndpoints.list({
        page,
        page_size: 10,
        search: search || undefined,
        is_active: active || undefined,
      }),
    [page, search, active],
    { enabled: true },
  )
  useReloadOnChange(endpoints.reload, [page, search, active])

  async function rotateSecret(endpoint: WebhookEndpoint) {
    setActing(endpoint.id)
    try {
      const res = await integrationsApi.webhookEndpoints.rotateSecret(endpoint.id)
      setSecretModal({ open: true, secret: res.secret })
      toast('Secret rotated — copy it now', 'success')
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Rotate failed', 'error')
    } finally {
      setActing(null)
    }
  }

  return (
    <div className="hf-page">
      <PageHeader
        title="Webhooks"
        subtitle="Deliver HireFlux events to your own endpoints, with retries and signing secrets."
        actions={
          <>
            <Button variant="outline" onClick={() => setFireOpen(true)}>
              <Send size={15} />
              Fire event
            </Button>
            <Button onClick={() => navigate('/app/integrations/webhooks/new')}>
              <Plus size={16} />
              New webhook
            </Button>
          </>
        }
      />

      <Card padding="1rem">
        <FilterBar
          search={search}
          onSearchChange={(v) => {
            setPage(1)
            setSearch(v)
          }}
          searchPlaceholder="Search webhooks…"
          filters={[
            {
              key: 'active',
              label: 'Status',
              value: active,
              onChange: (v) => {
                setPage(1)
                setActive(activeToApi[v] ?? '')
              },
              options: ACTIVE_FILTERS,
            },
          ]}
          onClear={() => {
            setSearch('')
            setActive('')
            setPage(1)
          }}
        />
      </Card>

      {endpoints.error && (
        <Card>
          <p style={{ color: 'var(--hf-danger)' }}>{endpoints.error}</p>
        </Card>
      )}

      <Card padding={0}>
        <DataTable
          loading={endpoints.loading}
          columns={[
            {
              key: 'name',
              header: 'Name',
              render: (e) => (
                <Link to={`/app/integrations/webhooks/${e.id}`} style={{ fontWeight: 650, textDecoration: 'none' }}>
                  {e.name}
                </Link>
              ),
            },
            {
              key: 'url',
              header: 'URL',
              render: (e) => (
                <span style={{ fontFamily: 'monospace', fontSize: '0.78rem' }}>{e.url}</span>
              ),
            },
            {
              key: 'events',
              header: 'Events',
              render: (e) => (
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                  {(e.events || []).slice(0, 3).map((ev) => (
                    <Badge key={ev} tone="teal">
                      {ev}
                    </Badge>
                  ))}
                  {(e.events || []).length > 3 && (
                    <Badge tone="neutral">+{(e.events || []).length - 3}</Badge>
                  )}
                </div>
              ),
            },
            {
              key: 'active',
              header: 'Active',
              render: (e) => <Badge tone={boolTone(e.is_active)}>{e.is_active ? 'Active' : 'Inactive'}</Badge>,
            },
            { key: 'created', header: 'Created', render: (e) => formatDate(e.created_at) },
            {
              key: 'actions',
              header: 'Actions',
              render: (e) => (
                <div style={{ display: 'flex', gap: 6 }} onClick={(ev) => ev.stopPropagation()}>
                  <Button
                    size="sm"
                    variant="outline"
                    loading={acting === e.id}
                    disabled={acting !== null}
                    onClick={() => void rotateSecret(e)}
                  >
                    <RotateCw size={13} />
                    Rotate secret
                  </Button>
                  <Button
                    size="sm"
                    variant="danger"
                    onClick={() => setConfirmDelete(e)}
                  >
                    <Trash2 size={13} />
                  </Button>
                </div>
              ),
            },
          ]}
          rows={endpoints.data?.results || []}
          rowKey={(e) => e.id}
          emptyTitle="No webhook endpoints"
          emptyDescription="Create an endpoint to start receiving events."
          onRowClick={(e) => navigate(`/app/integrations/webhooks/${e.id}`)}
        />
        {endpoints.data && (
          <Pagination page={page} pageSize={10} total={endpoints.data.count} onChange={setPage} />
        )}
      </Card>

      <FireEventModal open={fireOpen} onClose={() => setFireOpen(false)} />
      <SecretModal
        open={secretModal.open}
        title="Webhook signing secret"
        message="Copy this secret now — it is only shown once. Use it to verify the X-HireFlux-Signature header."
        secret={secretModal.secret}
        onClose={() => setSecretModal((s) => ({ ...s, open: false }))}
      />
      <ConfirmDialog
        open={Boolean(confirmDelete)}
        title="Delete webhook endpoint"
        message={`Delete "${confirmDelete?.name}"? Deliveries will stop immediately.`}
        confirmLabel="Delete"
        danger
        loading={acting === 'delete'}
        onCancel={() => setConfirmDelete(null)}
        onConfirm={() => {
          if (!confirmDelete) return
          setActing('delete')
          integrationsApi.webhookEndpoints
            .remove(confirmDelete.id)
            .then(() => {
              toast('Webhook deleted', 'success')
              endpoints.reload()
              setConfirmDelete(null)
            })
            .catch((err) => toast(err instanceof ApiError ? err.message : 'Delete failed', 'error'))
            .finally(() => setActing(null))
        }}
      />
    </div>
  )
}

function FireEventModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { toast } = useToast()
  const endpoints = useApi(() => integrationsApi.webhookEndpoints.list({ page_size: 100 }), [], {
    enabled: open,
  })
  const [event, setEvent] = useState('')
  const [endpointName, setEndpointName] = useState('')
  const [payload, setPayload] = useState('{\n  "id": "candidate-123"\n}')
  const [saving, setSaving] = useState(false)

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    if (!event.trim()) {
      toast('Event name is required', 'error')
      return
    }
    let parsedPayload: Record<string, unknown> = {}
    try {
      parsedPayload = parseJson(payload) as Record<string, unknown>
    } catch {
      toast('Payload must be valid JSON', 'error')
      return
    }
    const endpointId = (endpoints.data?.results || []).find(
      (x) => x.name === endpointName,
    )?.id
    setSaving(true)
    try {
      const res = await integrationsApi.webhookEndpoints.fireEvent({
        event: event.trim(),
        endpoint_id: endpointId || null,
        payload: parsedPayload,
      })
      toast(`Queued ${res.queued} delivery(ies)`, 'success')
      setEvent('')
      setEndpointName('')
      onClose()
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Fire failed', 'error')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal open={open} onClose={onClose} title="Fire test event">
      <form onSubmit={onSubmit} style={{ display: 'grid', gap: 12 }}>
        <Input label="Event" required value={event} onChange={(e) => setEvent(e.target.value)} placeholder="candidate.created" />
        <Select
          label="Endpoint (optional — all endpoints if empty)"
          value={endpointName}
          onChange={(e) => setEndpointName(e.target.value)}
          placeholder="All endpoints"
          options={(endpoints.data?.results || []).map((x) => ({ value: x.name, label: x.name }))}
        />
        <Textarea label="Payload (JSON)" value={payload} onChange={(e) => setPayload(e.target.value)} />
        <Button type="submit" loading={saving}>
          <Send size={15} />
          Fire event
        </Button>
      </form>
    </Modal>
  )
}

/* ---------------------------------------------------------------------------
 * Webhook create / edit form
 * ------------------------------------------------------------------------ */

export function WebhookFormPage() {
  const { id } = useParams()
  const isEdit = Boolean(id)
  const navigate = useNavigate()
  const { toast } = useToast()
  const [form, setForm] = useState({ name: '', url: '', events: '', is_active: true })
  const [loading, setLoading] = useState(isEdit)
  const [saving, setSaving] = useState(false)
  const [secret, setSecret] = useState('')

  useEffect(() => {
    if (isEdit && id) {
      setLoading(true)
      integrationsApi.webhookEndpoints
        .get(id)
        .then((e) =>
          setForm({
            name: e.name,
            url: e.url,
            events: (e.events || []).join(', '),
            is_active: e.is_active,
          }),
        )
        .catch((err) => toast(err instanceof ApiError ? err.message : 'Failed to load', 'error'))
        .finally(() => setLoading(false))
    }
  }, [id, isEdit, toast])

  function set<K extends keyof typeof form>(key: K, value: (typeof form)[K]) {
    setForm((f) => ({ ...f, [key]: value }))
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    if (!form.name.trim() || !form.url.trim()) {
      toast('Name and URL are required', 'error')
      return
    }
    const events = form.events
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean)
    setSaving(true)
    try {
      if (isEdit) {
        const updated = await integrationsApi.webhookEndpoints.update(id!, {
          name: form.name.trim(),
          url: form.url.trim(),
          events,
          is_active: form.is_active,
        })
        toast('Webhook updated', 'success')
        navigate(`/app/integrations/webhooks/${updated.id}`)
      } else {
        const created = await integrationsApi.webhookEndpoints.create({
          name: form.name.trim(),
          url: form.url.trim(),
          events,
          is_active: form.is_active,
        })
        setSecret(created.secret)
      }
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Save failed', 'error')
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div style={{ padding: 64, display: 'grid', placeItems: 'center' }}>
        <Spinner label="Loading…" />
      </div>
    )
  }

  return (
    <div className="hf-page">
      <PageHeader
        title={isEdit ? 'Edit webhook' : 'New webhook'}
        subtitle="HireFlux will POST matching events to this URL with a signing header."
      />
      <form onSubmit={onSubmit}>
        <Card>
          <div style={{ display: 'grid', gap: 14 }}>
            <Input label="Name" required value={form.name} onChange={(e) => set('name', e.target.value)} placeholder="e.g. Slack alerts" />
            <Input label="URL" required type="url" value={form.url} onChange={(e) => set('url', e.target.value)} placeholder="https://example.com/hooks/hireflux" />
            <Input
              label="Events (comma-separated)"
              value={form.events}
              onChange={(e) => set('events', e.target.value)}
              placeholder="candidate.created, offer.accepted"
              hint="Leave empty to receive all events."
            />
            <label style={{ display: 'flex', gap: 8, alignItems: 'center', fontSize: '0.88rem' }}>
              <input
                type="checkbox"
                checked={form.is_active}
                onChange={(e) => set('is_active', e.target.checked)}
              />
              Endpoint active
            </label>
            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
              <Button type="button" variant="outline" onClick={() => navigate(-1)}>
                Cancel
              </Button>
              <Button type="submit" loading={saving}>
                {isEdit ? 'Save changes' : 'Create webhook'}
              </Button>
            </div>
          </div>
        </Card>
      </form>

      <SecretModal
        open={Boolean(secret)}
        title="Webhook signing secret"
        message="Copy this secret now — it is only shown once. Use it to verify the X-HireFlux-Signature header on incoming requests."
        secret={secret}
        onClose={() => navigate('/app/integrations/webhooks')}
      />
    </div>
  )
}

/* ---------------------------------------------------------------------------
 * Webhook detail
 * ------------------------------------------------------------------------ */

export function WebhookDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { toast } = useToast()
  const [tab, setTab] = useState('overview')
  const [page, setPage] = useState(1)
  const [acting, setActing] = useState<string | null>(null)
  const [fireOpen, setFireOpen] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [secretModal, setSecretModal] = useState<{ open: boolean; secret: string }>({
    open: false,
    secret: '',
  })

  const endpoint = useApi(() => integrationsApi.webhookEndpoints.get(id), [id], {
    enabled: Boolean(id),
  })
  const deliveries = useApi(
    () => integrationsApi.webhookDeliveries.list({ endpoint: id, page, page_size: 10 }),
    [id, page],
    { enabled: Boolean(id) },
  )
  useReloadOnChange(deliveries.reload, [page])

  async function rotateSecret() {
    setActing('rotate')
    try {
      const res = await integrationsApi.webhookEndpoints.rotateSecret(id!)
      setSecretModal({ open: true, secret: res.secret })
      toast('Secret rotated — copy it now', 'success')
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Rotate failed', 'error')
    } finally {
      setActing(null)
    }
  }

  async function redeliver(deliveryId: string) {
    setActing(deliveryId)
    try {
      await integrationsApi.webhookDeliveries.redeliver(deliveryId)
      toast('Delivery re-queued', 'success')
      deliveries.reload()
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Redeliver failed', 'error')
    } finally {
      setActing(null)
    }
  }

  async function retryFailed() {
    setActing('retry')
    try {
      const res = await integrationsApi.webhookDeliveries.retryFailed()
      toast(`Queued ${res.queued} failed delivery(ies)`, 'success')
      deliveries.reload()
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Retry failed', 'error')
    } finally {
      setActing(null)
    }
  }

  if (endpoint.loading) {
    return (
      <div style={{ padding: 64, display: 'grid', placeItems: 'center' }}>
        <Spinner label="Loading webhook…" />
      </div>
    )
  }
  if (endpoint.error || !endpoint.data) {
    return (
      <EmptyState
        title="Webhook not found"
        description={endpoint.error || 'This webhook may have been deleted.'}
        actionLabel="Back to webhooks"
        onAction={() => navigate('/app/integrations/webhooks')}
      />
    )
  }
  const e = endpoint.data

  return (
    <div className="hf-page">
      <PageHeader
        title={e.name}
        subtitle={e.url}
        actions={
          <>
            <Badge tone={boolTone(e.is_active)}>{e.is_active ? 'Active' : 'Inactive'}</Badge>
            <Button variant="outline" onClick={() => setFireOpen(true)}>
              <Send size={15} />
              Fire event
            </Button>
            <Button variant="outline" loading={acting === 'rotate'} onClick={() => void rotateSecret()}>
              <RotateCw size={15} />
              Rotate secret
            </Button>
            <Button variant="outline" onClick={() => navigate(`/app/integrations/webhooks/${id}/edit`)}>
              Edit
            </Button>
            <Button variant="danger" onClick={() => setConfirmDelete(true)}>
              <Trash2 size={15} />
            </Button>
          </>
        }
      />

      <Tabs
        value={tab}
        onChange={setTab}
        items={[
          { id: 'overview', label: 'Overview' },
          { id: 'deliveries', label: 'Deliveries', count: deliveries.data?.count },
        ]}
      />

      {tab === 'overview' && (
        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 16 }}>
          <Card>
            <h3 style={{ margin: '0 0 12px' }}>Endpoint</h3>
            <dl style={{ display: 'grid', gap: 10, margin: 0, fontSize: '0.88rem' }}>
              <Row label="URL" value={e.url} />
              <Row label="Status" value={e.is_active ? 'Active' : 'Inactive'} />
              <Row label="Created" value={formatDate(e.created_at)} />
              <Row label="Updated" value={formatDate(e.updated_at)} />
            </dl>
            <h3 style={{ margin: '18px 0 8px' }}>Events</h3>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
              {(e.events || []).length ? (
                (e.events || []).map((ev) => (
                  <Badge key={ev} tone="teal">
                    {ev}
                  </Badge>
                ))
              ) : (
                <span className="hf-muted">All events</span>
              )}
            </div>
          </Card>
          <Card>
            <h3 style={{ margin: '0 0 12px' }}>Recent deliveries</h3>
            <Timeline
              items={(deliveries.data?.results || []).slice(0, 5).map((d) => ({
                id: d.id,
                title: d.event,
                description:
                  d.response_body ||
                  (d.status === 'pending' ? 'Queued for delivery' : 'No response body'),
                at: d.created_at,
                meta: `${titleCase(d.status)} · ${d.attempts} attempt(s)`,
              }))}
            />
          </Card>
        </div>
      )}

      {tab === 'deliveries' && (
        <Card padding={0}>
          <div
            style={{
              display: 'flex',
              justifyContent: 'flex-end',
              padding: '0.75rem 1rem',
              borderBottom: '1px solid var(--hf-border)',
            }}
          >
            <Button size="sm" variant="outline" loading={acting === 'retry'} onClick={() => void retryFailed()}>
              <RefreshCw size={14} />
              Retry failed
            </Button>
          </div>
          <DataTable
            loading={deliveries.loading}
            columns={[
              { key: 'event', header: 'Event', render: (d) => <strong>{d.event}</strong> },
              {
                key: 'status',
                header: 'Status',
                render: (d) => <Badge tone={deliveryTone(d.status)}>{titleCase(d.status)}</Badge>,
              },
              { key: 'attempts', header: 'Attempts', render: (d) => d.attempts },
              {
                key: 'response',
                header: 'Response',
                render: (d) => (d.response_status != null ? String(d.response_status) : '—'),
              },
              { key: 'next', header: 'Next attempt', render: (d) => formatDateTime(d.next_attempt_at) },
              { key: 'created', header: 'Created', render: (d) => formatDateTime(d.created_at) },
              {
                key: 'actions',
                header: 'Actions',
                render: (d) => (
                  <div style={{ display: 'flex', gap: 6 }} onClick={(ev) => ev.stopPropagation()}>
                    <Button
                      size="sm"
                      variant="outline"
                      loading={acting === d.id}
                      disabled={acting !== null}
                      onClick={() => void redeliver(d.id)}
                    >
                      <RefreshCw size={13} />
                      Redeliver
                    </Button>
                  </div>
                ),
              },
            ]}
            rows={deliveries.data?.results || []}
            rowKey={(d) => d.id}
            emptyTitle="No deliveries yet"
            emptyDescription="Deliveries appear here once events are fired at this endpoint."
          />
          {deliveries.data && (
            <Pagination page={page} pageSize={10} total={deliveries.data.count} onChange={setPage} />
          )}
        </Card>
      )}

      <FireEventModal open={fireOpen} onClose={() => setFireOpen(false)} />
      <SecretModal
        open={secretModal.open}
        title="Webhook signing secret"
        message="Copy this secret now — it is only shown once."
        secret={secretModal.secret}
        onClose={() => setSecretModal((s) => ({ ...s, open: false }))}
      />
      <ConfirmDialog
        open={confirmDelete}
        title="Delete webhook endpoint"
        message={`Delete "${e.name}"? Deliveries will stop immediately.`}
        confirmLabel="Delete"
        danger
        loading={acting === 'delete'}
        onCancel={() => setConfirmDelete(false)}
        onConfirm={() => {
          setActing('delete')
          integrationsApi.webhookEndpoints
            .remove(id!)
            .then(() => {
              toast('Webhook deleted', 'success')
              navigate('/app/integrations/webhooks')
            })
            .catch((err) => toast(err instanceof ApiError ? err.message : 'Delete failed', 'error'))
            .finally(() => setActing(null))
        }}
      />
    </div>
  )
}

function SecretModal({
  open,
  title,
  message,
  secret,
  onClose,
}: {
  open: boolean
  title: string
  message: string
  secret: string
  onClose: () => void
}) {
  const { toast } = useToast()
  return (
    <Modal open={open} onClose={onClose} title={title} width={560}>
      <p className="hf-muted">{message}</p>
      <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
        <Input readOnly value={secret} style={{ fontFamily: 'monospace', fontSize: '0.8rem' }} />
        <Button
          variant="outline"
          onClick={() => {
            void copyText(secret).then((ok) =>
              toast(ok ? 'Secret copied' : 'Copy failed', ok ? 'success' : 'error'),
            )
          }}
        >
          <Copy size={15} />
        </Button>
      </div>
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 14 }}>
        <Button onClick={onClose}>Done</Button>
      </div>
    </Modal>
  )
}

/* ---------------------------------------------------------------------------
 * API keys
 * ------------------------------------------------------------------------ */

export function ApiKeysPage() {
  const { toast } = useToast()
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [active, setActive] = useState('')
  const [acting, setActing] = useState<string | null>(null)
  const [createOpen, setCreateOpen] = useState(false)
  const [keyModal, setKeyModal] = useState<{ open: boolean; key: string; label: string }>({
    open: false,
    key: '',
    label: '',
  })
  const [confirmRevoke, setConfirmRevoke] = useState<{ id: string; name: string } | null>(null)
  const [confirmDelete, setConfirmDelete] = useState<{ id: string; name: string } | null>(null)

  const keys = useApi(
    () =>
      integrationsApi.apiKeys.list({
        page,
        page_size: 10,
        search: search || undefined,
        is_active: active || undefined,
      }),
    [page, search, active],
    { enabled: true },
  )
  useReloadOnChange(keys.reload, [page, search, active])

  async function regenerate(key: { id: string; name: string }) {
    setActing(key.id)
    try {
      const res = await integrationsApi.apiKeys.regenerate(key.id)
      setKeyModal({ open: true, key: res.key, label: key.name })
      toast('Key regenerated — copy it now', 'success')
      keys.reload()
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Regenerate failed', 'error')
    } finally {
      setActing(null)
    }
  }

  return (
    <div className="hf-page">
      <PageHeader
        title="API keys"
        subtitle="Programmatic access to the HireFlux API. Keys are shown once at creation."
        actions={
          <Button onClick={() => setCreateOpen(true)}>
            <Plus size={16} />
            New API key
          </Button>
        }
      />

      <Card padding="1rem">
        <FilterBar
          search={search}
          onSearchChange={(v) => {
            setPage(1)
            setSearch(v)
          }}
          searchPlaceholder="Search keys…"
          filters={[
            {
              key: 'active',
              label: 'Status',
              value: active,
              onChange: (v) => {
                setPage(1)
                setActive(activeToApi[v] ?? '')
              },
              options: ACTIVE_FILTERS,
            },
          ]}
          onClear={() => {
            setSearch('')
            setActive('')
            setPage(1)
          }}
        />
      </Card>

      {keys.error && (
        <Card>
          <p style={{ color: 'var(--hf-danger)' }}>{keys.error}</p>
        </Card>
      )}

      <Card padding={0}>
        <DataTable
          loading={keys.loading}
          columns={[
            { key: 'name', header: 'Name', render: (k) => <strong>{k.name}</strong> },
            {
              key: 'key',
              header: 'Key',
              render: (k) => (
                <span style={{ fontFamily: 'monospace', fontSize: '0.8rem' }}>
                  {k.key_prefix ? `${k.key_prefix}••••••••` : '—'}
                </span>
              ),
            },
            {
              key: 'scopes',
              header: 'Scopes',
              render: (k) => (
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                  {(k.scopes || []).length ? (
                    (k.scopes || []).map((s) => (
                      <Badge key={s} tone="info">
                        {s}
                      </Badge>
                    ))
                  ) : (
                    <span className="hf-muted">All scopes</span>
                  )}
                </div>
              ),
            },
            {
              key: 'active',
              header: 'Active',
              render: (k) => <Badge tone={boolTone(k.is_active)}>{k.is_active ? 'Active' : 'Revoked'}</Badge>,
            },
            { key: 'expires', header: 'Expires', render: (k) => formatDate(k.expires_at) },
            { key: 'used', header: 'Last used', render: (k) => formatDateTime(k.last_used_at) },
            {
              key: 'actions',
              header: 'Actions',
              render: (k) => (
                <div style={{ display: 'flex', gap: 6 }} onClick={(ev) => ev.stopPropagation()}>
                  <Button
                    size="sm"
                    variant="outline"
                    loading={acting === k.id}
                    disabled={acting !== null}
                    onClick={() => void regenerate(k)}
                  >
                    <RotateCw size={13} />
                    Regenerate
                  </Button>
                  {k.is_active && (
                    <Button size="sm" variant="outline" onClick={() => setConfirmRevoke(k)}>
                      Revoke
                    </Button>
                  )}
                  <Button size="sm" variant="danger" onClick={() => setConfirmDelete(k)}>
                    <Trash2 size={13} />
                  </Button>
                </div>
              ),
            },
          ]}
          rows={keys.data?.results || []}
          rowKey={(k) => k.id}
          emptyTitle="No API keys"
          emptyDescription="Create a key to authenticate programmatic access."
        />
        {keys.data && (
          <Pagination page={page} pageSize={10} total={keys.data.count} onChange={setPage} />
        )}
      </Card>

      <ApiKeyCreateModal open={createOpen} onClose={() => setCreateOpen(false)} onCreated={keys.reload} />
      <KeyRevealModal
        open={keyModal.open}
        label={keyModal.label}
        keyValue={keyModal.key}
        onClose={() => setKeyModal((s) => ({ ...s, open: false }))}
      />
      <ConfirmDialog
        open={Boolean(confirmRevoke)}
        title="Revoke API key"
        message={`Revoke "${confirmRevoke?.name}"? Requests using this key will stop working immediately.`}
        confirmLabel="Revoke"
        danger
        loading={acting === 'revoke'}
        onCancel={() => setConfirmRevoke(null)}
        onConfirm={() => {
          if (!confirmRevoke) return
          setActing('revoke')
          integrationsApi.apiKeys
            .revoke(confirmRevoke.id)
            .then(() => {
              toast('Key revoked', 'success')
              keys.reload()
              setConfirmRevoke(null)
            })
            .catch((err) => toast(err instanceof ApiError ? err.message : 'Revoke failed', 'error'))
            .finally(() => setActing(null))
        }}
      />
      <ConfirmDialog
        open={Boolean(confirmDelete)}
        title="Delete API key"
        message={`Delete "${confirmDelete?.name}"? This cannot be undone.`}
        confirmLabel="Delete"
        danger
        loading={acting === 'delete'}
        onCancel={() => setConfirmDelete(null)}
        onConfirm={() => {
          if (!confirmDelete) return
          setActing('delete')
          integrationsApi.apiKeys
            .remove(confirmDelete.id)
            .then(() => {
              toast('Key deleted', 'success')
              keys.reload()
              setConfirmDelete(null)
            })
            .catch((err) => toast(err instanceof ApiError ? err.message : 'Delete failed', 'error'))
            .finally(() => setActing(null))
        }}
      />
    </div>
  )
}

function ApiKeyCreateModal({
  open,
  onClose,
  onCreated,
}: {
  open: boolean
  onClose: () => void
  onCreated: () => void
}) {
  const { toast } = useToast()
  const [name, setName] = useState('')
  const [scopes, setScopes] = useState('')
  const [expiresAt, setExpiresAt] = useState('')
  const [isActive, setIsActive] = useState(true)
  const [saving, setSaving] = useState(false)
  const [reveal, setReveal] = useState('')
  const [revealLabel, setRevealLabel] = useState('')

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    if (!name.trim()) {
      toast('Name is required', 'error')
      return
    }
    const createdName = name.trim()
    setSaving(true)
    try {
      const res = await integrationsApi.apiKeys.create({
        name: createdName,
        scopes: scopes
          .split(',')
          .map((s) => s.trim())
          .filter(Boolean),
        is_active: isActive,
        expires_at: expiresAt || null,
      })
      setReveal(res.key)
      setRevealLabel(createdName)
      onCreated()
      setName('')
      setScopes('')
      setExpiresAt('')
      setIsActive(true)
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Create failed', 'error')
    } finally {
      setSaving(false)
    }
  }

  return (
    <>
      <Modal open={open && !reveal} onClose={onClose} title="New API key">
        <form onSubmit={onSubmit} style={{ display: 'grid', gap: 12 }}>
          <Input label="Name" required value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. CI pipeline" />
          <Input
            label="Scopes (comma-separated, optional)"
            value={scopes}
            onChange={(e) => setScopes(e.target.value)}
            placeholder="jobs.read, candidates.write"
            hint="Leave empty for full access."
          />
          <Input label="Expires (optional)" type="date" value={expiresAt} onChange={(e) => setExpiresAt(e.target.value)} />
          <label style={{ display: 'flex', gap: 8, alignItems: 'center', fontSize: '0.88rem' }}>
            <input type="checkbox" checked={isActive} onChange={(e) => setIsActive(e.target.checked)} />
            Active immediately
          </label>
          <Button type="submit" loading={saving}>
            Create key
          </Button>
        </form>
      </Modal>
      <KeyRevealModal
        open={Boolean(reveal)}
        label={revealLabel || 'API key'}
        keyValue={reveal}
        onClose={() => {
          setReveal('')
          setRevealLabel('')
          onClose()
        }}
      />
    </>
  )
}

function KeyRevealModal({
  open,
  label,
  keyValue,
  onClose,
}: {
  open: boolean
  label: string
  keyValue: string
  onClose: () => void
}) {
  const { toast } = useToast()
  return (
    <Modal open={open} onClose={onClose} title={`API key: ${label}`} width={560}>
      <p className="hf-muted">
        Copy this key now — it is only shown once and cannot be retrieved later.
      </p>
      <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
        <Input readOnly value={keyValue} style={{ fontFamily: 'monospace', fontSize: '0.8rem' }} />
        <Button
          variant="outline"
          onClick={() => {
            void copyText(keyValue).then((ok) =>
              toast(ok ? 'Key copied' : 'Copy failed', ok ? 'success' : 'error'),
            )
          }}
        >
          <Copy size={15} />
        </Button>
      </div>
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 14 }}>
        <Button onClick={onClose}>Done</Button>
      </div>
    </Modal>
  )
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}>
      <dt className="hf-muted">{label}</dt>
      <dd style={{ margin: 0, fontWeight: 600, wordBreak: 'break-word', textAlign: 'right' }}>
        {value}
      </dd>
    </div>
  )
}
