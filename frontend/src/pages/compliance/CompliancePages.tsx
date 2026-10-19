/**
 * Compliance pages (overview, policies, consents, retention, EEO, notes, exports).
 *
 * Exported components & suggested routes:
 *  - ComplianceOverviewPage      → /app/compliance
 *  - CompliancePoliciesPage      → /app/compliance/policies
 *  - ConsentRecordsPage          → /app/compliance/consents
 *  - RetentionPoliciesPage       → /app/compliance/retention
 *  - EeoDeclarationsPage         → /app/compliance/eeo
 *  - ComplianceNotesPage         → /app/compliance/notes
 *  - DataExportRequestsPage      → /app/compliance/exports
 */
import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { Download, FileDown, Lock, Plus, Scale, ShieldCheck, UserCheck } from 'lucide-react'
import { candidatesApi } from '../../api/candidates'
import {
  complianceApi,
  complianceNotesApi,
  compliancePoliciesApi,
  consentRecordsApi,
  dataExportRequestsApi,
  eeoDeclarationsApi,
  retentionPoliciesApi,
  type ComplianceOverview,
  type CompliancePolicy,
  type ConsentRecord,
  type DataExportRequest,
  type DataRetentionPolicy,
  type EEODeclaration,
  type PolicyType,
  type RetentionAction,
} from '../../api/compliance'
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
  StatCard,
  Textarea,
  useToast,
} from '../../components/ui'
import { formatDate, formatDateTime, titleCase } from '../../utils/format'
import { ApiError } from '../../api/http'

const POLICY_TYPES: Array<{ value: PolicyType; label: string }> = [
  { value: 'privacy', label: 'Privacy' },
  { value: 'consent', label: 'Consent' },
  { value: 'retention', label: 'Retention' },
  { value: 'eeo', label: 'EEO' },
]

// ---------------------------------------------------------------------------
// Overview
// ---------------------------------------------------------------------------

