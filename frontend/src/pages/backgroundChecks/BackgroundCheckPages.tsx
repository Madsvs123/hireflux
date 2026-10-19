/**
 * Background check pages (packages, requests, reports, disputes, providers).
 *
 * Exported components & suggested routes:
 *  - BackgroundCheckPackagesPage      → /app/background-checks
 *  - ScreeningProvidersPage           → /app/background-checks/providers
 *  - BackgroundCheckRequestsPage      → /app/background-checks/requests
 *  - BackgroundCheckRequestFormPage   → /app/background-checks/requests/new
 *  - BackgroundCheckRequestDetailPage → /app/background-checks/requests/:id
 *  - BackgroundCheckReportsPage       → /app/background-checks/reports
 *  - CheckDisputesPage                → /app/background-checks/disputes
 */
import { useState, type FormEvent } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { Plus } from 'lucide-react'
import { candidatesApi } from '../../api/candidates'
import { jobsApi } from '../../api/jobs'
import {
  backgroundCheckPackagesApi,
  backgroundCheckReportsApi,
  backgroundCheckRequestsApi,
  checkDisputesApi,
  screeningProvidersApi,
  type BackgroundCheckPackage,
  type BackgroundCheckReport,
  type BackgroundCheckRequest,
  type CheckDispute,
  type ReportStatus,
  type ScreeningProvider,
} from '../../api/backgroundChecks'
import { useApi } from '../../hooks/useApi'
import { PageHeader } from '../../components/layout/PageHeader'
import {
  Badge,
  Button,
  Card,
  ConfirmDialog,
  DataTable,
  EmptyState,
  Input,
  Modal,
  Pagination,
  Select,
  Spinner,
  Tabs,
  Textarea,
  Timeline,
  useToast,
} from '../../components/ui'
import { formatCurrency, formatDate, formatDateTime, titleCase } from '../../utils/format'
import { ApiError } from '../../api/http'

const CHECK_STATUS_OPTIONS = [
  { value: 'draft', label: 'Draft' },
  { value: 'submitted', label: 'Submitted' },
  { value: 'in_progress', label: 'In progress' },
  { value: 'completed', label: 'Completed' },
  { value: 'on_hold', label: 'On hold' },
  { value: 'cancelled', label: 'Cancelled' },
]

// ---------------------------------------------------------------------------
// Packages
// ---------------------------------------------------------------------------

