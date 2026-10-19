/**
 * Onboarding pages (templates, plans, plan tasks, plan documents).
 *
 * Exported components & suggested routes:
 *  - OnboardingTemplatesPage     → /app/onboarding
 *  - OnboardingTemplateFormPage  → /app/onboarding/templates/new  | /app/onboarding/templates/:id/edit
 *  - OnboardingPlansPage         → /app/onboarding/plans
 *  - OnboardingPlanFormPage      → /app/onboarding/plans/new
 *  - OnboardingPlanDetailPage    → /app/onboarding/plans/:id
 */
import { useEffect, useState, type FormEvent } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { CheckCircle2, ClipboardList, FileText, Plus, RotateCcw, XCircle } from 'lucide-react'
import { candidatesApi } from '../../api/candidates'
import { offersApi } from '../../api/offers'
import { onboardingApi, type OnboardingPlanTask, type OnboardingTemplate } from '../../api/onboarding'
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
  Tabs,
  Textarea,
  Timeline,
  useToast,
} from '../../components/ui'
import { formatDate, titleCase } from '../../utils/format'
import { ApiError } from '../../api/http'

const PLAN_STATUS_OPTIONS = [
  { value: 'draft', label: 'Draft' },
  { value: 'active', label: 'Active' },
  { value: 'completed', label: 'Completed' },
  { value: 'cancelled', label: 'Cancelled' },
]

// ---------------------------------------------------------------------------
// Templates
// ---------------------------------------------------------------------------

export function OnboardingTemplatesPage() {
  const navigate = useNavigate()
  const { toast } = useToast()
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [active, setActive] = useState('')
  const [acting, setActing] = useState<string | null>(null)
  const { data, loading, error, reload } = useApi(
    () =>
      onboardingApi.listTemplates({
        page,
        page_size: 20,
        search: search || undefined,
        is_active: active || undefined,
      }),
    [page, search, active],
  )

  return (
    <div className="hf-page">
      <PageHeader
        title="Onboarding templates"
        subtitle="Reusable new-hire onboarding checklists. Plans instantiate tasks from a template."
        actions={
          <Button leftIcon={<Plus size={16} />} onClick={() => navigate('/app/onboarding/templates/new')}>
            New template
          </Button>
        }
      />

      <Card padding="1rem">
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, alignItems: 'flex-end' }}>
          <div style={{ flex: '1 1 260px', minWidth: 220 }}>
            <Input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search templates…" />
          </div>
          <div style={{ minWidth: 150 }}>
            <Select
              label="Status"
              value={active}
              onChange={(e) => setActive(e.target.value)}
              options={[
                { value: '', label: 'All' },
                { value: 'true', label: 'Active' },
                { value: 'false', label: 'Inactive' },
              ]}
            />
          </div>
          <Button variant="ghost" size="sm" onClick={() => { setSearch(''); setActive(''); setPage(1) }}>
            Clear
          </Button>
        </div>
      </Card>

      {error && (
        <Card>
          <p style={{ color: 'var(--hf-danger)' }}>{error}</p>
          <Button variant="outline" size="sm" onClick={reload} style={{ marginTop: 8 }}>
            Retry
          </Button>
        </Card>
      )}

      <Card padding={0}>
        <DataTable
          loading={loading}
          columns={[
            {
              key: 'name',
              header: 'Name',
              render: (t: OnboardingTemplate) => (
                <div>
                  <Link to={`/app/onboarding/templates/${t.id}/edit`} style={{ fontWeight: 650, textDecoration: 'none' }}>
                    {t.name}
                  </Link>
                  <div className="hf-subtle" style={{ fontSize: '0.75rem' }}>
                    {t.task_definitions?.length || 0} tasks
                  </div>
                </div>
              ),
            },
            { key: 'description', header: 'Description', render: (t: OnboardingTemplate) => t.description || '—' },
            {
              key: 'active',
              header: 'Active',
              render: (t: OnboardingTemplate) => (
                <Badge tone={t.is_active ? 'success' : 'neutral'}>{t.is_active ? 'Active' : 'Inactive'}</Badge>
              ),
            },
            { key: 'created', header: 'Created', render: (t: OnboardingTemplate) => formatDate(t.created_at) },
            {
              key: 'actions',
              header: '',
              render: (t: OnboardingTemplate) => (
                <Button
                  variant="outline"
                  size="sm"
                  loading={acting === t.id}
                  onClick={(e) => {
                    e.stopPropagation()
                    setActing(t.id)
                    onboardingApi
                      .duplicateTemplate(t.id)
                      .then(() => {
                        toast('Template duplicated', 'success')
                        reload()
                      })
                      .catch((err) => toast(err instanceof ApiError ? err.message : 'Duplicate failed', 'error'))
                      .finally(() => setActing(null))
                  }}
                >
                  Duplicate
                </Button>
              ),
            },
          ]}
          rows={data?.results || []}
          rowKey={(t) => t.id}
          emptyTitle="No templates"
          emptyDescription="Create an onboarding template to standardize new-hire onboarding."
          onRowClick={(t) => navigate(`/app/onboarding/templates/${t.id}/edit`)}
        />
        {data && <Pagination page={page} pageSize={20} total={data.count} onChange={setPage} />}
      </Card>
    </div>
  )
}