export function ComplianceOverviewPage() {
  const navigate = useNavigate()
  const { data, loading, error, reload } = useApi(() => complianceApi.overview(), [])

  if (loading && !data) {
    return (
      <div style={{ padding: 64, display: 'grid', placeItems: 'center' }}>
        <Spinner label="Loading compliance overview…" />
      </div>
    )
  }

  if (error && !data) {
    return (
      <EmptyState
        title="Overview unavailable"
        description={error}
        actionLabel="Retry"
        onAction={reload}
      />
    )
  }

  const o: ComplianceOverview | null = data

  return (
    <div className="hf-page">
      <PageHeader
        title="Compliance"
        subtitle="GDPR / EEO / retention posture for your organization."
        actions={
          <>
            <Button variant="outline" onClick={() => navigate('/app/compliance/consents')}>Consents</Button>
            <Button variant="outline" onClick={() => navigate('/app/compliance/exports')}>Data exports</Button>
          </>
        }
      />

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 12 }}>
        <StatCard label="Consents granted" value={o?.consents.granted ?? 0} hint={`${o?.consents.withdrawn ?? 0} withdrawn`} icon={<ShieldCheck size={18} />} />
        <StatCard label="Active policies" value={o?.policies.active ?? 0} hint={`${o?.policies.total ?? 0} total`} icon={<Scale size={18} />} />
        <StatCard label="Retention policies" value={o?.retention.active_policies ?? 0} hint="active" icon={<Lock size={18} />} />
        <StatCard label="EEO declarations" value={o?.eeo_declarations ?? 0} icon={<UserCheck size={18} />} />
        <StatCard
          label="Export requests"
          value={(o?.exports.pending ?? 0) + (o?.exports.processing ?? 0)}
          hint={`${o?.exports.completed ?? 0} completed`}
          icon={<FileDown size={18} />}
        />
      </div>

      {o && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
          <Card title="Policies by type">
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
              {Object.entries(o.policies.by_type || {}).map(([type, count]) => (
                <Badge key={type} tone="teal">{titleCase(type)}: {count}</Badge>
              ))}
            </div>
          </Card>
          <Card title="Exports by status">
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
              {Object.entries(o.exports || {}).map(([status, count]) => (
                <Badge key={status} status={status} tone="neutral">{status}: {count}</Badge>
              ))}
            </div>
          </Card>
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Policies
// ---------------------------------------------------------------------------

export function CompliancePoliciesPage() {
  const { toast } = useToast()
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [policyType, setPolicyType] = useState('')
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<CompliancePolicy | null>(null)
  const [name, setName] = useState('')
  const [type, setType] = useState<PolicyType>('privacy')
  const [contentHtml, setContentHtml] = useState('')
  const [saving, setSaving] = useState(false)
  const [acting, setActing] = useState<string | null>(null)
  const [removing, setRemoving] = useState<CompliancePolicy | null>(null)
  const { data, loading, error, reload } = useApi(
    () =>
      compliancePoliciesApi.list({
        page,
        page_size: 20,
        search: search || undefined,
        policy_type: policyType || undefined,
      }),
    [page, search, policyType],
  )

  function openCreate() {
    setEditing(null)
    setName('')
    setType('privacy')
    setContentHtml('')
    setModalOpen(true)
  }

  function openEdit(p: CompliancePolicy) {
    setEditing(p)
    setName(p.name)
    setType(p.policy_type)
    setContentHtml(p.content_html)
    setModalOpen(true)
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setSaving(true)
    try {
      if (editing) {
        await compliancePoliciesApi.update(editing.id, { name, policy_type: type, content_html: contentHtml })
        toast('Policy updated', 'success')
      } else {
        await compliancePoliciesApi.create({ name, policy_type: type, content_html: contentHtml })
        toast('Policy created', 'success')
      }
      setModalOpen(false)
      reload()
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Save failed', 'error')
    } finally {
      setSaving(false)
    }
  }

  async function runActivate(p: CompliancePolicy) {
    setActing(p.id)
    try {
      await compliancePoliciesApi.activate(p.id)
      toast('Policy activated', 'success')
      reload()
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Activate failed', 'error')
    } finally {
      setActing(null)
    }
  }

  return (
    <div className="hf-page">
      <PageHeader
        title="Compliance policies"
        subtitle="Versioned privacy, consent, retention, and EEO policies."
        actions={<Button leftIcon={<Plus size={16} />} onClick={openCreate}>New policy</Button>}
      />

      <Card padding="1rem">
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, alignItems: 'flex-end' }}>
          <div style={{ flex: '1 1 260px', minWidth: 220 }}>
            <Input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search policies…" />
          </div>
          <div style={{ minWidth: 150 }}>
            <Select
              label="Type"
              value={policyType}
              onChange={(e) => setPolicyType(e.target.value)}
              options={[{ value: '', label: 'All' }, ...POLICY_TYPES]}
            />
          </div>
          <Button variant="ghost" size="sm" onClick={() => { setSearch(''); setPolicyType(''); setPage(1) }}>
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
              key: 'name',
              header: 'Policy',
              render: (p) => (
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span style={{ fontWeight: 650 }}>{p.name}</span>
                  <Badge tone="teal">v{p.version}</Badge>
                </div>
              ),
            },
            { key: 'type', header: 'Type', render: (p) => titleCase(p.policy_type) },
            {
              key: 'active',
              header: 'Status',
              render: (p) => <Badge tone={p.is_active ? 'success' : 'neutral'}>{p.is_active ? 'Active' : 'Inactive'}</Badge>,
            },
            { key: 'effective', header: 'Effective', render: (p) => formatDateTime(p.effective_at) },
            { key: 'created', header: 'Created', render: (p) => formatDate(p.created_at) },
            {
              key: 'actions',
              header: '',
              render: (p) => (
                <div style={{ display: 'flex', gap: 6 }}>
                  {!p.is_active && (
                    <Button size="sm" loading={acting === p.id} onClick={(e) => { e.stopPropagation(); void runActivate(p) }}>
                      Activate
                    </Button>
                  )}
                  <Button size="sm" variant="outline" onClick={(e) => { e.stopPropagation(); openEdit(p) }}>Edit</Button>
                  <Button size="sm" variant="ghost" onClick={(e) => { e.stopPropagation(); setRemoving(p) }}>Delete</Button>
                </div>
              ),
            },
          ]}
          rows={data?.results || []}
          rowKey={(p) => p.id}
          emptyTitle="No policies"
          emptyDescription="Create a compliance policy to manage consent and retention."
        />
        {data && <Pagination page={page} pageSize={20} total={data.count} onChange={setPage} />}
      </Card>

      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title={editing ? 'Edit policy' : 'New policy'} width={600}>
        <form onSubmit={onSubmit} style={{ display: 'grid', gap: 12 }}>
          <Input label="Name" required value={name} onChange={(e) => setName(e.target.value)} />
          <Select
            label="Type"
            value={type}
            onChange={(e) => setType(e.target.value as PolicyType)}
            options={POLICY_TYPES}
          />
          <Textarea
            label="Content (HTML)"
            value={contentHtml}
            onChange={(e) => setContentHtml(e.target.value)}
            style={{ minHeight: 160, fontFamily: 'monospace', fontSize: '0.85rem' }}
          />
          {editing && (
            <p className="hf-subtle" style={{ fontSize: '0.78rem', margin: 0 }}>
              Version {editing.version} · activating a consent policy bumps its version and expires older consents.
            </p>
          )}
          <Button type="submit" loading={saving}>{editing ? 'Save changes' : 'Create policy'}</Button>
        </form>
      </Modal>

      <ConfirmDialog
        open={Boolean(removing)}
        title="Delete policy"
        message={`Delete "${removing?.name}" v${removing?.version}?`}
        confirmLabel="Delete"
        danger
        onCancel={() => setRemoving(null)}
        onConfirm={() => {
          if (!removing) return
          compliancePoliciesApi
            .remove(removing.id)
            .then(() => { toast('Policy deleted', 'success'); setRemoving(null); reload() })
            .catch((err) => toast(err instanceof ApiError ? err.message : 'Delete failed', 'error'))
        }}
      />
    </div>
  )
}