export function BackgroundCheckPackagesPage() {
  const navigate = useNavigate()
  const { toast } = useToast()
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<BackgroundCheckPackage | null>(null)
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [checkTypes, setCheckTypes] = useState('')
  const [price, setPrice] = useState('')
  const [turnaroundDays, setTurnaroundDays] = useState(5)
  const [isActive, setIsActive] = useState(true)
  const [saving, setSaving] = useState(false)
  const [removing, setRemoving] = useState<BackgroundCheckPackage | null>(null)
  const { data, loading, error, reload } = useApi(
    () => backgroundCheckPackagesApi.list({ page, page_size: 20, search: search || undefined }),
    [page, search],
  )

  function openCreate() {
    setEditing(null)
    setName('')
    setDescription('')
    setCheckTypes('')
    setPrice('')
    setTurnaroundDays(5)
    setIsActive(true)
    setModalOpen(true)
  }

  function openEdit(pkg: BackgroundCheckPackage) {
    setEditing(pkg)
    setName(pkg.name)
    setDescription(pkg.description)
    setCheckTypes((pkg.check_types || []).join(', '))
    setPrice(String(pkg.price ?? ''))
    setTurnaroundDays(pkg.turnaround_days)
    setIsActive(pkg.is_active)
    setModalOpen(true)
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setSaving(true)
    const payload = {
      name,
      description,
      check_types: checkTypes.split(',').map((s) => s.trim()).filter(Boolean),
      price: price || '0',
      turnaround_days: Number(turnaroundDays) || 5,
      is_active: isActive,
    }
    try {
      if (editing) {
        await backgroundCheckPackagesApi.update(editing.id, payload)
        toast('Package updated', 'success')
      } else {
        await backgroundCheckPackagesApi.create(payload)
        toast('Package created', 'success')
      }
      setModalOpen(false)
      reload()
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Save failed', 'error')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="hf-page">
      <PageHeader
        title="Background check packages"
        subtitle="Bundles of check types (identity, criminal, employment…) with pricing."
        actions={
          <>
            <Button variant="outline" onClick={() => navigate('/app/background-checks/providers')}>Providers</Button>
            <Button leftIcon={<Plus size={16} />} onClick={openCreate}>New package</Button>
          </>
        }
      />

      <Card padding="1rem">
        <Input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search packages…" />
      </Card>

      {error && (
        <Card>
          <p style={{ color: 'var(--hf-danger)' }}>{error}</p>
          <Button variant="outline" size="sm" onClick={reload} style={{ marginTop: 8 }}>Retry</Button>
        </Card>
      )}

      <Card padding={0}>
        <DataTable
          loading={loading}
          columns={[
            { key: 'name', header: 'Name', render: (p) => p.name },
            { key: 'description', header: 'Description', render: (p) => p.description || '—' },
            {
              key: 'checks',
              header: 'Check types',
              render: (p) => (
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                  {(p.check_types || []).map((c) => <Badge key={c} tone="teal">{c}</Badge>)}
                </div>
              ),
            },
            { key: 'price', header: 'Price', render: (p) => formatCurrency(p.price) },
            { key: 'turnaround', header: 'Turnaround', render: (p) => `${p.turnaround_days}d` },
            {
              key: 'active',
              header: 'Active',
              render: (p) => <Badge tone={p.is_active ? 'success' : 'neutral'}>{p.is_active ? 'Active' : 'Inactive'}</Badge>,
            },
            {
              key: 'actions',
              header: '',
              render: (p) => (
                <div style={{ display: 'flex', gap: 6 }}>
                  <Button variant="outline" size="sm" onClick={(e) => { e.stopPropagation(); openEdit(p) }}>Edit</Button>
                  <Button variant="ghost" size="sm" onClick={(e) => { e.stopPropagation(); setRemoving(p) }}>Delete</Button>
                </div>
              ),
            },
          ]}
          rows={data?.results || []}
          rowKey={(p) => p.id}
          emptyTitle="No packages"
          emptyDescription="Create a background check package to offer to candidates."
        />
        {data && <Pagination page={page} pageSize={20} total={data.count} onChange={setPage} />}
      </Card>

      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title={editing ? 'Edit package' : 'New package'} width={560}>
        <form onSubmit={onSubmit} style={{ display: 'grid', gap: 12 }}>
          <Input label="Name" required value={name} onChange={(e) => setName(e.target.value)} />
          <Textarea label="Description" value={description} onChange={(e) => setDescription(e.target.value)} />
          <Input
            label="Check types (comma-separated)"
            value={checkTypes}
            onChange={(e) => setCheckTypes(e.target.value)}
            placeholder="identity, criminal, employment"
          />
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <Input label="Price" type="number" step="0.01" min={0} value={price} onChange={(e) => setPrice(e.target.value)} />
            <Input
              label="Turnaround (days)"
              type="number"
              min={1}
              value={turnaroundDays}
              onChange={(e) => setTurnaroundDays(Number(e.target.value))}
            />
          </div>
          <label style={{ display: 'flex', gap: 8, alignItems: 'center', fontSize: '0.88rem' }}>
            <input type="checkbox" checked={isActive} onChange={(e) => setIsActive(e.target.checked)} />
            Active
          </label>
          <Button type="submit" loading={saving}>{editing ? 'Save changes' : 'Create package'}</Button>
        </form>
      </Modal>

      <ConfirmDialog
        open={Boolean(removing)}
        title="Delete package"
        message={`Delete "${removing?.name}"? Existing requests keep their data.`}
        confirmLabel="Delete"
        danger
        onCancel={() => setRemoving(null)}
        onConfirm={() => {
          if (!removing) return
          backgroundCheckPackagesApi
            .remove(removing.id)
            .then(() => { toast('Package deleted', 'success'); setRemoving(null); reload() })
            .catch((err) => toast(err instanceof ApiError ? err.message : 'Delete failed', 'error'))
        }}
      />
    </div>
  )
}

// ---------------------------------------------------------------------------
// Providers
// ---------------------------------------------------------------------------

export function ScreeningProvidersPage() {
  const { toast } = useToast()
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<ScreeningProvider | null>(null)
  const [name, setName] = useState('')
  const [apiEndpoint, setApiEndpoint] = useState('')
  const [supportedChecks, setSupportedChecks] = useState('')
  const [isActive, setIsActive] = useState(true)
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState<string | null>(null)
  const [testResult, setTestResult] = useState<Record<string, string | number | boolean> | null>(null)
  const { data, loading, error, reload } = useApi(
    () => screeningProvidersApi.list({ page, page_size: 20, search: search || undefined }),
    [page, search],
  )

  function openCreate() {
    setEditing(null)
    setName('')
    setApiEndpoint('')
    setSupportedChecks('')
    setIsActive(true)
    setModalOpen(true)
  }

  function openEdit(p: ScreeningProvider) {
    setEditing(p)
    setName(p.name)
    setApiEndpoint(p.api_endpoint)
    setSupportedChecks((p.supported_checks || []).join(', '))
    setIsActive(p.is_active)
    setModalOpen(true)
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setSaving(true)
    const payload = {
      name,
      api_endpoint: apiEndpoint,
      supported_checks: supportedChecks.split(',').map((s) => s.trim()).filter(Boolean),
      is_active: isActive,
    }
    try {
      if (editing) {
        await screeningProvidersApi.update(editing.id, payload)
        toast('Provider updated', 'success')
      } else {
        await screeningProvidersApi.create(payload)
        toast('Provider created', 'success')
      }
      setModalOpen(false)
      reload()
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Save failed', 'error')
    } finally {
      setSaving(false)
    }
  }

  async function runTest(p: ScreeningProvider) {
    setTesting(p.id)
    setTestResult(null)
    try {
      const result = await screeningProvidersApi.test(p.id)
      setTestResult(result as unknown as Record<string, string | number | boolean>)
      toast(result.ok ? 'Provider reachable' : 'Provider test failed', result.ok ? 'success' : 'error')
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Test failed', 'error')
    } finally {
      setTesting(null)
    }
  }

  return (
    <div className="hf-page">
      <PageHeader
        title="Screening providers"
        subtitle="Background check provider connections used when submitting requests."
        actions={
          <Button leftIcon={<Plus size={16} />} onClick={openCreate}>New provider</Button>
        }
      />

      <Card padding="1rem">
        <Input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search providers…" />
      </Card>

      {error && (
        <Card>
          <p style={{ color: 'var(--hf-danger)' }}>{error}</p>
          <Button variant="outline" size="sm" onClick={reload} style={{ marginTop: 8 }}>Retry</Button>
        </Card>
      )}

      <Card padding={0}>
        <DataTable
          loading={loading}
          columns={[
            { key: 'name', header: 'Name', render: (p) => p.name },
            { key: 'key', header: 'Key', render: (p) => <Badge tone="teal">{p.key}</Badge> },
            { key: 'endpoint', header: 'API endpoint', render: (p) => p.api_endpoint || '—' },
            {
              key: 'active',
              header: 'Active',
              render: (p) => <Badge tone={p.is_active ? 'success' : 'neutral'}>{p.is_active ? 'Active' : 'Inactive'}</Badge>,
            },
            {
              key: 'actions',
              header: '',
              render: (p) => (
                <div style={{ display: 'flex', gap: 6 }}>
                  <Button size="sm" variant="outline" loading={testing === p.id} onClick={(e) => { e.stopPropagation(); void runTest(p) }}>
                    Test
                  </Button>
                  <Button size="sm" variant="outline" onClick={(e) => { e.stopPropagation(); openEdit(p) }}>Edit</Button>
                </div>
              ),
            },
          ]}
          rows={data?.results || []}
          rowKey={(p) => p.id}
          emptyTitle="No providers"
          emptyDescription="Add a screening provider to submit checks against."
        />
        {data && <Pagination page={page} pageSize={20} total={data.count} onChange={setPage} />}
      </Card>

      {testResult && (
        <Card title="Last test result">
          <pre className="hf-muted" style={{ fontSize: '0.85rem', margin: 0 }}>{JSON.stringify(testResult, null, 2)}</pre>
        </Card>
      )}

      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title={editing ? 'Edit provider' : 'New provider'}>
        <form onSubmit={onSubmit} style={{ display: 'grid', gap: 12 }}>
          <Input label="Name" required value={name} onChange={(e) => setName(e.target.value)} />
          <Input label="API endpoint" value={apiEndpoint} onChange={(e) => setApiEndpoint(e.target.value)} placeholder="https://provider.example.com/webhook" />
          <Input
            label="Supported checks (comma-separated)"
            value={supportedChecks}
            onChange={(e) => setSupportedChecks(e.target.value)}
            placeholder="identity, criminal"
          />
          <label style={{ display: 'flex', gap: 8, alignItems: 'center', fontSize: '0.88rem' }}>
            <input type="checkbox" checked={isActive} onChange={(e) => setIsActive(e.target.checked)} />
            Active
          </label>
          <Button type="submit" loading={saving}>{editing ? 'Save changes' : 'Create provider'}</Button>
        </form>
      </Modal>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Requests
// ---------------------------------------------------------------------------

export function BackgroundCheckRequestsPage() {
  const navigate = useNavigate()
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('')
  const { data, loading, error, reload } = useApi(
    () =>
      backgroundCheckRequestsApi.list({
        page,
        page_size: 20,
        search: search || undefined,
        status: status || undefined,
      }),
    [page, search, status],
  )

  return (
    <div className="hf-page">
      <PageHeader
        title="Background check requests"
        subtitle="Submit, track, and review background checks for candidates."
        actions={
          <Button leftIcon={<Plus size={16} />} onClick={() => navigate('/app/background-checks/requests/new')}>
            New request
          </Button>
        }
      />

      <Card padding="1rem">
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, alignItems: 'flex-end' }}>
          <div style={{ flex: '1 1 260px', minWidth: 220 }}>
            <Input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search by candidate…" />
          </div>
          <div style={{ minWidth: 150 }}>
            <Select
              label="Status"
              value={status}
              onChange={(e) => setStatus(e.target.value)}
              options={[{ value: '', label: 'All' }, ...CHECK_STATUS_OPTIONS]}
            />
          </div>
          <Button variant="ghost" size="sm" onClick={() => { setSearch(''); setStatus(''); setPage(1) }}>
            Clear
          </Button>
        </div>
      </Card>

      {error && (
        <Card>
          <p style={{ color: 'var(--hf-danger)' }}>{error}</p>
          <Button variant="outline" size="sm" onClick={reload} style={{ marginTop: 8 }}>Retry</Button>
        </Card>
      )}

      <Card padding={0}>
        <DataTable
          loading={loading}
          columns={[
            {
              key: 'candidate',
              header: 'Candidate',
              render: (r) => (
                <div>
                  <Link to={`/app/background-checks/requests/${r.id}`} style={{ fontWeight: 650, textDecoration: 'none' }}>
                    {r.candidate_name}
                  </Link>
                  <div className="hf-subtle" style={{ fontSize: '0.75rem' }}>{r.candidate_email_actual || r.candidate_email}</div>
                </div>
              ),
            },
            { key: 'package', header: 'Package', render: (r) => r.package_name || '—' },
            { key: 'job', header: 'Job', render: (r) => r.job_title || '—' },
            { key: 'status', header: 'Status', render: (r) => <Badge status={r.status} /> },
            { key: 'provider', header: 'Provider', render: (r) => r.provider_name || '—' },
            {
              key: 'report',
              header: 'Report',
              render: (r) =>
                r.latest_report ? <Badge status={r.latest_report.status} tone="info">{r.latest_report.status}</Badge> : '—',
            },
            { key: 'created', header: 'Created', render: (r) => formatDate(r.created_at) },
          ]}
          rows={data?.results || []}
          rowKey={(r) => r.id}
          emptyTitle="No requests"
          emptyDescription="Create a background check request for a candidate."
          onRowClick={(r) => navigate(`/app/background-checks/requests/${r.id}`)}
        />
        {data && <Pagination page={page} pageSize={20} total={data.count} onChange={setPage} />}
      </Card>
    </div>
  )
}

export function BackgroundCheckRequestFormPage() {
  const navigate = useNavigate()
  const { toast } = useToast()
  const [candidateId, setCandidateId] = useState('')
  const [jobId, setJobId] = useState('')
  const [packageId, setPackageId] = useState('')
  const [candidateEmail, setCandidateEmail] = useState('')
  const [candidatePhone, setCandidatePhone] = useState('')
  const [saving, setSaving] = useState(false)
  const candidates = useApi(() => candidatesApi.list({ page_size: 100 }), [])
  const jobs = useApi(() => jobsApi.list({ page_size: 100 }), [])
  const packages = useApi(() => backgroundCheckPackagesApi.list({ page_size: 100, is_active: true }), [])

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    if (!candidateId) {
      toast('Select a candidate', 'error')
      return
    }
    setSaving(true)
    try {
      const req = await backgroundCheckRequestsApi.create({
        candidate_id: candidateId,
        job_id: jobId || null,
        package_id: packageId || null,
        candidate_email: candidateEmail,
        candidate_phone: candidatePhone,
      })
      toast('Request created', 'success')
      navigate(`/app/background-checks/requests/${req.id}`)
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Save failed', 'error')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="hf-page">
      <PageHeader title="New background check request" subtitle="Create a draft request; submit it to the provider later." />
      <form onSubmit={onSubmit}>
        <Card>
          <div style={{ display: 'grid', gap: 14 }}>
            <Select
              label="Candidate"
              required
              value={candidateId}
              onChange={(e) => setCandidateId(e.target.value)}
              placeholder="Select candidate"
              options={(candidates.data?.results || []).map((c) => ({ value: c.id, label: c.full_name || c.name }))}
            />
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              <Select
                label="Job (optional)"
                value={jobId}
                onChange={(e) => setJobId(e.target.value)}
                placeholder="Select job"
                options={(jobs.data?.results || []).map((j) => ({ value: j.id, label: j.title }))}
              />
              <Select
                label="Package (optional)"
                value={packageId}
                onChange={(e) => setPackageId(e.target.value)}
                placeholder="Select package"
                options={(packages.data?.results || []).map((p) => ({ value: p.id, label: p.name }))}
              />
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              <Input label="Candidate email (override)" value={candidateEmail} onChange={(e) => setCandidateEmail(e.target.value)} />
              <Input label="Candidate phone (override)" value={candidatePhone} onChange={(e) => setCandidatePhone(e.target.value)} />
            </div>
            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
              <Button type="button" variant="outline" onClick={() => navigate('/app/background-checks/requests')}>Cancel</Button>
              <Button type="submit" loading={saving}>Create request</Button>
            </div>
          </div>
        </Card>
      </form>
    </div>
  )
}

export function BackgroundCheckRequestDetailPage() {
  const { id = '' } = useParams()
  const navigate = useNavigate()
  const { toast } = useToast()
  const [tab, setTab] = useState('overview')
  const [acting, setActing] = useState(false)
  const [cancelOpen, setCancelOpen] = useState(false)
  const request = useApi(() => backgroundCheckRequestsApi.get(id), [id], { enabled: Boolean(id) })
  const statusPayload = useApi(() => backgroundCheckRequestsApi.status(id), [id, tab], {
    enabled: Boolean(id) && tab === 'timeline',
  })
  const reports = useApi(
    () => backgroundCheckReportsApi.list({ request: id, page_size: 50 }),
    [id, tab],
    { enabled: Boolean(id) && tab === 'reports' },
  )

  async function runAction(action: () => Promise<unknown>, ok: string) {
    setActing(true)
    try {
      await action()
      toast(ok, 'success')
      request.reload()
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Action failed', 'error')
    } finally {
      setActing(false)
    }
  }

  if (request.loading) {
    return (
      <div style={{ padding: 64, display: 'grid', placeItems: 'center' }}>
        <Spinner label="Loading request…" />
      </div>
    )
  }

  if (request.error || !request.data) {
    return (
      <EmptyState
        title="Request not found"
        description={request.error || 'This request may have been deleted.'}
        actionLabel="Back to requests"
        onAction={() => navigate('/app/background-checks/requests')}
      />
    )
  }

  const r = request.data

  return (
    <div className="hf-page">
      <PageHeader
        title={r.candidate_name}
        subtitle={`${r.package_name || 'No package'}${r.job_title ? ` · ${r.job_title}` : ''}${r.provider_name ? ` · ${r.provider_name}` : ''}`}
        actions={
          <>
            <Badge status={r.status} />
            {r.status === 'draft' && (
              <Button loading={acting} onClick={() => runAction(() => backgroundCheckRequestsApi.submit(id), 'Request submitted')}>
                Submit
              </Button>
            )}
            {['submitted', 'in_progress', 'on_hold'].includes(r.status) && (
              <Button variant="outline" loading={acting} onClick={() => runAction(() => backgroundCheckRequestsApi.resend(id), 'Request resent')}>
                Resend
              </Button>
            )}
            {!['completed', 'cancelled'].includes(r.status) && (
              <Button variant="danger" loading={acting} onClick={() => setCancelOpen(true)}>
                Cancel
              </Button>
            )}
          </>
        }
      />

      <Tabs
        value={tab}
        onChange={setTab}
        items={[
          { id: 'overview', label: 'Overview' },
          { id: 'timeline', label: 'Timeline' },
          { id: 'reports', label: 'Reports', count: reports.data?.count },
        ]}
      />

      {tab === 'overview' && (
        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 16 }}>
          <Card title="Result summary">
            {r.result_summary && Object.keys(r.result_summary).length ? (
              <pre className="hf-muted" style={{ fontSize: '0.85rem', margin: 0, whiteSpace: 'pre-wrap' }}>
                {JSON.stringify(r.result_summary, null, 2)}
              </pre>
            ) : (
              <EmptyState title="No results yet" description="The result summary appears once the provider responds." />
            )}
          </Card>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <Card title="Details">
              <dl style={{ display: 'grid', gap: 10, margin: 0, fontSize: '0.88rem' }}>
                <Row label="Status" value={titleCase(r.status)} />
                <Row label="Package" value={r.package_name || '—'} />
                <Row label="Provider" value={r.provider_name || '—'} />
                <Row label="Provider ref" value={r.provider_ref || '—'} />
                <Row label="Email" value={r.candidate_email || r.candidate_email_actual || '—'} />
                <Row label="Phone" value={r.candidate_phone || '—'} />
                <Row label="Consent given" value={formatDateTime(r.consent_given_at)} />
                <Row label="Submitted" value={formatDateTime(r.submitted_at)} />
                <Row label="Completed" value={formatDateTime(r.completed_at)} />
              </dl>
            </Card>
            {r.latest_report && (
              <Card title="Latest report">
                <Badge status={r.latest_report.status} />
                <p className="hf-muted" style={{ marginTop: 8, fontSize: '0.85rem', lineHeight: 1.5 }}>
                  {r.latest_report.summary || 'No summary'}
                </p>
              </Card>
            )}
          </div>
        </div>
      )}

      {tab === 'timeline' && (
        <Card title="Status timeline">
          {statusPayload.data ? (
            <Timeline
              items={buildTimeline(statusPayload.data)}
            />
          ) : statusPayload.loading ? (
            <div style={{ padding: 32, display: 'grid', placeItems: 'center' }}><Spinner /></div>
          ) : (
            <EmptyState title="No timeline" description={statusPayload.error || 'Status not available.'} />
          )}
        </Card>
      )}

      {tab === 'reports' && (
        <Card padding={0} title="Reports">
          <DataTable
            loading={reports.loading}
            columns={[
              { key: 'status', header: 'Status', render: (rep) => <Badge status={rep.status} /> },
              { key: 'summary', header: 'Summary', render: (rep) => rep.summary || '—' },
              {
                key: 'findings',
                header: 'Findings',
                render: (rep) => <Badge tone="neutral">{rep.findings?.length || 0} items</Badge>,
              },
              { key: 'received', header: 'Received', render: (rep) => formatDateTime(rep.received_at) },
              { key: 'reviewed', header: 'Reviewed', render: (rep) => rep.reviewed_by_name || '—' },
            ]}
            rows={reports.data?.results || []}
            rowKey={(rep) => rep.id}
            emptyTitle="No reports"
            emptyDescription="Reports appear when the provider responds."
          />
        </Card>
      )}

      <ConfirmDialog
        open={cancelOpen}
        title="Cancel request"
        message={`Cancel the background check for ${r.candidate_name}?`}
        confirmLabel="Cancel request"
        danger
        loading={acting}
        onCancel={() => setCancelOpen(false)}
        onConfirm={() => {
          setCancelOpen(false)
          void runAction(() => backgroundCheckRequestsApi.cancel(id), 'Request cancelled')
        }}
      />
    </div>
  )
}