interface DefDraft {
  id?: string
  title: string
  description: string
  owner_role: string
  due_offset_days: number
  required: boolean
  order: number
}

export function OnboardingTemplateFormPage() {
  const { id } = useParams()
  const isEdit = Boolean(id)
  const navigate = useNavigate()
  const { toast } = useToast()
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [isActive, setIsActive] = useState(true)
  const [defs, setDefs] = useState<DefDraft[]>([])
  const [loading, setLoading] = useState(isEdit)
  const [saving, setSaving] = useState(false)
  const [defModal, setDefModal] = useState(false)
  const [defDraft, setDefDraft] = useState<DefDraft>({
    title: '',
    description: '',
    owner_role: '',
    due_offset_days: 0,
    required: true,
    order: 0,
  })

  useEffect(() => {
    if (!id) return
    setLoading(true)
    onboardingApi
      .getTemplate(id)
      .then((t) => {
        setName(t.name)
        setDescription(t.description)
        setIsActive(t.is_active)
        setDefs(
          (t.task_definitions || []).map((d) => ({
            id: d.id,
            title: d.title,
            description: d.description,
            owner_role: d.owner_role,
            due_offset_days: d.due_offset_days,
            required: d.required,
            order: d.order,
          })),
        )
      })
      .catch((err) => toast(err instanceof ApiError ? err.message : 'Failed to load', 'error'))
      .finally(() => setLoading(false))
  }, [id, toast])

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setSaving(true)
    try {
      const tpl = isEdit
        ? await onboardingApi.updateTemplate(id!, { name, description, is_active: isActive })
        : await onboardingApi.createTemplate({ name, description, is_active: isActive })
      for (const d of defs) {
        if (d.id) continue
        await onboardingApi.createTaskDefinition({
          template: tpl.id,
          title: d.title,
          description: d.description,
          owner_role: d.owner_role,
          due_offset_days: Number(d.due_offset_days) || 0,
          required: d.required,
          order: Number(d.order) || 0,
        })
      }
      const removed = (await onboardingApi.getTemplate(tpl.id)).task_definitions.filter(
        (d) => !defs.some((dd) => dd.id === d.id),
      )
      for (const d of removed) {
        await onboardingApi.removeTaskDefinition(d.id)
      }
      toast(isEdit ? 'Template updated' : 'Template created', 'success')
      navigate('/app/onboarding')
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
        title={isEdit ? 'Edit onboarding template' : 'New onboarding template'}
        subtitle="Define the checklist tasks that get instantiated when a plan starts."
      />
      <form onSubmit={onSubmit} style={{ display: 'grid', gap: 16 }}>
        <Card>
          <div style={{ display: 'grid', gap: 14 }}>
            <Input label="Name" required value={name} onChange={(e) => setName(e.target.value)} />
            <Textarea label="Description" value={description} onChange={(e) => setDescription(e.target.value)} />
            <label style={{ display: 'flex', gap: 8, alignItems: 'center', fontSize: '0.88rem' }}>
              <input type="checkbox" checked={isActive} onChange={(e) => setIsActive(e.target.checked)} />
              Active — available for new plans
            </label>
          </div>
        </Card>

        <Card
          title="Task definitions"
          subtitle="Tasks created on every plan that starts from this template."
          actions={
            <Button
              variant="outline"
              size="sm"
              leftIcon={<Plus size={14} />}
              onClick={() => {
                setDefDraft({ title: '', description: '', owner_role: '', due_offset_days: 0, required: true, order: defs.length })
                setDefModal(true)
              }}
            >
              Add task
            </Button>
          }
        >
          {defs.length ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {defs.map((d, idx) => (
                <div
                  key={d.id || idx}
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    gap: 12,
                    padding: 12,
                    borderRadius: 10,
                    border: '1px solid var(--hf-border)',
                  }}
                >
                  <div>
                    <div style={{ fontWeight: 600, fontSize: '0.9rem' }}>
                      {d.required ? <Badge tone="teal" status="required" /> : null} {d.title}
                    </div>
                    <div className="hf-subtle" style={{ fontSize: '0.78rem' }}>
                      {d.owner_role || 'Any role'} · due +{d.due_offset_days}d · order {d.order}
                    </div>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setDefs((list) => list.filter((_, i) => i !== idx))}
                  >
                    Remove
                  </Button>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState title="No tasks yet" description="Add task definitions to this template." />
          )}
        </Card>

        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
          <Button type="button" variant="outline" onClick={() => navigate('/app/onboarding')}>
            Cancel
          </Button>
          <Button type="submit" loading={saving}>
            {isEdit ? 'Save changes' : 'Create template'}
          </Button>
        </div>
      </form>

      <Modal open={defModal} onClose={() => setDefModal(false)} title="Add task definition" width={560}>
        <div style={{ display: 'grid', gap: 12 }}>
          <Input
            label="Title"
            required
            value={defDraft.title}
            onChange={(e) => setDefDraft((d) => ({ ...d, title: e.target.value }))}
          />
          <Textarea
            label="Description"
            value={defDraft.description}
            onChange={(e) => setDefDraft((d) => ({ ...d, description: e.target.value }))}
          />
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <Input
              label="Owner role"
              value={defDraft.owner_role}
              onChange={(e) => setDefDraft((d) => ({ ...d, owner_role: e.target.value }))}
            />
            <Input
              label="Due offset (days)"
              type="number"
              min={0}
              value={defDraft.due_offset_days}
              onChange={(e) => setDefDraft((d) => ({ ...d, due_offset_days: Number(e.target.value) }))}
            />
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <Input
              label="Order"
              type="number"
              min={0}
              value={defDraft.order}
              onChange={(e) => setDefDraft((d) => ({ ...d, order: Number(e.target.value) }))}
            />
            <label style={{ display: 'flex', gap: 8, alignItems: 'center', fontSize: '0.88rem', alignSelf: 'end', paddingBottom: 10 }}>
              <input
                type="checkbox"
                checked={defDraft.required}
                onChange={(e) => setDefDraft((d) => ({ ...d, required: e.target.checked }))}
              />
              Required
            </label>
          </div>
          <Button
            onClick={() => {
              if (!defDraft.title.trim()) return
              setDefs((list) => [...list, defDraft])
              setDefModal(false)
            }}
          >
            Add task
          </Button>
        </div>
      </Modal>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Plans
// ---------------------------------------------------------------------------

export function OnboardingPlansPage() {
  const navigate = useNavigate()
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('')
  const { data, loading, error, reload } = useApi(
    () =>
      onboardingApi.listPlans({
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
        title="Onboarding plans"
        subtitle="Track new-hire onboarding plans: checklists, documents, and progress."
        actions={
          <Button leftIcon={<Plus size={16} />} onClick={() => navigate('/app/onboarding/plans/new')}>
            New plan
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
              options={[{ value: '', label: 'All' }, ...PLAN_STATUS_OPTIONS]}
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
          <Button variant="outline" size="sm" onClick={reload} style={{ marginTop: 8 }}>
            Retry
          </Button>
        </Card>
      )}

      <Card padding={0}>
        <DataTable
          loading={loading}
          columns={[
            {
              key: 'candidate',
              header: 'Candidate',
              render: (p) => (
                <div>
                  <Link to={`/app/onboarding/plans/${p.id}`} style={{ fontWeight: 650, textDecoration: 'none' }}>
                    {p.candidate_name}
                  </Link>
                  <div className="hf-subtle" style={{ fontSize: '0.75rem' }}>{p.candidate_email}</div>
                </div>
              ),
            },
            { key: 'template', header: 'Template', render: (p) => p.template_name || '—' },
            { key: 'offer', header: 'Offer', render: (p) => p.offer_title || '—' },
            { key: 'status', header: 'Status', render: (p) => <Badge status={p.status} /> },
            {
              key: 'progress',
              header: 'Progress',
              render: (p) => (
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <div style={{ flex: 1, minWidth: 80, height: 6, borderRadius: 999, background: 'var(--hf-slate-100)' }}>
                    <div
                      style={{
                        width: `${p.progress?.task_completion_pct ?? 0}%`,
                        height: 6,
                        borderRadius: 999,
                        background: 'var(--hf-teal-600)',
                      }}
                    />
                  </div>
                  <span className="hf-subtle" style={{ fontSize: '0.75rem' }}>
                    {p.progress?.task_completion_pct ?? 0}%
                  </span>
                </div>
              ),
            },
            { key: 'start', header: 'Start date', render: (p) => formatDate(p.start_date) },
            { key: 'created', header: 'Created', render: (p) => formatDate(p.created_at) },
          ]}
          rows={data?.results || []}
          rowKey={(p) => p.id}
          emptyTitle="No plans"
          emptyDescription="Create an onboarding plan for a hired candidate."
          onRowClick={(p) => navigate(`/app/onboarding/plans/${p.id}`)}
        />
        {data && <Pagination page={page} pageSize={20} total={data.count} onChange={setPage} />}
      </Card>
    </div>
  )
}

export function OnboardingPlanFormPage() {
  const navigate = useNavigate()
  const { toast } = useToast()
  const [candidateId, setCandidateId] = useState('')
  const [offerId, setOfferId] = useState('')
  const [templateId, setTemplateId] = useState('')
  const [startDate, setStartDate] = useState('')
  const [saving, setSaving] = useState(false)
  const candidates = useApi(() => candidatesApi.list({ page_size: 100 }), [])
  const offers = useApi(() => offersApi.list({ page_size: 100 }), [])
  const templates = useApi(() => onboardingApi.listTemplates({ page_size: 100, is_active: true }), [])

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    if (!candidateId) {
      toast('Select a candidate', 'error')
      return
    }
    setSaving(true)
    try {
      const plan = await onboardingApi.createPlan({
        candidate_id: candidateId,
        offer_id: offerId || null,
        template_id: templateId || null,
        start_date: startDate || null,
      })
      toast('Plan created', 'success')
      navigate(`/app/onboarding/plans/${plan.id}`)
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Save failed', 'error')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="hf-page">
      <PageHeader title="New onboarding plan" subtitle="Create a draft plan for a hired candidate." />
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
                label="Offer (optional)"
                value={offerId}
                onChange={(e) => setOfferId(e.target.value)}
                placeholder="Select offer"
                options={(offers.data?.results || []).map((o) => ({ value: o.id, label: o.title || o.id }))}
              />
              <Select
                label="Template (optional)"
                value={templateId}
                onChange={(e) => setTemplateId(e.target.value)}
                placeholder="Select template"
                options={(templates.data?.results || []).map((t) => ({ value: t.id, label: t.name }))}
              />
            </div>
            <Input label="Start date" type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
              <Button type="button" variant="outline" onClick={() => navigate('/app/onboarding/plans')}>
                Cancel
              </Button>
              <Button type="submit" loading={saving}>
                Create plan
              </Button>
            </div>
          </div>
        </Card>
      </form>
    </div>
  )
}

export function OnboardingPlanDetailPage() {
  const { id = '' } = useParams()
  const navigate = useNavigate()
  const { toast } = useToast()
  const [tab, setTab] = useState('overview')
  const [acting, setActing] = useState(false)
  const [cancelOpen, setCancelOpen] = useState(false)
  const [taskModal, setTaskModal] = useState(false)
  const [blockTask, setBlockTask] = useState<OnboardingPlanTask | null>(null)
  const [docModal, setDocModal] = useState(false)
  const plan = useApi(() => onboardingApi.getPlan(id), [id], { enabled: Boolean(id) })
  const tasks = useApi(
    () => onboardingApi.listPlanTasks({ plan: id, page_size: 100 }),
    [id, tab],
    { enabled: Boolean(id) && (tab === 'overview' || tab === 'tasks') },
  )
  const documents = useApi(
    () => onboardingApi.listDocuments({ plan: id, page_size: 100 }),
    [id, tab],
    { enabled: Boolean(id) && tab === 'documents' },
  )

  async function runAction(action: () => Promise<unknown>, ok: string) {
    setActing(true)
    try {
      await action()
      toast(ok, 'success')
      plan.reload()
      tasks.reload()
      documents.reload()
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Action failed', 'error')
    } finally {
      setActing(false)
    }
  }

  if (plan.loading) {
    return (
      <div style={{ padding: 64, display: 'grid', placeItems: 'center' }}>
        <Spinner label="Loading plan…" />
      </div>
    )
  }

  if (plan.error || !plan.data) {
    return (
      <EmptyState
        title="Plan not found"
        description={plan.error || 'This plan may have been deleted.'}
        actionLabel="Back to plans"
        onAction={() => navigate('/app/onboarding/plans')}
      />
    )
  }

  const p = plan.data
  const progress = p.progress || { tasks: {}, documents: {}, task_completion_pct: 0, status: p.status }
  const taskRows = tasks.data?.results || []
  const docRows = documents.data?.results || []

  return (
    <div className="hf-page">
      <PageHeader
        title={p.candidate_name}
        subtitle={`${p.candidate_email} · ${p.template_name || 'No template'}${p.offer_title ? ` · ${p.offer_title}` : ''}`}
        actions={
          <>
            <Badge status={p.status} />
            {(p.status === 'draft' || p.status === 'cancelled') && (
              <Button loading={acting} onClick={() => runAction(() => onboardingApi.startPlan(id), 'Plan started')}>
                Start plan
              </Button>
            )}
            {(p.status === 'draft' || p.status === 'active') && (
              <Button variant="danger" loading={acting} onClick={() => setCancelOpen(true)}>
                Cancel plan
              </Button>
            )}
            {p.status === 'active' && (
              <Button
                variant="outline"
                loading={acting}
                onClick={() => runAction(() => onboardingApi.sendPlanReminders(id), 'Reminders queued')}
              >
                Send reminders
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
          { id: 'tasks', label: 'Tasks', count: taskRows.length },
          { id: 'documents', label: 'Documents', count: docRows.length },
        ]}
      />

      {tab === 'overview' && (
        <>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 12 }}>
            <StatCard label="Task completion" value={`${progress.task_completion_pct}%`} hint={`${progress.tasks?.completed || 0} of ${sumCounts(progress.tasks)} tasks done`} icon={<ClipboardList size={18} />} />
            <StatCard label="Pending tasks" value={progress.tasks?.pending ?? 0} hint={`${progress.tasks?.in_progress || 0} in progress`} icon={<RotateCcw size={18} />} />
            <StatCard label="Documents approved" value={progress.documents?.approved ?? 0} hint={`${progress.documents?.uploaded || 0} awaiting review`} icon={<FileText size={18} />} />
            <StatCard label="Documents missing" value={progress.documents?.missing ?? 0} icon={<XCircle size={18} />} />
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 16 }}>
            <Card title="Checklist">
              {taskRows.length ? (
                <Timeline
                  items={taskRows.map((t) => ({
                    id: t.id,
                    title: t.title,
                    description: t.notes || undefined,
                    at: t.completed_at || t.due_date || t.created_at,
                    meta: `${titleCase(t.status)}${t.due_date ? ` · due ${formatDate(t.due_date)}` : ''}`,
                  }))}
                />
              ) : (
                <EmptyState
                  title="No tasks yet"
                  description={p.status === 'active' ? 'Start the plan from a template to instantiate tasks.' : 'Tasks appear once the plan is started.'}
                />
              )}
            </Card>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              <Card title="Details">
                <dl style={{ display: 'grid', gap: 10, margin: 0, fontSize: '0.88rem' }}>
                  <Row label="Status" value={titleCase(p.status)} />
                  <Row label="Start date" value={formatDate(p.start_date)} />
                  <Row label="Template" value={p.template_name || '—'} />
                  <Row label="Offer" value={p.offer_title || '—'} />
                  <Row label="Created" value={formatDate(p.created_at)} />
                </dl>
              </Card>
              <Card title="Task status counts">
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                  {(Object.entries(progress.tasks || {}) as Array<[string, number]>).map(([status, count]) => (
                    <Badge key={status} status={status} tone="neutral">
                      {status}: {count}
                    </Badge>
                  ))}
                  {!Object.keys(progress.tasks || {}).length && <span className="hf-muted">No tasks</span>}
                </div>
              </Card>
            </div>
          </div>
        </>
      )}

      {tab === 'tasks' && (
        <Card
          padding={0}
          title="Plan tasks"
          actions={
            <Button variant="outline" size="sm" leftIcon={<Plus size={14} />} onClick={() => setTaskModal(true)}>
              Add task
            </Button>
          }
        >
          <DataTable
            loading={tasks.loading}
            columns={[
              { key: 'title', header: 'Task', render: (t) => t.title },
              { key: 'definition', header: 'From template', render: (t) => t.definition_title || 'Ad-hoc' },
              { key: 'status', header: 'Status', render: (t) => <Badge status={t.status} /> },
              { key: 'due', header: 'Due', render: (t) => formatDate(t.due_date) },
              { key: 'completed', header: 'Completed', render: (t) => (t.completed_by_name ? `${t.completed_by_name} · ${formatDate(t.completed_at)}` : '—') },
              {
                key: 'actions',
                header: '',
                render: (t) => (
                  <div style={{ display: 'flex', gap: 6 }}>
                    {t.status === 'pending' && (
                      <Button size="sm" leftIcon={<CheckCircle2 size={13} />} onClick={(e) => { e.stopPropagation(); void runAction(() => onboardingApi.completePlanTask(t.id), 'Task completed') }}>
                        Complete
                      </Button>
                    )}
                    {t.status === 'completed' && (
                      <Button size="sm" variant="outline" leftIcon={<RotateCcw size={13} />} onClick={(e) => { e.stopPropagation(); void runAction(() => onboardingApi.reopenPlanTask(t.id), 'Task reopened') }}>
                        Reopen
                      </Button>
                    )}
                    {t.status !== 'completed' && t.status !== 'blocked' && (
                      <Button size="sm" variant="outline" leftIcon={<XCircle size={13} />} onClick={(e) => { e.stopPropagation(); setBlockTask(t) }}>
                        Block
                      </Button>
                    )}
                  </div>
                ),
              },
            ]}
            rows={taskRows}
            rowKey={(t) => t.id}
            emptyTitle="No tasks"
            emptyDescription="Add a task or start the plan from a template."
          />
        </Card>
      )}

      {tab === 'documents' && (
        <Card
          padding={0}
          title="Plan documents"
          actions={
            <Button variant="outline" size="sm" leftIcon={<Plus size={14} />} onClick={() => setDocModal(true)}>
              Upload document
            </Button>
          }
        >
          <DataTable
            loading={documents.loading}
            columns={[
              { key: 'name', header: 'Name', render: (d) => d.name },
              { key: 'status', header: 'Status', render: (d) => <Badge status={d.status} /> },
              { key: 'uploaded', header: 'Uploaded by', render: (d) => d.uploaded_by_name || '—' },
              { key: 'approved', header: 'Approved by', render: (d) => d.approved_by_name || '—' },
              {
                key: 'actions',
                header: '',
                render: (d) => (
                  <div style={{ display: 'flex', gap: 6 }}>
                    {d.file && (
                      <Button size="sm" variant="outline" onClick={(e) => { e.stopPropagation(); window.open(d.file!, '_blank') }}>
                        View
                      </Button>
                    )}
                    {d.status === 'uploaded' && (
                      <>
                        <Button size="sm" leftIcon={<CheckCircle2 size={13} />} onClick={(e) => { e.stopPropagation(); void runAction(() => onboardingApi.approveDocument(d.id), 'Document approved') }}>
                          Approve
                        </Button>
                        <Button size="sm" variant="danger" leftIcon={<XCircle size={13} />} onClick={(e) => { e.stopPropagation(); void runAction(() => onboardingApi.rejectDocument(d.id), 'Document rejected') }}>
                          Reject
                        </Button>
                      </>
                    )}
                  </div>
                ),
              },
            ]}
            rows={docRows}
            rowKey={(d) => d.id}
            emptyTitle="No documents"
            emptyDescription="Upload required paperwork for this plan."
          />
        </Card>
      )}

      <ConfirmDialog
        open={cancelOpen}
        title="Cancel onboarding plan"
        message={`Cancel the onboarding plan for ${p.candidate_name}? This cannot be undone.`}
        confirmLabel="Cancel plan"
        danger
        loading={acting}
        onCancel={() => setCancelOpen(false)}
        onConfirm={() => {
          setCancelOpen(false)
          void runAction(() => onboardingApi.cancelPlan(id), 'Plan cancelled')
        }}
      />
      <AddTaskModal open={taskModal} planId={id} onClose={() => setTaskModal(false)} onDone={() => { tasks.reload(); plan.reload() }} />
      <BlockTaskModal task={blockTask} onClose={() => setBlockTask(null)} onDone={() => { tasks.reload(); plan.reload() }} />
      <UploadDocumentModal open={docModal} planId={id} onClose={() => setDocModal(false)} onDone={() => { documents.reload(); plan.reload() }} />
    </div>
  )
}

