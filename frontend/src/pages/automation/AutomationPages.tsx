/**
 * AutomationPages.tsx — Workflow automation frontend.
 *
 * Exported components & suggested routes (wired by main agent in App.tsx):
 *   AutomationRulesPage       → /app/automation
 *   AutomationRuleFormPage    → /app/automation/new, /app/automation/:id/edit
 *   AutomationRuleDetailPage  → /app/automation/:id
 *   RuleExecutionsPage        → /app/automation/executions
 */
import { useEffect, useState, type FormEvent } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { Activity, Copy, Pencil, Play, Plus, Trash2, Zap } from 'lucide-react'
import {
  automationEventsApi,
  automationRulesApi,
  ruleActionLogsApi,
  ruleExecutionsApi,
} from '../../api/automation'
import type { AutomationRule, RuleActionLog, RuleExecution } from '../../api/automation'
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
  Tabs,
  Textarea,
  Timeline,
  useToast,
} from '../../components/ui'
import type { TimelineItem } from '../../components/ui'
import { formatDateTime, titleCase } from '../../utils/format'
import { ApiError } from '../../api/http'

const TRIGGERS = [
  { value: 'stage_change', label: 'Stage change' },
  { value: 'job_published', label: 'Job published' },
  { value: 'candidate_created', label: 'Candidate created' },
  { value: 'offer_accepted', label: 'Offer accepted' },
  { value: 'assessment_completed', label: 'Assessment completed' },
  { value: 'date_based', label: 'Date based' },
]

const EXECUTION_STATUSES = [
  { value: 'matched', label: 'Matched' },
  { value: 'skipped', label: 'Skipped' },
  { value: 'failed', label: 'Failed' },
]