function buildTimeline(payload: { status: string; submitted_at?: string | null; completed_at?: string | null; consent_given_at?: string | null; provider_ref?: string }) {
  const items: Array<{ id: string; title: string; description?: string; at: string }> = [
    { id: 'created', title: 'Request created', at: '' },
  ]
  if (payload.consent_given_at) {
    items.push({ id: 'consent', title: 'Consent recorded', at: payload.consent_given_at })
  }
  if (payload.submitted_at) {
    items.push({
      id: 'submitted',
      title: `Submitted to provider${payload.provider_ref ? ` (${payload.provider_ref})` : ''}`,
      at: payload.submitted_at,
    })
  }
  if (payload.completed_at) {
    items.push({ id: 'completed', title: 'Check completed', at: payload.completed_at })
  }
  return items
}

// ---------------------------------------------------------------------------
// Reports
// ---------------------------------------------------------------------------

export function BackgroundCheckReportsPage() {
  const { toast } = useToast()
  const [page, setPage] = useState(1)
  const [status, setStatus] = useState('')
  const [reviewing, setReviewing] = useState<BackgroundCheckReport | null>(null)
  const [decision, setDecision] = useState<ReportStatus>('clear')
  const [summary, setSummary] = useState('')
  const [saving, setSaving] = useState(false)
  const { data, loading, error, reload } = useApi(
    () =>
      backgroundCheckReportsApi.list({
        page,
        page_size: 20,
        status: status || undefined,
      }),
    [page, status],
  )

  function openReview(rep: BackgroundCheckReport) {
    setReviewing(rep)
    setDecision('clear')
    setSummary(rep.summary || '')
  }

  async function submitReview(e: FormEvent) {
    e.preventDefault()
    if (!reviewing) return
    setSaving(true)
    try {
      await backgroundCheckReportsApi.review(reviewing.id, { decision, summary })
      toast('Report reviewed', 'success')
      setReviewing(null)
      reload()
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Review failed', 'error')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="hf-page">
      <PageHeader title="Background check reports" subtitle="Review provider reports and record decisions." />

      <Card padding="1rem">
        <div style={{ maxWidth: 240 }}>
          <Select
            label="Status"
            value={status}
            onChange={(e) => setStatus(e.target.value)}
            options={[
              { value: '', label: 'All' },
              { value: 'pending', label: 'Pending' },
              { value: 'clear', label: 'Clear' },
              { value: 'consider', label: 'Consider' },
              { value: 'flagged', label: 'Flagged' },
            ]}
          />
        </div>
      </Card>

      {error && (
        <Card>
          <p style={{ color: 'var(--hf-danger)' }}>{error}</p>
          <Button variant="outline" size="sm" onClick={reload} style={{ marginTop: 8 }}>Retry</Button>
        </Card>
      )}

      <Card padding={0}>
        <DataTable
          loading={loading}
          columns={[
            { key: 'candidate', header: 'Candidate', render: (rep) => rep.request_candidate },
            { key: 'status', header: 'Status', render: (rep) => <Badge status={rep.status} /> },
            { key: 'summary', header: 'Summary', render: (rep) => rep.summary || '—' },
            {
              key: 'findings',
              header: 'Findings',
              render: (rep) => <Badge tone="neutral">{rep.findings?.length || 0} items</Badge>,
            },
            { key: 'received', header: 'Received', render: (rep) => formatDateTime(rep.received_at) },
            { key: 'reviewed', header: 'Reviewed by', render: (rep) => rep.reviewed_by_name || '—' },
            {
              key: 'actions',
              header: '',
              render: (rep) =>
                rep.status === 'pending' ? (
                  <Button size="sm" variant="outline" onClick={(e) => { e.stopPropagation(); openReview(rep) }}>
                    Review
                  </Button>
                ) : null,
            },
          ]}
          rows={data?.results || []}
          rowKey={(rep) => rep.id}
          emptyTitle="No reports"
          emptyDescription="Reports appear when provider callbacks arrive."
        />
        {data && <Pagination page={page} pageSize={20} total={data.count} onChange={setPage} />}
      </Card>

      <Modal open={Boolean(reviewing)} onClose={() => setReviewing(null)} title="Review report" width={560}>
        <form onSubmit={submitReview} style={{ display: 'grid', gap: 12 }}>
          <p className="hf-muted" style={{ fontSize: '0.88rem', margin: 0 }}>
            {reviewing?.request_candidate} — received {reviewing ? formatDateTime(reviewing.received_at) : '—'}
          </p>
          <Select
            label="Decision"
            value={decision}
            onChange={(e) => setDecision(e.target.value as ReportStatus)}
            options={[
              { value: 'clear', label: 'Clear' },
              { value: 'consider', label: 'Consider' },
              { value: 'flagged', label: 'Flagged' },
            ]}
          />
          <Textarea label="Summary" value={summary} onChange={(e) => setSummary(e.target.value)} />
          <Button type="submit" loading={saving}>Save decision</Button>
        </form>
      </Modal>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Disputes
// ---------------------------------------------------------------------------

export function CheckDisputesPage() {
  const { toast } = useToast()
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('')
  const [acting, setActing] = useState<string | null>(null)
  const [resolution, setResolution] = useState('')
  const [decisionOpen, setDecisionOpen] = useState<{ dispute: CheckDispute; kind: 'resolve' | 'reject' } | null>(null)
  const { data, loading, error, reload } = useApi(
    () =>
      checkDisputesApi.list({
        page,
        page_size: 20,
        search: search || undefined,
        status: status || undefined,
      }),
    [page, search, status],
  )

  function openDecision(dispute: CheckDispute, kind: 'resolve' | 'reject') {
    setResolution(dispute.resolution || '')
    setDecisionOpen({ dispute, kind })
  }

  async function submitDecision() {
    if (!decisionOpen) return
    const { dispute, kind } = decisionOpen
    setActing(dispute.id)
    try {
      if (kind === 'resolve') {
        await checkDisputesApi.resolve(dispute.id, { resolution })
        toast('Dispute resolved', 'success')
      } else {
        await checkDisputesApi.reject(dispute.id, { resolution })
        toast('Dispute rejected', 'success')
      }
      setDecisionOpen(null)
      reload()
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Action failed', 'error')
    } finally {
      setActing(null)
    }
  }

  return (
    <div className="hf-page">
      <PageHeader title="Check disputes" subtitle="Candidate disputes against background check reports." />

      <Card padding="1rem">
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, alignItems: 'flex-end' }}>
          <div style={{ flex: '1 1 260px', minWidth: 220 }}>
            <Input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search disputes…" />
          </div>
          <div style={{ minWidth: 150 }}>
            <Select
              label="Status"
              value={status}
              onChange={(e) => setStatus(e.target.value)}
              options={[
                { value: '', label: 'All' },
                { value: 'open', label: 'Open' },
                { value: 'under_review', label: 'Under review' },
                { value: 'resolved', label: 'Resolved' },
                { value: 'rejected', label: 'Rejected' },
              ]}
            />
          </div>
          <Button variant="ghost" size="sm" onClick={() => { setSearch(''); setStatus(''); setPage(1) }}>
            Clear
          </Button>
        </div>
      </Card>

      {error && (
        <Card>
          <p style={{ color: 'var(--hf-danger)' }}>{error}</p>
          <Button variant="outline" size="sm" onClick={reload} style={{ marginTop: 8 }}>Retry</Button>
        </Card>
      )}

      <Card padding={0}>
        <DataTable
          loading={loading}
          columns={[
            {
              key: 'candidate',
              header: 'Candidate',
              render: (d) => (
                <div>
                  <div style={{ fontWeight: 650 }}>{d.candidate_name}</div>
                  <div className="hf-subtle" style={{ fontSize: '0.75rem' }}>{d.reason}</div>
                </div>
              ),
            },
            { key: 'details', header: 'Details', render: (d) => d.details || '—' },
            { key: 'status', header: 'Status', render: (d) => <Badge status={d.status} /> },
            { key: 'resolved', header: 'Resolved', render: (d) => (d.resolved_by_name ? `${d.resolved_by_name} · ${formatDate(d.resolved_at)}` : '—') },
            {
              key: 'actions',
              header: '',
              render: (d) =>
                ['open', 'under_review'].includes(d.status) ? (
                  <div style={{ display: 'flex', gap: 6 }}>
                    <Button size="sm" variant="outline" loading={acting === d.id} onClick={(e) => { e.stopPropagation(); openDecision(d, 'resolve') }}>
                      Resolve
                    </Button>
                    <Button size="sm" variant="danger" loading={acting === d.id} onClick={(e) => { e.stopPropagation(); openDecision(d, 'reject') }}>
                      Reject
                    </Button>
                  </div>
                ) : null,
            },
          ]}
          rows={data?.results || []}
          rowKey={(d) => d.id}
          emptyTitle="No disputes"
          emptyDescription="Disputes filed against reports appear here."
        />
        {data && <Pagination page={page} pageSize={20} total={data.count} onChange={setPage} />}
      </Card>

      <Modal
        open={Boolean(decisionOpen)}
        onClose={() => setDecisionOpen(null)}
        title={decisionOpen?.kind === 'resolve' ? 'Resolve dispute' : 'Reject dispute'}
      >
        <div style={{ display: 'grid', gap: 12 }}>
          <p className="hf-muted" style={{ fontSize: '0.88rem', margin: 0 }}>
            {decisionOpen?.dispute.candidate_name} — {decisionOpen?.dispute.reason}
          </p>
          <Textarea label="Resolution note" value={resolution} onChange={(e) => setResolution(e.target.value)} />
          <Button loading={acting === decisionOpen?.dispute.id} onClick={() => void submitDecision()}>
            {decisionOpen?.kind === 'resolve' ? 'Resolve dispute' : 'Reject dispute'}
          </Button>
        </div>
      </Modal>
    </div>
  )
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}>
      <dt className="hf-muted">{label}</dt>
      <dd style={{ margin: 0, fontWeight: 600 }}>{value}</dd>
    </div>
  )
}