// ---------------------------------------------------------------------------
// Consents
// ---------------------------------------------------------------------------

export function ConsentRecordsPage() {
  const { toast } = useToast()
  const [page, setPage] = useState(1)
  const [purpose, setPurpose] = useState('')
  const [status, setStatus] = useState('')
  const [grantOpen, setGrantOpen] = useState(false)
  const [policyId, setPolicyId] = useState('')
  const [candidateId, setCandidateId] = useState('')
  const [grantPurpose, setGrantPurpose] = useState('')
  const [source, setSource] = useState('')
  const [saving, setSaving] = useState(false)
  const [acting, setActing] = useState<string | null>(null)
  const { data, loading, error, reload } = useApi(
    () =>
      consentRecordsApi.list({
        page,
        page_size: 20,
        purpose: purpose || undefined,
        status: status || undefined,
      }),
    [page, purpose, status],
  )
  const policies = useApi(() => compliancePoliciesApi.list({ page_size: 100, policy_type: 'consent' }), [])
  const candidates = useApi(() => candidatesApi.list({ page_size: 100 }), [])

  async function grantConsent(e: FormEvent) {
    e.preventDefault()
    setSaving(true)
    try {
      await consentRecordsApi.grant({
        policy_id: policyId,
        candidate_id: candidateId || null,
        purpose: grantPurpose,
        source,
      })
      toast('Consent granted', 'success')
      setGrantOpen(false)
      setPolicyId('')
      setCandidateId('')
      setGrantPurpose('')
      setSource('')
      reload()
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Grant failed', 'error')
    } finally {
      setSaving(false)
    }
  }

  async function runWithdraw(record: ConsentRecord) {
    setActing(record.id)
    try {
      await consentRecordsApi.withdraw(record.id)
      toast('Consent withdrawn', 'success')
      reload()
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Withdraw failed', 'error')
    } finally {
      setActing(null)
    }
  }

  return (
    <div className="hf-page">
      <PageHeader
        title="Consent records"
        subtitle="Consent grants and withdrawals against consent policies."
        actions={<Button leftIcon={<Plus size={16} />} onClick={() => setGrantOpen(true)}>Grant consent</Button>}
      />

      <Card padding="1rem">
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, alignItems: 'flex-end' }}>
          <div style={{ minWidth: 180, flex: '0 1 220px' }}>
            <Input value={purpose} onChange={(e) => setPurpose(e.target.value)} placeholder="Filter by purpose…" />
          </div>
          <div style={{ minWidth: 150 }}>
            <Select
              label="Status"
              value={status}
              onChange={(e) => setStatus(e.target.value)}
              options={[
                { value: '', label: 'All' },
                { value: 'granted', label: 'Granted' },
                { value: 'withdrawn', label: 'Withdrawn' },
              ]}
            />
          </div>
          <Button variant="ghost" size="sm" onClick={() => { setPurpose(''); setStatus(''); setPage(1) }}>
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
            { key: 'subject', header: 'Subject', render: (c) => c.candidate_name || c.user_email || '—' },
            { key: 'policy', header: 'Policy', render: (c) => `${c.policy_name} v${c.consent_version}` },
            { key: 'purpose', header: 'Purpose', render: (c) => c.purpose || '—' },
            { key: 'status', header: 'Status', render: (c) => <Badge status={c.status} /> },
            { key: 'granted', header: 'Granted', render: (c) => formatDateTime(c.granted_at) },
            { key: 'withdrawn', header: 'Withdrawn', render: (c) => formatDateTime(c.withdrawn_at) },
            { key: 'source', header: 'Source', render: (c) => c.source || '—' },
            {
              key: 'actions',
              header: '',
              render: (c) =>
                c.status === 'granted' ? (
                  <Button size="sm" variant="outline" loading={acting === c.id} onClick={(e) => { e.stopPropagation(); void runWithdraw(c) }}>
                    Withdraw
                  </Button>
                ) : null,
            },
          ]}
          rows={data?.results || []}
          rowKey={(c) => c.id}
          emptyTitle="No consent records"
          emptyDescription="Grant consent against an active consent policy."
        />
        {data && <Pagination page={page} pageSize={20} total={data.count} onChange={setPage} />}
      </Card>

      <Modal open={grantOpen} onClose={() => setGrantOpen(false)} title="Grant consent">
        <form onSubmit={grantConsent} style={{ display: 'grid', gap: 12 }}>
          <Select
            label="Consent policy"
            required
            value={policyId}
            onChange={(e) => setPolicyId(e.target.value)}
            placeholder="Select policy"
            options={(policies.data?.results || []).map((p) => ({ value: p.id, label: `${p.name} v${p.version}` }))}
          />
          <Select
            label="Candidate (optional)"
            value={candidateId}
            onChange={(e) => setCandidateId(e.target.value)}
            placeholder="Select candidate"
            options={(candidates.data?.results || []).map((c) => ({ value: c.id, label: c.full_name || c.name }))}
          />
          <Input label="Purpose" value={grantPurpose} onChange={(e) => setGrantPurpose(e.target.value)} />
          <Input label="Source" value={source} onChange={(e) => setSource(e.target.value)} placeholder="e.g. careers page, recruiter" />
          <Button type="submit" loading={saving}>Grant consent</Button>
        </form>
      </Modal>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Retention policies