export function AutomationRulesPage() {
  const navigate = useNavigate()
  const { toast } = useToast()
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [trigger, setTrigger] = useState('')
  const [active, setActive] = useState('')
  const [acting, setActing] = useState<string | null>(null)
  const [deleting, setDeleting] = useState<AutomationRule | null>(null)
  const [removing, setRemoving] = useState(false)
  const rules = useApi(
    () =>
      automationRulesApi.list({
        page,
        page_size: 20,
        search: search || undefined,
        trigger: trigger || undefined,
        is_active: active === '' ? undefined : active === 'true',
      }),
    [page, search, trigger, active, deleting],
    { enabled: true },
  )

  async function toggleActive(rule: AutomationRule) {
    setActing(rule.id)
    try {
      if (rule.is_active) {
        await automationRulesApi.disable(rule.id)
        toast('Rule disabled', 'success')
      } else {
        await automationRulesApi.enable(rule.id)
        toast('Rule enabled', 'success')
      }
      rules.reload()
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Action failed', 'error')
    } finally {
      setActing(null)
    }
  }

  async function onDuplicate(ruleId: string) {
    setActing(ruleId)
    try {
      await automationRulesApi.duplicate(ruleId)
      toast('Rule duplicated', 'success')
      rules.reload()
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Duplicate failed', 'error')
    } finally {
      setActing(null)
    }
  }

  async function onDelete() {
    if (!deleting) return
    setRemoving(true)
    try {
      await automationRulesApi.remove(deleting.id)
      toast('Rule deleted', 'success')
      setDeleting(null)
      rules.reload()
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Delete failed', 'error')
    } finally {
      setRemoving(false)
    }
  }

  return (
    <div className="hf-page">
      <PageHeader
        title="Automation"
        subtitle="Build rules that react to recruiting events automatically."
        actions={
          <>
            <Button variant="outline" leftIcon={<Activity size={15} />} onClick={() => navigate('/app/automation/executions')}>
              Executions
            </Button>
            <Button leftIcon={<Plus size={16} />} onClick={() => navigate('/app/automation/new')}>
              New rule
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
          searchPlaceholder="Search rules…"
          filters={[
            {
              key: 'trigger',
              label: 'Trigger',
              value: trigger,
              onChange: (v) => {
                setPage(1)
                setTrigger(v)
              },
              options: TRIGGERS,
            },
            {
              key: 'active',
              label: 'Active',
              value: active,
              onChange: (v) => {
                setPage(1)
                setActive(v)
              },
              options: [
                { value: 'true', label: 'Active' },
                { value: 'false', label: 'Inactive' },
              ],
            },
          ]}
          onClear={() => {
            setSearch('')
            setTrigger('')
            setActive('')
            setPage(1)
          }}
        />
      </Card>
      <Card padding={0}>
        <DataTable
          loading={rules.loading}
          columns={[
            {
              key: 'name',
              header: 'Rule',
              render: (r: AutomationRule) => (
                <div>
                  <Link to={`/app/automation/${r.id}`} style={{ fontWeight: 650, textDecoration: 'none' }}>
                    {r.name}
                  </Link>
                  {r.description && (
                    <div className="hf-subtle" style={{ fontSize: '0.75rem', maxWidth: 420, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {r.description}
                    </div>
                  )}
                </div>
              ),
            },
            { key: 'trigger', header: 'Trigger', render: (r: AutomationRule) => titleCase(r.trigger) },
            { key: 'actions_count', header: 'Actions', render: (r: AutomationRule) => String((r.actions || []).length) },
            { key: 'run_count', header: 'Runs', render: (r: AutomationRule) => r.run_count },
            { key: 'last_run', header: 'Last run', render: (r: AutomationRule) => formatDateTime(r.last_run_at) },
            {
              key: 'active',
              header: 'Active',
              render: (r: AutomationRule) => <Badge tone={r.is_active ? 'success' : 'neutral'}>{r.is_active ? 'Yes' : 'No'}</Badge>,
            },
            {
              key: 'actions',
              header: '',
              render: (r: AutomationRule) => (
                <div style={{ display: 'flex', gap: 6, justifyContent: 'flex-end' }}>
                  <Button size="sm" variant="outline" loading={acting === r.id} onClick={() => void toggleActive(r)}>
                    {r.is_active ? 'Disable' : 'Enable'}
                  </Button>
                  <Button size="sm" variant="ghost" loading={acting === r.id} onClick={() => void onDuplicate(r.id)} aria-label="Duplicate">
                    <Copy size={14} />
                  </Button>
                  <Button size="sm" variant="ghost" onClick={() => setDeleting(r)} aria-label="Delete">
                    <Trash2 size={14} />
                  </Button>
                </div>
              ),
            },
          ]}
          rows={rules.data?.results || []}
          rowKey={(r) => r.id}
          emptyTitle="No automation rules"
          emptyDescription="Create a rule to automate actions like emails, tasks, and stage moves."
          onRowClick={(r) => navigate(`/app/automation/${r.id}`)}
        />
        {rules.data && <Pagination page={page} pageSize={20} total={rules.data.count} onChange={setPage} />}
      </Card>
      <ConfirmDialog
        open={Boolean(deleting)}
        title="Delete automation rule"
        message={`Delete "${deleting?.name || 'this rule'}"? This cannot be undone.`}
        confirmLabel="Delete"
        danger
        loading={removing}
        onConfirm={() => void onDelete()}
        onCancel={() => setDeleting(null)}
      />
    </div>
  )
}

const emptyRule = {
  name: '',
  description: '',
  trigger: 'stage_change',
  trigger_config: '{}',
  conditions: '[]',
  actions: '[]',
  is_active: true,
}

export function AutomationRuleFormPage() {
  const { id } = useParams()
  const isEdit = Boolean(id)
  const navigate = useNavigate()
  const { toast } = useToast()
  const [form, setForm] = useState(emptyRule)
  const [loading, setLoading] = useState(isEdit)
  const [saving, setSaving] = useState(false)
  const rule = useApi(() => automationRulesApi.get(id!), [id], { enabled: isEdit })

  useEffect(() => {
    if (!rule.data) return
    setForm({
      name: rule.data.name,
      description: rule.data.description || '',
      trigger: rule.data.trigger,
      trigger_config: JSON.stringify(rule.data.trigger_config || {}, null, 2),
      conditions: JSON.stringify(rule.data.conditions || [], null, 2),
      actions: JSON.stringify(rule.data.actions || [], null, 2),
      is_active: rule.data.is_active,
    })
    setLoading(false)
  }, [rule.data])

  function parseJson(label: string, value: string): unknown {
    try {
      return JSON.parse(value || 'null')
    } catch {
      toast(`${label} must be valid JSON`, 'error')
      throw new Error('invalid json')
    }
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    if (!form.name.trim()) {
      toast('Rule name is required', 'error')
      return
    }
    let triggerConfig: unknown
    let conditions: unknown
    let actions: unknown
    try {
      triggerConfig = parseJson('Trigger config', form.trigger_config)
      conditions = parseJson('Conditions', form.conditions)
      actions = parseJson('Actions', form.actions)
    } catch {
      return
    }
    setSaving(true)
    const payload = {
      name: form.name,
      description: form.description,
      trigger: form.trigger,
      trigger_config: triggerConfig || {},
      conditions: conditions || [],
      actions: actions || [],
      is_active: form.is_active,
    }
    try {
      const saved = isEdit ? await automationRulesApi.update(id!, payload) : await automationRulesApi.create(payload)
      toast(isEdit ? 'Rule updated' : 'Rule created', 'success')
      navigate(`/app/automation/${saved.id}`)
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Save failed', 'error')
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div style={{ padding: 64, display: 'grid', placeItems: 'center' }}>
        <Spinner label="Loading rule…" />
      </div>
    )
  }

  if (isEdit && !rule.loading && rule.error) {
    return (
      <EmptyState title="Rule not found" description={rule.error} actionLabel="Back" onAction={() => navigate('/app/automation')} />
    )
  }

  return (
    <div className="hf-page">
      <PageHeader
        title={isEdit ? 'Edit automation rule' : 'New automation rule'}
        subtitle="Define the trigger, conditions, and actions for this workflow."
      />
      <form onSubmit={onSubmit}>
        <Card>
          <div style={{ display: 'grid', gap: 14 }}>
            <Input label="Rule name" required value={form.name} onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))} />
            <Textarea label="Description" value={form.description} onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))} />
            <Select
              label="Trigger"
              value={form.trigger}
              onChange={(e) => setForm((f) => ({ ...f, trigger: e.target.value }))}
              options={TRIGGERS}
            />
            <Textarea
              label="Trigger config (JSON)"
              value={form.trigger_config}
              onChange={(e) => setForm((f) => ({ ...f, trigger_config: e.target.value }))}
              hint='e.g. {"stage_id": "...", "days": 2}'
            />
            <Textarea
              label="Conditions (JSON)"
              value={form.conditions}
              onChange={(e) => setForm((f) => ({ ...f, conditions: e.target.value }))}
              hint='e.g. [{"field": "job.department", "operator": "eq", "value": "eng"}] or {"operator": "and", "rules": [...]}'
            />
            <Textarea
              label="Actions (JSON)"
              value={form.actions}
              onChange={(e) => setForm((f) => ({ ...f, actions: e.target.value }))}
              hint='e.g. [{"type": "send_email", "params": {"subject": "Welcome", "to": "candidate"}}]'
            />
            <label style={{ display: 'flex', gap: 8, alignItems: 'center', fontSize: '0.88rem' }}>
              <input type="checkbox" checked={form.is_active} onChange={(e) => setForm((f) => ({ ...f, is_active: e.target.checked }))} />
              Rule active
            </label>
            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
              <Button type="button" variant="outline" onClick={() => navigate(-1)}>
                Cancel
              </Button>
              <Button type="submit" loading={saving}>
                {isEdit ? 'Save changes' : 'Create rule'}
              </Button>
            </div>
          </div>
        </Card>
      </form>
    </div>
  )
}