function AddTaskModal({
  open,
  planId,
  onClose,
  onDone,
}: {
  open: boolean
  planId: string
  onClose: () => void
  onDone: () => void
}) {
  const { toast } = useToast()
  const [title, setTitle] = useState('')
  const [dueDate, setDueDate] = useState('')
  const [saving, setSaving] = useState(false)

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setSaving(true)
    try {
      await onboardingApi.createPlanTask({ plan_id: planId, title, due_date: dueDate || null })
      toast('Task added', 'success')
      onDone()
      onClose()
      setTitle('')
      setDueDate('')
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Failed', 'error')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal open={open} onClose={onClose} title="Add plan task">
      <form onSubmit={onSubmit} style={{ display: 'grid', gap: 12 }}>
        <Input label="Title" required value={title} onChange={(e) => setTitle(e.target.value)} />
        <Input label="Due date" type="date" value={dueDate} onChange={(e) => setDueDate(e.target.value)} />
        <Button type="submit" loading={saving}>
          Add task
        </Button>
      </form>
    </Modal>
  )
}

function BlockTaskModal({
  task,
  onClose,
  onDone,
}: {
  task: OnboardingPlanTask | null
  onClose: () => void
  onDone: () => void
}) {
  const { toast } = useToast()
  const [note, setNote] = useState('')
  const [saving, setSaving] = useState(false)

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    if (!task) return
    setSaving(true)
    try {
      await onboardingApi.blockPlanTask(task.id, { note })
      toast('Task blocked', 'success')
      onDone()
      onClose()
      setNote('')
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Failed', 'error')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal open={Boolean(task)} onClose={onClose} title="Block task">
      <form onSubmit={onSubmit} style={{ display: 'grid', gap: 12 }}>
        <p className="hf-muted" style={{ fontSize: '0.88rem' }}>{task?.title}</p>
        <Textarea label="Note (optional)" value={note} onChange={(e) => setNote(e.target.value)} />
        <Button type="submit" loading={saving}>
          Block task
        </Button>
      </form>
    </Modal>
  )
}