// ---------------------------------------------------------------------------

const RETENTION_ACTIONS: Array<{ value: RetentionAction; label: string }> = [
  { value: 'anonymize', label: 'Anonymize' },
  { value: 'delete', label: 'Delete' },
  { value: 'archive', label: 'Archive' },
]

const DATA_TYPES = [
  'candidates',
  'applications',
  'documents',
  'messages',
  'audit_logs',
  'offers',
  'interviews',
  'assessments',
  'compliance_notes',
  'consent_records',
]

export function RetentionPoliciesPage() {
  const { toast } = useToast()
  const [page, setPage] = useState(1)
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<DataRetentionPolicy | null>(null)
  const [dataType, setDataType] = useState(DATA_TYPES[0])
  const [retentionDays, setRetentionDays] = useState(365)
  const [action, setAction] = useState<RetentionAction>('delete')
  const [notes, setNotes] = useState('')
  const [isActive, setIsActive] = useState(true)
  const [saving, setSaving] = useState(false)
  const [removing, setRemoving] = useState<DataRetentionPolicy | null>(null)
  const { data, loading, error, reload } = useApi(
    () => retentionPoliciesApi.list({ page, page_size: 20 }),
    [page],
  )

  function openCreate() {
    setEditing(null)
    setDataType(DATA_TYPES[0])
    setRetentionDays(365)
    setAction('delete')
    setNotes('')
    setIsActive(true)
    setModalOpen(true)
  }

  function openEdit(p: DataRetentionPolicy) {
    setEditing(p)
    setDataType(p.data_type)
    setRetentionDays(p.retention_days)
    setAction(p.action)
    setNotes(p.notes)
    setIsActive(p.is_active)
    setModalOpen(true)
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setSaving(true)
    const payload = { data_type: dataType, retention_days: Number(retentionDays) || 365, action, notes, is_active: isActive }
    try {
      if (editing) {
        await retentionPoliciesApi.update(editing.id, payload)
        toast('Retention policy updated', 'success')
      } else {
        await retentionPoliciesApi.create(payload)
        toast('Retention policy created', 'success')
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
        title="Retention policies"
        subtitle="How long each data type is kept and what happens afterwards."
        actions={<Button leftIcon={<Plus size={16} />} onClick={openCreate}>New policy</Button>}
      />

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
            { key: 'type', header: 'Data type', render: (p) => <Badge tone="teal">{p.data_type}</Badge> },
            { key: 'days', header: 'Retention', render: (p) => `${p.retention_days} days` },
            { key: 'action', header: 'Action', render: (p) => titleCase(p.action) },
            {
              key: 'active',
              header: 'Active',
              render: (p) => <Badge tone={p.is_active ? 'success' : 'neutral'}>{p.is_active ? 'Active' : 'Inactive'}</Badge>,
            },
            { key: 'notes', header: 'Notes', render: (p) => p.notes || '—' },
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
          emptyTitle="No retention policies"
          emptyDescription="Define retention rules per data type."
        />
        {data && <Pagination page={page} pageSize={20} total={data.count} onChange={setPage} />}
      </Card>

      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title={editing ? 'Edit retention policy' : 'New retention policy'}>
        <form onSubmit={onSubmit} style={{ display: 'grid', gap: 12 }}>
          <Select
            label="Data type"
            value={dataType}
            onChange={(e) => setDataType(e.target.value)}
            options={DATA_TYPES.map((d) => ({ value: d, label: titleCase(d) }))}
          />
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <Input
              label="Retention (days)"
              type="number"
              min={1}
              value={retentionDays}
              onChange={(e) => setRetentionDays(Number(e.target.value))}
            />
            <Select
              label="Action"
              value={action}
              onChange={(e) => setAction(e.target.value as RetentionAction)}
              options={RETENTION_ACTIONS}
            />
          </div>
          <Textarea label="Notes" value={notes} onChange={(e) => setNotes(e.target.value)} />
          <label style={{ display: 'flex', gap: 8, alignItems: 'center', fontSize: '0.88rem' }}>
            <input type="checkbox" checked={isActive} onChange={(e) => setIsActive(e.target.checked)} />
            Active
          </label>
          <Button type="submit" loading={saving}>{editing ? 'Save changes' : 'Create policy'}</Button>
        </form>
      </Modal>

      <ConfirmDialog
        open={Boolean(removing)}
        title="Delete retention policy"
        message={`Delete the "${removing?.data_type}" retention policy?`}
        confirmLabel="Delete"
        danger
        onCancel={() => setRemoving(null)}
        onConfirm={() => {
          if (!removing) return
          retentionPoliciesApi
            .remove(removing.id)
            .then(() => { toast('Policy deleted', 'success'); setRemoving(null); reload() })
            .catch((err) => toast(err instanceof ApiError ? err.message : 'Delete failed', 'error'))
        }}
      />
    </div>
  )
}

// ---------------------------------------------------------------------------
// EEO declarations
// ---------------------------------------------------------------------------

export function EeoDeclarationsPage() {
  const { toast } = useToast()
  const [page, setPage] = useState(1)
  const [modalOpen, setModalOpen] = useState(false)
  const [candidateId, setCandidateId] = useState('')
  const [saving, setSaving] = useState(false)
  const { data, loading, error, reload } = useApi(
    () => eeoDeclarationsApi.list({ page, page_size: 20 }),
    [page],
  )
  const candidates = useApi(() => candidatesApi.list({ page_size: 100 }), [])

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setSaving(true)
    try {
      await eeoDeclarationsApi.create({ candidate_id: candidateId || null })
      toast('Declaration created', 'success')
      setModalOpen(false)
      setCandidateId('')
      reload()
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Create failed', 'error')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="hf-page">
      <PageHeader
        title="EEO declarations"
        subtitle="Self-identified EEO data; submissions are anonymous via token."
        actions={<Button leftIcon={<Plus size={16} />} onClick={() => setModalOpen(true)}>New declaration</Button>}
      />

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
            { key: 'candidate', header: 'Candidate', render: (d) => d.candidate_name || '—' },
            { key: 'job', header: 'Job', render: (d) => d.job_title || '—' },
            {
              key: 'submitted',
              header: 'Status',
              render: (d) =>
                d.submitted_at ? <Badge tone="success">Submitted</Badge> : <Badge tone="warning">Pending</Badge>,
            },
            { key: 'gender', header: 'Gender', render: (d) => titleCase(d.gender) || '—' },
            { key: 'race', header: 'Race / ethnicity', render: (d) => titleCase(d.race_ethnicity) || '—' },
            { key: 'veteran', header: 'Veteran', render: (d) => titleCase(d.veteran_status) || '—' },
            { key: 'disability', header: 'Disability', render: (d) => titleCase(d.disability_status) || '—' },
            { key: 'created', header: 'Created', render: (d) => formatDate(d.created_at) },
          ]}
          rows={data?.results || []}
          rowKey={(d) => d.id}
          emptyTitle="No declarations"
          emptyDescription="Create a declaration shell; the candidate fills it in anonymously."
        />
        {data && <Pagination page={page} pageSize={20} total={data.count} onChange={setPage} />}
      </Card>

      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title="New EEO declaration">
        <form onSubmit={onSubmit} style={{ display: 'grid', gap: 12 }}>
          <Select
            label="Candidate (optional)"
            value={candidateId}
            onChange={(e) => setCandidateId(e.target.value)}
            placeholder="Anonymous declaration"
            options={(candidates.data?.results || []).map((c) => ({ value: c.id, label: c.full_name || c.name }))}
          />
          <p className="hf-subtle" style={{ fontSize: '0.78rem', margin: 0 }}>
            The declaration is filled in anonymously by the candidate using a unique token.
          </p>
          <Button type="submit" loading={saving}>Create declaration</Button>
        </form>
      </Modal>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Compliance notes
// ---------------------------------------------------------------------------

export function ComplianceNotesPage() {
  const { toast } = useToast()
  const [page, setPage] = useState(1)
  const [category, setCategory] = useState('')
  const [modalOpen, setModalOpen] = useState(false)
  const [candidateId, setCandidateId] = useState('')
  const [noteCategory, setNoteCategory] = useState('other')
  const [body, setBody] = useState('')
  const [saving, setSaving] = useState(false)
  const [removing, setRemoving] = useState<{ id: string; body: string } | null>(null)
  const { data, loading, error, reload } = useApi(
    () =>
      complianceNotesApi.list({
        page,
        page_size: 20,
        category: category || undefined,
      }),
    [page, category],
  )
  const candidates = useApi(() => candidatesApi.list({ page_size: 100 }), [])

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setSaving(true)
    try {
      await complianceNotesApi.create({ candidate_id: candidateId || null, category: noteCategory, body })
      toast('Note added', 'success')
      setModalOpen(false)
      setCandidateId('')
      setBody('')
      setNoteCategory('other')
      reload()
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Create failed', 'error')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="hf-page">
      <PageHeader
        title="Compliance notes"
        subtitle="Notes about GDPR, EEO, retention, and consent matters."
        actions={<Button leftIcon={<Plus size={16} />} onClick={() => setModalOpen(true)}>Add note</Button>}
      />

      <Card padding="1rem">
        <div style={{ maxWidth: 240 }}>
          <Select
            label="Category"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            options={[
              { value: '', label: 'All' },
              { value: 'gdpr', label: 'GDPR' },
              { value: 'eeo', label: 'EEO' },
              { value: 'retention', label: 'Retention' },
              { value: 'consent', label: 'Consent' },
              { value: 'other', label: 'Other' },
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
            { key: 'candidate', header: 'Candidate', render: (n) => n.candidate_name || '—' },
            { key: 'category', header: 'Category', render: (n) => <Badge tone="teal">{titleCase(n.category)}</Badge> },
            { key: 'body', header: 'Note', render: (n) => n.body || '—' },
            { key: 'author', header: 'Author', render: (n) => n.user_email || '—' },
            { key: 'created', header: 'Created', render: (n) => formatDateTime(n.created_at) },
            {
              key: 'actions',
              header: '',
              render: (n) => (
                <Button variant="ghost" size="sm" onClick={(e) => { e.stopPropagation(); setRemoving({ id: n.id, body: n.body }) }}>
                  Delete
                </Button>
              ),
            },
          ]}
          rows={data?.results || []}
          rowKey={(n) => n.id}
          emptyTitle="No notes"
          emptyDescription="Add compliance notes for candidates or the organization."
        />
        {data && <Pagination page={page} pageSize={20} total={data.count} onChange={setPage} />}
      </Card>

      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title="Add compliance note">
        <form onSubmit={onSubmit} style={{ display: 'grid', gap: 12 }}>
          <Select
            label="Candidate (optional)"
            value={candidateId}
            onChange={(e) => setCandidateId(e.target.value)}
            placeholder="Organization-wide note"
            options={(candidates.data?.results || []).map((c) => ({ value: c.id, label: c.full_name || c.name }))}
          />
          <Select
            label="Category"
            value={noteCategory}
            onChange={(e) => setNoteCategory(e.target.value)}
            options={[
              { value: 'gdpr', label: 'GDPR' },
              { value: 'eeo', label: 'EEO' },
              { value: 'retention', label: 'Retention' },
              { value: 'consent', label: 'Consent' },
              { value: 'other', label: 'Other' },
            ]}
          />
          <Textarea label="Note" required value={body} onChange={(e) => setBody(e.target.value)} />
          <Button type="submit" loading={saving}>Add note</Button>
        </form>
      </Modal>

      <ConfirmDialog
        open={Boolean(removing)}
        title="Delete note"
        message={`Delete this note? ${removing?.body ? `"${removing.body.slice(0, 80)}${removing.body.length > 80 ? '…' : ''}"` : ''}`}
        confirmLabel="Delete"
        danger
        onCancel={() => setRemoving(null)}
        onConfirm={() => {
          if (!removing) return
          complianceNotesApi
            .remove(removing.id)
            .then(() => { toast('Note deleted', 'success'); setRemoving(null); reload() })
            .catch((err) => toast(err instanceof ApiError ? err.message : 'Delete failed', 'error'))
        }}
      />
    </div>
  )
}

// ---------------------------------------------------------------------------
// Data export requests
// ---------------------------------------------------------------------------

export function DataExportRequestsPage() {
  const { toast } = useToast()
  const [page, setPage] = useState(1)
  const [status, setStatus] = useState('')
  const [modalOpen, setModalOpen] = useState(false)
  const [candidateId, setCandidateId] = useState('')
  const [includeFields, setIncludeFields] = useState('')
  const [saving, setSaving] = useState(false)
  const [acting, setActing] = useState<string | null>(null)
  const { data, loading, error, reload } = useApi(
    () =>
      dataExportRequestsApi.list({
        page,
        page_size: 20,
        status: status || undefined,
      }),
    [page, status],
  )
  const candidates = useApi(() => candidatesApi.list({ page_size: 100 }), [])

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    if (!candidateId) {
      toast('Select a candidate', 'error')
      return
    }
    setSaving(true)
    try {
      await dataExportRequestsApi.create({
        candidate_id: candidateId,
        include_fields: includeFields.split(',').map((s) => s.trim()).filter(Boolean),
      })
      toast('Export request created', 'success')
      setModalOpen(false)
      setCandidateId('')
      setIncludeFields('')
      reload()
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Create failed', 'error')
    } finally {
      setSaving(false)
    }
  }

  async function runFulfill(req: DataExportRequest) {
    setActing(req.id)
    try {
      await dataExportRequestsApi.fulfill(req.id)
      toast('Export queued', 'success')
      reload()
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Fulfill failed', 'error')
    } finally {
      setActing(null)
    }
  }

  return (
    <div className="hf-page">
      <PageHeader
        title="Data export requests"
        subtitle="GDPR data portability requests for candidate data."
        actions={<Button leftIcon={<Plus size={16} />} onClick={() => setModalOpen(true)}>New request</Button>}
      />

      <Card padding="1rem">
        <div style={{ maxWidth: 240 }}>
          <Select
            label="Status"
            value={status}
            onChange={(e) => setStatus(e.target.value)}
            options={[
              { value: '', label: 'All' },
              { value: 'pending', label: 'Pending' },
              { value: 'processing', label: 'Processing' },
              { value: 'completed', label: 'Completed' },
              { value: 'failed', label: 'Failed' },
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
            {
              key: 'candidate',
              header: 'Candidate',
              render: (r) => (
                <div>
                  <span style={{ fontWeight: 650 }}>{r.candidate_name}</span>
                  <div className="hf-subtle" style={{ fontSize: '0.75rem' }}>{r.requested_by_email || '—'}</div>
                </div>
              ),
            },
            { key: 'status', header: 'Status', render: (r) => <Badge status={r.status} /> },
            { key: 'requested', header: 'Requested', render: (r) => formatDateTime(r.requested_at) },
            { key: 'completed', header: 'Completed', render: (r) => formatDateTime(r.completed_at) },
            {
              key: 'fields',
              header: 'Include fields',
              render: (r) => (r.include_fields?.length ? r.include_fields.join(', ') : 'All'),
            },
            {
              key: 'actions',
              header: '',
              render: (r) => (
                <div style={{ display: 'flex', gap: 6 }}>
                  {['pending', 'failed'].includes(r.status) && (
                    <Button size="sm" loading={acting === r.id} onClick={(e) => { e.stopPropagation(); void runFulfill(r) }}>
                      Fulfill
                    </Button>
                  )}
                  {r.status === 'completed' && (
                    <Button
                      size="sm"
                      variant="outline"
                      leftIcon={<Download size={13} />}
                      onClick={(e) => {
                        e.stopPropagation()
                        dataExportRequestsApi
                          .download(r.id)
                          .then(() => toast('Download started', 'success'))
                          .catch((err) => toast(err instanceof ApiError ? err.message : 'Download failed', 'error'))
                      }}
                    >
                      Download
                    </Button>
                  )}
                </div>
              ),
            },
          ]}
          rows={data?.results || []}
          rowKey={(r) => r.id}
          emptyTitle="No export requests"
          emptyDescription="Create a data export request for a candidate."
        />
        {data && <Pagination page={page} pageSize={20} total={data.count} onChange={setPage} />}
      </Card>

      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title="New export request">
        <form onSubmit={onSubmit} style={{ display: 'grid', gap: 12 }}>
          <Select
            label="Candidate"
            required
            value={candidateId}
            onChange={(e) => setCandidateId(e.target.value)}
            placeholder="Select candidate"
            options={(candidates.data?.results || []).map((c) => ({ value: c.id, label: c.full_name || c.name }))}
          />
          <Input
            label="Include fields (comma-separated; empty = everything)"
            value={includeFields}
            onChange={(e) => setIncludeFields(e.target.value)}
            placeholder="profile, education, experience, documents"
          />
          <Button type="submit" loading={saving}>Create request</Button>
        </form>
      </Modal>
    </div>
  )
}