export function AutomationRuleDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { toast } = useToast()
  const [tab, setTab] = useState('overview')
  const [acting, setActing] = useState(false)
  const [testOpen, setTestOpen] = useState(false)
  const [testForm, setTestForm] = useState({ entity_type: '', entity_id: '' })
  const [testResult, setTestResult] = useState<Record<string, unknown> | null>(null)
  const [testing, setTesting] = useState(false)
  const rule = useApi(() => automationRulesApi.get(id!), [id], { enabled: Boolean(id) })
  const executions = useApi(
    () => ruleExecutionsApi.list({ rule: id, page_size: 20 }),
    [id, tab],
    { enabled: Boolean(id) && tab === 'executions' },
  )

  async function runAction(action: () => Promise<unknown>, ok: string) {
    setActing(true)
    try {
      await action()
      toast(ok, 'success')
      rule.reload()
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Action failed', 'error')
    } finally {
      setActing(false)
    }
  }

  async function onTestRun(e: FormEvent) {
    e.preventDefault()
    setTesting(true)
    setTestResult(null)
    try {
      const result = await automationRulesApi.testRun(id!, testForm)
      setTestResult(result as unknown as Record<string, unknown>)
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Test run failed', 'error')
    } finally {
      setTesting(false)
    }
  }

  if (rule.loading) {
    return (
      <div style={{ padding: 64, display: 'grid', placeItems: 'center' }}>
        <Spinner label="Loading rule…" />
      </div>
    )
  }

  if (rule.error || !rule.data) {
    return (
      <EmptyState
        title="Rule not found"
        description={rule.error || 'This rule may have been deleted.'}
        actionLabel="Back to automation"
        onAction={() => navigate('/app/automation')}
      />
    )
  }

  const r = rule.data

  return (
    <div className="hf-page">
      <PageHeader
        title={r.name}
        subtitle={titleCase(r.trigger)}
        actions={
          <>
            <Badge tone={r.is_active ? 'success' : 'neutral'}>{r.is_active ? 'Active' : 'Inactive'}</Badge>
            <Button variant="outline" leftIcon={<Play size={14} />} onClick={() => setTestOpen(true)}>
              Test run
            </Button>
            <Button variant="outline" leftIcon={<Pencil size={14} />} onClick={() => navigate(`/app/automation/${id}/edit`)}>
              Edit
            </Button>
            {r.is_active ? (
              <Button variant="outline" loading={acting} onClick={() => void runAction(() => automationRulesApi.disable(id!), 'Rule disabled')}>
                Disable
              </Button>
            ) : (
              <Button loading={acting} onClick={() => void runAction(() => automationRulesApi.enable(id!), 'Rule enabled')}>
                Enable
              </Button>
            )}
            <Button variant="outline" loading={acting} onClick={() => void runAction(() => automationRulesApi.duplicate(id!), 'Rule duplicated')}>
              <Copy size={14} /> Duplicate
            </Button>
          </>
        }
      />
      <Tabs
        value={tab}
        onChange={setTab}
        items={[
          { id: 'overview', label: 'Overview' },
          { id: 'executions', label: 'Executions' },
        ]}
      />
      {tab === 'overview' && (
        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 16 }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <Card title="Description">
              <div style={{ whiteSpace: 'pre-wrap', lineHeight: 1.6 }} className="hf-muted">
                {r.description || 'No description.'}
              </div>
            </Card>
            <Card title="Conditions">
              <pre
                style={{
                  margin: 0,
                  fontSize: '0.8rem',
                  whiteSpace: 'pre-wrap',
                  color: 'var(--hf-text-muted)',
                  background: 'var(--hf-slate-50, #f8fafc)',
                  borderRadius: 8,
                  padding: 12,
                }}
              >
                {JSON.stringify(r.conditions, null, 2)}
              </pre>
            </Card>
            <Card title="Actions">
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {(r.actions || []).map((a, idx) => (
                  <div
                    key={idx}
                    style={{
                      padding: 10,
                      borderRadius: 8,
                      border: '1px solid var(--hf-border)',
                      fontSize: '0.88rem',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
                      <strong>{titleCase(a.type)}</strong>
                      <Badge tone="info">#{idx + 1}</Badge>
                    </div>
                    {a.params && (
                      <pre
                        style={{
                          margin: '8px 0 0',
                          fontSize: '0.75rem',
                          whiteSpace: 'pre-wrap',
                          color: 'var(--hf-text-muted)',
                        }}
                      >
                        {JSON.stringify(a.params, null, 2)}
                      </pre>
                    )}
                  </div>
                ))}
                {!r.actions?.length && <span className="hf-muted">No actions defined.</span>}
              </div>
            </Card>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <Card title="Trigger config">
              <pre
                style={{
                  margin: 0,
                  fontSize: '0.8rem',
                  whiteSpace: 'pre-wrap',
                  color: 'var(--hf-text-muted)',
                }}
              >
                {JSON.stringify(r.trigger_config || {}, null, 2)}
              </pre>
            </Card>
            <Card title="Stats">
              <dl style={{ display: 'grid', gap: 10, margin: 0, fontSize: '0.88rem' }}>
                <Row label="Run count" value={String(r.run_count)} />
                <Row label="Last run" value={formatDateTime(r.last_run_at)} />
                <Row label="Created" value={formatDateTime(r.created_at)} />
              </dl>
            </Card>
          </div>
        </div>
      )}
      {tab === 'executions' && (
        <Card padding={0} title="Executions">
          <DataTable
            loading={executions.loading}
            columns={[
              {
                key: 'when',
                header: 'Executed',
                render: (x: RuleExecution) => (
                  <div>
                    <div>{formatDateTime(x.executed_at)}</div>
                    <div className="hf-subtle" style={{ fontSize: '0.75rem' }}>{x.trigger_event}</div>
                  </div>
                ),
              },
              { key: 'entity', header: 'Entity', render: (x: RuleExecution) => `${x.entity_type}${x.entity_id ? ` · ${x.entity_id}` : ''}` || '—' },
              { key: 'status', header: 'Status', render: (x: RuleExecution) => <Badge status={x.status} /> },
              {
                key: 'error',
                header: 'Error',
                render: (x: RuleExecution) => <span style={{ fontSize: '0.8rem' }}>{x.error || '—'}</span>,
              },
              {
                key: 'actions',
                header: '',
                render: (x: RuleExecution) =>
                  x.status === 'failed' ? (
                    <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => void retry(x.id)}
                      >
                        Retry
                      </Button>
                    </div>
                  ) : null,
              },
            ]}
            rows={executions.data?.results || []}
            rowKey={(x) => x.id}
            emptyTitle="No executions"
            emptyDescription="Executions appear when this rule runs."
          />
        </Card>
      )}

      <Modal open={testOpen} onClose={() => setTestOpen(false)} title="Test run" width={560}>
        <form onSubmit={onTestRun} style={{ display: 'grid', gap: 12 }}>
          <Input
            label="Entity type"
            value={testForm.entity_type}
            onChange={(e) => setTestForm((f) => ({ ...f, entity_type: e.target.value }))}
            placeholder="e.g. application, candidate, job"
          />
          <Input
            label="Entity ID"
            value={testForm.entity_id}
            onChange={(e) => setTestForm((f) => ({ ...f, entity_id: e.target.value }))}
            placeholder="UUID of the entity to simulate"
          />
          <Button type="submit" loading={testing} leftIcon={<Zap size={14} />}>
            Run test
          </Button>
        </form>
        {testResult && (
          <div style={{ marginTop: 14 }}>
            <Card title="Result">
              <pre
                style={{
                  margin: 0,
                  fontSize: '0.78rem',
                  whiteSpace: 'pre-wrap',
                  color: 'var(--hf-text-muted)',
                }}
              >
                {JSON.stringify(testResult, null, 2)}
              </pre>
            </Card>
          </div>
        )}
      </Modal>
    </div>
  )

  async function retry(executionId: string) {
    try {
      await ruleExecutionsApi.retry(executionId)
      toast('Execution retried', 'success')
      executions.reload()
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Retry failed', 'error')
    }
  }
}