function UploadDocumentModal({
  open,
  planId,
  onClose,
  onDone,
}: {
  open: boolean
  planId: string
  onClose: () => void
  onDone: () => void
}) {
  const { toast } = useToast()
  const [name, setName] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [saving, setSaving] = useState(false)

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    if (!name.trim()) {
      toast('Enter a document name', 'error')
      return
    }
    setSaving(true)
    try {
      const fd = new FormData()
      fd.append('plan_id', planId)
      fd.append('name', name)
      if (file) fd.append('file', file)
      await onboardingApi.createDocument(fd)
      toast('Document uploaded', 'success')
      onDone()
      onClose()
      setName('')
      setFile(null)
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Upload failed', 'error')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal open={open} onClose={onClose} title="Upload document">
      <form onSubmit={onSubmit} style={{ display: 'grid', gap: 12 }}>
        <Input label="Name" required value={name} onChange={(e) => setName(e.target.value)} />
        <label style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--hf-text-muted)' }}>File (optional)</span>
          <input
            type="file"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
            style={{ fontSize: '0.85rem' }}
          />
        </label>
        <Button type="submit" loading={saving}>
          Upload
        </Button>
      </form>
    </Modal>
  )
}

function sumCounts(counts?: Record<string, number>) {
  return Object.values(counts || {}).reduce((a, b) => a + b, 0)
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}>
      <dt className="hf-muted">{label}</dt>
      <dd style={{ margin: 0, fontWeight: 600 }}>{value}</dd>
    </div>
  )
}