export function RuleExecutionsPage() {
  const { toast } = useToast()
  const [page, setPage] = useState(1)
  const [status, setStatus] = useState('')
  const [search, setSearch] = useState('')
  const [logsOpen, setLogsOpen] = useState(false)
  const [logs, setLogs] = useState<RuleActionLog[]>([])
  const [logsLoading, setLogsLoading] = useState(false)
  const [fireOpen, setFireOpen] = useState(false)
  const [fireForm, setFireForm] = useState({ trigger_event: '', entity_type: '', entity_id: '', async_mode: false })
  const [firing, setFiring] = useState(false)
  const executions = useApi(
    () =>
      ruleExecutionsApi.list({
        page,
        page_size: 20,
        search: search || undefined,
        status: status || undefined,
      }),
    [page, search, status],
    { enabled: true },
  )
  const eventInfo = useApi(() => automationEventsApi.info(), [], { enabled: true })

  async function openLogs(executionId: string) {
    setLogsOpen(true)
    setLogsLoading(true)
    setLogs([])
    try {
      const res = await ruleActionLogsApi.list({ execution: executionId, page_size: 100 })
      setLogs(res.results || [])
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Failed to load logs', 'error')
    } finally {
      setLogsLoading(false)
    }
  }

  async function onRetry(executionId: string) {
    try {
      await ruleExecutionsApi.retry(executionId)
      toast('Execution retried', 'success')
      executions.reload()
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Retry failed', 'error')
    }
  }

  async function onFire(e: FormEvent) {
    e.preventDefault()
    if (!fireForm.trigger_event) {
      toast('Trigger event is required', 'error')
      return
    }
    setFiring(true)
    try {
      const result = await automationEventsApi.fire(fireForm)
      toast(`Fired — ${(result.results || []).length} rule(s) evaluated`, 'success')
      setFireOpen(false)
      executions.reload()
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Fire failed', 'error')
    } finally {
      setFiring(false)
    }
  }

  const timelineItems: TimelineItem[] = logs.map((log) => ({
    id: log.id,
    title: `#${log.action_index + 1} · ${titleCase(log.action_type)}`,
    description: JSON.stringify(log.detail || {}),
    at: log.executed_at || log.created_at,
    meta: titleCase(log.status),
  }))

  return (
    <div className="hf-page">
      <PageHeader
        title="Rule executions"
        subtitle="History of automation rule evaluations across your organization."
        actions={
          <Button variant="outline" leftIcon={<Zap size={15} />} onClick={() => setFireOpen(true)}>
            Fire event
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
          searchPlaceholder="Search by error…"
          filters={[
            {
              key: 'status',
              label: 'Status',
              value: status,
              onChange: (v) => {
                setPage(1)
                setStatus(v)
              },
              options: EXECUTION_STATUSES,
            },
          ]}
          onClear={() => {
            setSearch('')
            setStatus('')
            setPage(1)
          }}
        />
      </Card>
      <Card padding={0}>
        <DataTable
          loading={executions.loading}
          columns={[
            {
              key: 'rule',
              header: 'Rule',
              render: (x: RuleExecution) => (
                <Link to={`/app/automation/${x.rule}`} style={{ fontWeight: 600, textDecoration: 'none' }}>
                  {x.rule_name || x.rule}
                </Link>
              ),
            },
            { key: 'trigger', header: 'Trigger', render: (x: RuleExecution) => titleCase(x.trigger_event) },
            { key: 'entity', header: 'Entity', render: (x: RuleExecution) => `${x.entity_type}${x.entity_id ? ` · ${x.entity_id}` : ''}` || '—' },
            { key: 'when', header: 'Executed', render: (x: RuleExecution) => formatDateTime(x.executed_at) },
            { key: 'status', header: 'Status', render: (x: RuleExecution) => <Badge status={x.status} /> },
            {
              key: 'actions',
              header: '',
              render: (x: RuleExecution) => (
                <div style={{ display: 'flex', gap: 6, justifyContent: 'flex-end' }}>
                  <Button size="sm" variant="outline" onClick={() => void openLogs(x.id)}>
                    Logs
                  </Button>
                  {x.status === 'failed' && (
                    <Button size="sm" variant="ghost" onClick={() => void onRetry(x.id)}>
                      Retry
                    </Button>
                  )}
                </div>
              ),
            },
          ]}
          rows={executions.data?.results || []}
          rowKey={(x) => x.id}
          emptyTitle="No executions"
          emptyDescription="Rule evaluations will appear here as triggers fire."
        />
        {executions.data && <Pagination page={page} pageSize={20} total={executions.data.count} onChange={setPage} />}
      </Card>

      <Modal open={logsOpen} onClose={() => setLogsOpen(false)} title="Action logs" width={560}>
        {logsLoading ? (
          <div style={{ padding: 32, display: 'grid', placeItems: 'center' }}>
            <Spinner />
          </div>
        ) : (
          <Timeline items={timelineItems} />
        )}
      </Modal>

      <Modal open={fireOpen} onClose={() => setFireOpen(false)} title="Fire trigger event" width={480}>
        <form onSubmit={onFire} style={{ display: 'grid', gap: 12 }}>
          <Select
            label="Trigger event"
            required
            value={fireForm.trigger_event}
            onChange={(e) => setFireForm((f) => ({ ...f, trigger_event: e.target.value }))}
            placeholder="Select trigger"
            options={(eventInfo.data?.triggers || TRIGGERS.map((t) => t.value)).map((t) => ({ value: t, label: titleCase(t) }))}
          />
          <Input
            label="Entity type"
            value={fireForm.entity_type}
            onChange={(e) => setFireForm((f) => ({ ...f, entity_type: e.target.value }))}
            placeholder="e.g. application, candidate, job"
          />
          <Input
            label="Entity ID"
            value={fireForm.entity_id}
            onChange={(e) => setFireForm((f) => ({ ...f, entity_id: e.target.value }))}
            placeholder="UUID of the entity"
          />
          <label style={{ display: 'flex', gap: 8, alignItems: 'center', fontSize: '0.88rem' }}>
            <input type="checkbox" checked={fireForm.async_mode} onChange={(e) => setFireForm((f) => ({ ...f, async_mode: e.target.checked }))} />
            Run asynchronously (queue)
          </label>
          <Button type="submit" loading={firing} leftIcon={<Zap size={14} />}>
            Fire event
          </Button>
        </form>
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
