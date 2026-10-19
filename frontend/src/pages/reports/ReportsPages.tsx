/**
 * Reports pages.
 *
 * Exported components and suggested routes (wire into App.tsx):
 *   - ReportsPage           -> /app/reports
 *   - ReportDetailPage      -> /app/reports/:id
 *   - ReportFormPage        -> /app/reports/new, /app/reports/:id/edit
 *   - DashboardWidgetsPage  -> /app/reports/widgets
 */
import { useEffect, useState, type FormEvent } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import {
  ArrowDown,
  ArrowUp,
  CalendarClock,
  Eye,
  LayoutDashboard,
  Pencil,
  Play,
  Plus,
  RefreshCw,
  Trash2,
} from 'lucide-react'
import { reportsApi, type DashboardWidget, type ReportDefinition } from '../../api/reports'
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
  useToast,
} from '../../components/ui'
import { formatDate, formatDateTime } from '../../utils/format'
import { ApiError } from '../../api/http'

// NOTE: the shared <Select> emits option labels as values, so filter/form
// options carry display labels and are mapped back to API values on submit.
const REPORT_TYPE_OPTIONS = [
  { value: 'Hires', label: 'Hires' },
  { value: 'Pipeline', label: 'Pipeline' },
  { value: 'Source', label: 'Source' },
  { value: 'Time to Fill', label: 'Time to Fill' },
  { value: 'Offer Acceptance', label: 'Offer Acceptance' },
  { value: 'Interview', label: 'Interview' },
]
const REPORT_TYPE_VALUES: Record<string, string> = {
  Hires: 'hires',
  Pipeline: 'pipeline',
  Source: 'source',
  'Time to Fill': 'time_to_fill',
  'Offer Acceptance': 'offer_acceptance',
  Interview: 'interview',
}

const RUN_STATUS_OPTIONS = [
  { value: 'Queued', label: 'Queued' },
  { value: 'Running', label: 'Running' },
  { value: 'Completed', label: 'Completed' },
  { value: 'Failed', label: 'Failed' },
]
const RUN_STATUS_VALUES: Record<string, string> = {
  Queued: 'queued',
  Running: 'running',
  Completed: 'completed',
  Failed: 'failed',
}

const WIDGET_TYPE_OPTIONS = [
  { value: 'Summary', label: 'Summary' },
  { value: 'Bar Chart', label: 'Bar Chart' },
  { value: 'Line Chart', label: 'Line Chart' },
  { value: 'Pie Chart', label: 'Pie Chart' },
  { value: 'Table', label: 'Table' },
  { value: 'Recent Items', label: 'Recent Items' },
]
const WIDGET_TYPE_VALUES: Record<string, string> = {
  Summary: 'summary',
  'Bar Chart': 'bar',
  'Line Chart': 'line',
  'Pie Chart': 'pie',
  Table: 'table',
  'Recent Items': 'recent',
}

function reportTypeLabel(value?: string) {
  if (!value) return ''
  return REPORT_TYPE_OPTIONS.find((o) => REPORT_TYPE_VALUES[o.value] === value)?.value ?? value
}
function widgetTypeLabel(value?: string) {
  if (!value) return ''
  return WIDGET_TYPE_OPTIONS.find((o) => WIDGET_TYPE_VALUES[o.value] === value)?.value ?? value
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}>
      <dt className="hf-muted">{label}</dt>
      <dd style={{ margin: 0, fontWeight: 600 }}>{value}</dd>
    </div>
  )
}

export function ReportsPage() {
  const navigate = useNavigate()
  const { toast } = useToast()
  const [tab, setTab] = useState('definitions')
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [type, setType] = useState('')
  const [runStatus, setRunStatus] = useState('')
  const [builderOpen, setBuilderOpen] = useState(false)

  const definitions = useApi(
    () =>
      reportsApi.definitions.list({
        page,
        page_size: 20,
        search: search || undefined,
        report_type: type ? REPORT_TYPE_VALUES[type] : undefined,
      }),
    [page, search, type, tab],
    { enabled: tab === 'definitions' },
  )
  const runs = useApi(
    () =>
      reportsApi.runs.list({
        page,
        page_size: 20,
        search: search || undefined,
        status: runStatus ? RUN_STATUS_VALUES[runStatus] : undefined,
      }),
    [page, search, runStatus, tab],
    { enabled: tab === 'runs' },
  )
  const widgets = useApi(
    () => reportsApi.widgets.list({ page_size: 50 }),
    [tab],
    { enabled: tab === 'widgets' },
  )

  function resetPage() {
    setPage(1)
  }

  return (
    <div className="hf-page">
      <PageHeader
        title="Reports"
        subtitle="Define scheduled reports, review run history, and manage dashboard widgets."
        actions={
          <Button leftIcon={<Plus size={16} />} onClick={() => setBuilderOpen(true)}>
            New report
          </Button>
        }
      />
      <Tabs
        value={tab}
        onChange={(t) => {
          setTab(t)
          resetPage()
        }}
        items={[
          { id: 'definitions', label: 'Definitions', count: definitions.data?.count },
          { id: 'runs', label: 'Run history', count: runs.data?.count },
          { id: 'widgets', label: 'Widgets', count: widgets.data?.count },
        ]}
      />

      {tab === 'definitions' && (
        <>
          <Card padding="1rem">
            <FilterBarReports
              search={search}
              onSearchChange={(v) => {
                resetPage()
                setSearch(v)
              }}
              type={type}
              onTypeChange={(v) => {
                resetPage()
                setType(v)
              }}
              onClear={() => {
                setSearch('')
                setType('')
                resetPage()
              }}
            />
          </Card>
          <Card padding={0}>
            <DataTable
              loading={definitions.loading}
              columns={[
                {
                  key: 'name',
                  header: 'Name',
                  render: (d: ReportDefinition) => (
                    <div>
                      <Link
                        to={`/app/reports/${d.id}`}
                        style={{ fontWeight: 650, textDecoration: 'none' }}
                      >
                        {d.name}
                      </Link>
                      <div className="hf-subtle" style={{ fontSize: '0.75rem' }}>
                        {reportTypeLabel(d.report_type)}
                      </div>
                    </div>
                  ),
                },
                {
                  key: 'schedule',
                  header: 'Schedule',
                  render: (d: ReportDefinition) =>
                    d.schedule_enabled ? (
                      <Badge tone="success">
                        <CalendarClock size={12} /> {d.schedule_cron || 'On'}
                      </Badge>
                    ) : (
                      <Badge tone="neutral">Off</Badge>
                    ),
                },
                {
                  key: 'visibility',
                  header: 'Visibility',
                  render: (d: ReportDefinition) =>
                    d.is_public ? <Badge tone="info">Public</Badge> : <Badge>Private</Badge>,
                },
                {
                  key: 'last_run',
                  header: 'Last run',
                  render: (d: ReportDefinition) => formatDateTime(d.last_run_at),
                },
              ]}
              rows={definitions.data?.results || []}
              rowKey={(d) => d.id}
              emptyTitle="No report definitions"
              emptyDescription="Create a report definition to start tracking hiring metrics."
              onRowClick={(d) => navigate(`/app/reports/${d.id}`)}
            />
            {definitions.data && (
              <Pagination page={page} pageSize={20} total={definitions.data.count} onChange={setPage} />
            )}
          </Card>
        </>
      )}

      {tab === 'runs' && (
        <>
          <Card padding="1rem">
            <FilterBarReports
              search={search}
              onSearchChange={(v) => {
                resetPage()
                setSearch(v)
              }}
              type={type}
              onTypeChange={(v) => {
                resetPage()
                setType(v)
              }}
              onClear={() => {
                setSearch('')
                setType('')
                resetPage()
              }}
              runFilter
              runStatus={runStatus}
              onRunStatusChange={(v) => {
                resetPage()
                setRunStatus(v)
              }}
            />
          </Card>
          <Card padding={0}>
            <DataTable
              loading={runs.loading}
              columns={[
                {
                  key: 'definition',
                  header: 'Report',
                  render: (r) => (
                    <div>
                      <Link
                        to={`/app/reports/${r.definition}`}
                        style={{ fontWeight: 600, textDecoration: 'none' }}
                      >
                        {r.definition_name || '—'}
                      </Link>
                      <div className="hf-subtle" style={{ fontSize: '0.75rem' }}>
                        {reportTypeLabel(r.report_type)}
                      </div>
                    </div>
                  ),
                },
                { key: 'status', header: 'Status', render: (r) => <Badge status={r.status} /> },
                {
                  key: 'summary',
                  header: 'Summary',
                  render: (r) => (
                    <span className="hf-subtle" style={{ fontSize: '0.8rem' }}>
                      {r.result_summary ? JSON.stringify(r.result_summary).slice(0, 60) : '—'}
                    </span>
                  ),
                },
                {
                  key: 'error',
                  header: 'Error',
                  render: (r) => r.error || '—',
                },
                {
                  key: 'started',
                  header: 'Started',
                  render: (r) => formatDateTime(r.started_at),
                },
                {
                  key: 'actions',
                  header: '',
                  render: (r) =>
                    r.status === 'failed' ? (
                      <Button
                        variant="outline"
                        size="sm"
                        leftIcon={<RefreshCw size={14} />}
                        onClick={(e) => {
                          e.stopPropagation()
                          void retryRun(r.id)
                        }}
                      >
                        Retry
                      </Button>
                    ) : (
                      <span className="hf-subtle" style={{ fontSize: '0.75rem' }}>
                        {r.exports.length} export{r.exports.length === 1 ? '' : 's'}
                      </span>
                    ),
                },
              ]}
              rows={runs.data?.results || []}
              rowKey={(r) => r.id}
              emptyTitle="No report runs yet"
              emptyDescription="Run a report to generate its history here."
            />
            {runs.data && (
              <Pagination page={page} pageSize={20} total={runs.data.count} onChange={setPage} />
            )}
          </Card>
        </>
      )}

      {tab === 'widgets' && (
        <div style={{ display: 'grid', gap: 16 }}>
          <Card title="Dashboard widgets" subtitle="Visible cards shown on the reporting dashboard.">
            <div style={{ display: 'grid', gap: 10 }}>
              {(widgets.data?.results || []).map((w, idx) => (
                <WidgetRow
                  key={w.id}
                  widget={w}
                  first={idx === 0}
                  last={idx === (widgets.data?.results.length || 0) - 1}
                  onMove={async (dir) => {
                    const rows = [...(widgets.data?.results || [])]
                    const i = rows.findIndex((x) => x.id === w.id)
                    const j = i + dir
                    if (i < 0 || j < 0 || j >= rows.length) return
                    const [item] = rows.splice(i, 1)
                    rows.splice(j, 0, item)
                    try {
                      await reportsApi.widgets.reorder({ ordered_ids: rows.map((x) => x.id) })
                      toast('Widget order saved', 'success')
                      widgets.reload()
                    } catch (err) {
                      toast(err instanceof ApiError ? err.message : 'Reorder failed', 'error')
                    }
                  }}
                  onToggle={async () => {
                    try {
                      await reportsApi.widgets.update(w.id, { is_visible: !w.is_visible })
                      widgets.reload()
                    } catch (err) {
                      toast(err instanceof ApiError ? err.message : 'Update failed', 'error')
                    }
                  }}
                  onEdit={() => {
                    setEditing(w)
                    setBuilderOpen(true)
                  }}
                  onDelete={async () => {
                    try {
                      await reportsApi.widgets.remove(w.id)
                      toast('Widget removed', 'success')
                      widgets.reload()
                    } catch (err) {
                      toast(err instanceof ApiError ? err.message : 'Delete failed', 'error')
                    }
                  }}
                />
              ))}
              {!widgets.data?.results?.length && (
                <EmptyState
                  title="No widgets yet"
                  description="Add a widget to surface key metrics on the dashboard."
                  actionLabel="Add widget"
                  onAction={() => {
                    setEditing(null)
                    setBuilderOpen(true)
                  }}
                />
              )}
            </div>
          </Card>
          <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
            <Button
              variant="outline"
              leftIcon={<Plus size={16} />}
              onClick={() => {
                setEditing(null)
                setBuilderOpen(true)
              }}
            >
              Add widget
            </Button>
          </div>
        </div>
      )}

      <ReportFormModal
        open={builderOpen}
        onClose={() => setBuilderOpen(false)}
        onSaved={() => {
          definitions.reload()
          setBuilderOpen(false)
        }}
      />
    </div>
  )

  function retryRun(id: string) {
    reportsApi.runs
      .retry(id)
      .then(() => toast('Run re-queued', 'success'))
      .then(() => runs.reload())
      .catch((err: unknown) =>
        toast(err instanceof ApiError ? err.message : 'Retry failed', 'error'),
      )
  }
}

function FilterBarReports({
  search,
  onSearchChange,
  type,
  onTypeChange,
  onClear,
  runFilter,
  runStatus,
  onRunStatusChange,
}: {
  search: string
  onSearchChange: (v: string) => void
  type: string
  onTypeChange: (v: string) => void
  onClear: () => void
  runFilter?: boolean
  runStatus?: string
  onRunStatusChange?: (v: string) => void
}) {
  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, alignItems: 'flex-end' }}>
      <div style={{ flex: '1 1 220px', minWidth: 200 }}>
        <Input
          value={search}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder="Search reports…"
        />
      </div>
      {runFilter ? (
        <div style={{ minWidth: 150, flex: '0 1 160px' }}>
          <Select
            label="Status"
            value={runStatus || ''}
            onChange={(e) => onRunStatusChange?.(e.target.value)}
            options={[{ value: '', label: 'All' }, ...RUN_STATUS_OPTIONS]}
          />
        </div>
      ) : (
        <div style={{ minWidth: 150, flex: '0 1 160px' }}>
          <Select
            label="Type"
            value={type}
            onChange={(e) => onTypeChange(e.target.value)}
            options={[{ value: '', label: 'All' }, ...REPORT_TYPE_OPTIONS]}
          />
        </div>
      )}
      <div style={{ display: 'flex', gap: 8, marginLeft: 'auto' }}>
        <Button variant="ghost" size="sm" onClick={onClear}>
          Clear
        </Button>
      </div>
    </div>
  )
}

function WidgetRow({
  widget,
  first,
  last,
  onMove,
  onToggle,
  onEdit,
  onDelete,
}: {
  widget: DashboardWidget
  first: boolean
  last: boolean
  onMove: (dir: -1 | 1) => void
  onToggle: () => void
  onEdit: () => void
  onDelete: () => void
}) {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 12,
        padding: '0.75rem 1rem',
        border: '1px solid var(--hf-border)',
        borderRadius: 10,
      }}
    >
      <span
        style={{
          width: 34,
          height: 34,
          borderRadius: 10,
          display: 'grid',
          placeItems: 'center',
          background: 'var(--hf-primary-soft)',
          color: 'var(--hf-teal-700)',
          flexShrink: 0,
        }}
      >
        <LayoutDashboard size={16} />
      </span>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontWeight: 600 }}>{widget.title}</div>
        <div className="hf-subtle" style={{ fontSize: '0.75rem' }}>
          {widgetTypeLabel(widget.widget_type)} · Position {widget.position}
        </div>
      </div>
      <Badge tone={widget.is_visible ? 'success' : 'neutral'}>
        {widget.is_visible ? 'Visible' : 'Hidden'}
      </Badge>
      <div style={{ display: 'flex', gap: 4 }}>
        <Button variant="ghost" size="sm" disabled={first} onClick={() => onMove(-1)}>
          <ArrowUp size={14} />
        </Button>
        <Button variant="ghost" size="sm" disabled={last} onClick={() => onMove(1)}>
          <ArrowDown size={14} />
        </Button>
        <Button variant="ghost" size="sm" onClick={onToggle}>
          <Eye size={14} />
        </Button>
        <Button variant="ghost" size="sm" onClick={onEdit}>
          <Pencil size={14} />
        </Button>
        <Button variant="ghost" size="sm" onClick={onDelete}>
          <Trash2 size={14} />
        </Button>
      </div>
    </div>
  )
}

export function ReportDetailPage() {
  const { id = '' } = useParams()
  const navigate = useNavigate()
  const { toast } = useToast()
  const [tab, setTab] = useState('overview')
  const [acting, setActing] = useState(false)
  const [confirming, setConfirming] = useState(false)
  const [paramsText, setParamsText] = useState('{}')
  const [preview, setPreview] = useState<Record<string, unknown> | null>(null)
  const [previewing, setPreviewing] = useState(false)

  const definition = useApi(() => reportsApi.definitions.get(id), [id], { enabled: Boolean(id) })
  const runs = useApi(
    () => reportsApi.runs.list({ definition: id, page_size: 20 }),
    [id, tab],
    { enabled: Boolean(id) && tab === 'runs' },
  )

  async function runAction(action: () => Promise<unknown>, ok: string) {
    setActing(true)
    try {
      await action()
      toast(ok, 'success')
      definition.reload()
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Action failed', 'error')
    } finally {
      setActing(false)
    }
  }

  async function runPreview() {
    let params: Record<string, unknown>
    try {
      params = paramsText.trim() ? JSON.parse(paramsText) : {}
    } catch {
      toast('Params must be valid JSON', 'error')
      return
    }
    setPreviewing(true)
    try {
      const res = await reportsApi.definitions.preview(id, { params })
      setPreview(res.preview as Record<string, unknown>)
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Preview failed', 'error')
    } finally {
      setPreviewing(false)
    }
  }

  if (definition.loading) {
    return (
      <div style={{ padding: 64, display: 'grid', placeItems: 'center' }}>
        <Spinner label="Loading report…" />
      </div>
    )
  }
  if (definition.error || !definition.data) {
    return (
      <EmptyState
        title="Report not found"
        description={definition.error || 'This report may have been deleted.'}
        actionLabel="Back to reports"
        onAction={() => navigate('/app/reports')}
      />
    )
  }

  const d = definition.data

  return (
    <div className="hf-page">
      <PageHeader
        title={d.name}
        subtitle={`${reportTypeLabel(d.report_type)} · ${d.description || 'No description'}`}
        actions={
          <>
            <Badge tone={d.schedule_enabled ? 'success' : 'neutral'}>
              {d.schedule_enabled ? 'Scheduled' : 'Manual'}
            </Badge>
            <Badge tone={d.is_public ? 'info' : 'neutral'}>
              {d.is_public ? 'Public' : 'Private'}
            </Badge>
            <Button variant="outline" onClick={() => navigate(`/app/reports/${id}/edit`)}>
              Edit
            </Button>
            <Button
              variant="outline"
              loading={acting}
              leftIcon={<RefreshCw size={14} />}
              onClick={() =>
                runAction(() => reportsApi.definitions.toggleSchedule(id, { enabled: !d.schedule_enabled }), d.schedule_enabled ? 'Schedule disabled' : 'Schedule enabled')
              }
            >
              {d.schedule_enabled ? 'Disable schedule' : 'Enable schedule'}
            </Button>
            <Button
              loading={acting}
              leftIcon={<Play size={14} />}
              onClick={() => runAction(() => reportsApi.definitions.runNow(id), 'Report queued')}
            >
              Run now
            </Button>
            <Button variant="danger" onClick={() => setConfirming(true)}>
              Delete
            </Button>
          </>
        }
      />

      <Tabs
        value={tab}
        onChange={setTab}
        items={[
          { id: 'overview', label: 'Overview' },
          { id: 'runs', label: 'Run history', count: runs.data?.count },
          { id: 'preview', label: 'Preview' },
        ]}
      />

      {tab === 'overview' && (
        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 16 }}>
          <Card title="Details">
            <dl style={{ display: 'grid', gap: 10, margin: 0, fontSize: '0.88rem' }}>
              <Row label="Report type" value={reportTypeLabel(d.report_type)} />
              <Row label="Cron schedule" value={d.schedule_cron || '—'} />
              <Row label="Last run" value={formatDateTime(d.last_run_at)} />
              <Row label="Created" value={formatDate(d.created_at)} />
              <Row label="Updated" value={formatDate(d.updated_at)} />
            </dl>
          </Card>
          <Card title="Params">
            {d.params && Object.keys(d.params).length ? (
              <pre
                className="hf-muted"
                style={{ fontSize: '0.78rem', whiteSpace: 'pre-wrap', margin: 0 }}
              >
                {JSON.stringify(d.params, null, 2)}
              </pre>
            ) : (
              <span className="hf-muted">No params configured.</span>
            )}
          </Card>
        </div>
      )}

      {tab === 'runs' && (
        <Card padding={0}>
          <DataTable
            loading={runs.loading}
            columns={[
              { key: 'status', header: 'Status', render: (r) => <Badge status={r.status} /> },
              {
                key: 'summary',
                header: 'Summary',
                render: (r) => (
                  <span className="hf-subtle" style={{ fontSize: '0.8rem' }}>
                    {r.result_summary ? JSON.stringify(r.result_summary).slice(0, 80) : '—'}
                  </span>
                ),
              },
              { key: 'error', header: 'Error', render: (r) => r.error || '—' },
              {
                key: 'started',
                header: 'Started',
                render: (r) => formatDateTime(r.started_at),
              },
              {
                key: 'finished',
                header: 'Finished',
                render: (r) => formatDateTime(r.finished_at),
              },
              {
                key: 'actions',
                header: '',
                render: (r) =>
                  r.status === 'failed' ? (
                    <Button
                      variant="outline"
                      size="sm"
                      leftIcon={<RefreshCw size={14} />}
                      onClick={(e) => {
                        e.stopPropagation()
                        reportsApi.runs
                          .retry(r.id)
                          .then(() => toast('Run re-queued', 'success'))
                          .then(() => runs.reload())
                          .catch((err: unknown) =>
                            toast(err instanceof ApiError ? err.message : 'Retry failed', 'error'),
                          )
                      }}
                    >
                      Retry
                    </Button>
                  ) : (
                    <span className="hf-subtle" style={{ fontSize: '0.75rem' }}>
                      {r.exports.length} export{r.exports.length === 1 ? '' : 's'}
                    </span>
                  ),
              },
            ]}
            rows={runs.data?.results || []}
            rowKey={(r) => r.id}
            emptyTitle="No runs yet"
            emptyDescription="Run this report to generate run history."
          />
        </Card>
      )}

      {tab === 'preview' && (
        <Card title="Dataset preview" subtitle="Compute the current dataset without persisting a run.">
          <div style={{ display: 'grid', gap: 12 }}>
            <Textarea
              label="Params (JSON)"
              value={paramsText}
              onChange={(e) => setParamsText(e.target.value)}
              placeholder='{"from": "2026-06-01", "to": "2026-08-31"}'
            />
            <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
              <Button loading={previewing} leftIcon={<Eye size={14} />} onClick={() => void runPreview()}>
                Preview dataset
              </Button>
            </div>
            {preview && (
              <pre
                className="hf-muted"
                style={{
                  fontSize: '0.78rem',
                  whiteSpace: 'pre-wrap',
                  background: 'var(--hf-bg-muted)',
                  padding: 16,
                  borderRadius: 10,
                  maxHeight: 480,
                  overflow: 'auto',
                }}
              >
                {JSON.stringify(preview, null, 2)}
              </pre>
            )}
          </div>
        </Card>
      )}

      <ConfirmDialog
        open={confirming}
        title="Delete report"
        message={`Delete "${d.name}"? This will also remove its run history.`}
        confirmLabel="Delete"
        danger
        onCancel={() => setConfirming(false)}
        onConfirm={() => {
          reportsApi.definitions
            .remove(id)
            .then(() => {
              toast('Report deleted', 'success')
              navigate('/app/reports')
            })
            .catch((err: unknown) =>
              toast(err instanceof ApiError ? err.message : 'Delete failed', 'error'),
            )
            .finally(() => setConfirming(false))
        }}
      />
    </div>
  )
}

export function ReportFormPage() {
  const { id } = useParams()
  const isEdit = Boolean(id)
  const navigate = useNavigate()
  const { toast } = useToast()
  const [saving, setSaving] = useState(false)
  const [loading, setLoading] = useState(isEdit)
  const [form, setForm] = useState({
    name: '',
    description: '',
    report_type: 'Hires',
    schedule_cron: '',
    schedule_enabled: false,
    is_public: false,
    params: '{}',
  })

  function set<K extends keyof typeof form>(key: K, value: (typeof form)[K]) {
    setForm((f) => ({ ...f, [key]: value }))
  }

  useEffect(() => {
    if (!id) return
    setLoading(true)
    reportsApi.definitions
      .get(id)
      .then((d) => {
        setForm({
          name: d.name,
          description: d.description || '',
          report_type: reportTypeLabel(d.report_type),
          schedule_cron: d.schedule_cron || '',
          schedule_enabled: d.schedule_enabled,
          is_public: d.is_public,
          params: JSON.stringify(d.params || {}, null, 2),
        })
      })
      .catch((err: unknown) =>
        toast(err instanceof ApiError ? err.message : 'Failed to load report', 'error'),
      )
      .finally(() => setLoading(false))
  }, [id, toast])

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    let params: Record<string, unknown>
    try {
      params = form.params.trim() ? JSON.parse(form.params) : {}
    } catch {
      toast('Params must be valid JSON', 'error')
      return
    }
    setSaving(true)
    const payload = {
      name: form.name,
      description: form.description,
      report_type: REPORT_TYPE_VALUES[form.report_type] || form.report_type,
      schedule_cron: form.schedule_cron || null,
      schedule_enabled: form.schedule_enabled,
      is_public: form.is_public,
      params,
    }
    try {
      const saved = isEdit
        ? await reportsApi.definitions.update(id!, payload)
        : await reportsApi.definitions.create(payload)
      toast(isEdit ? 'Report updated' : 'Report created', 'success')
      navigate(`/app/reports/${saved.id}`)
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
        title={isEdit ? 'Edit report' : 'Create report'}
        subtitle="Describe the metric, parameters, and schedule for this report."
      />
      <form onSubmit={onSubmit}>
        <Card>
          <div style={{ display: 'grid', gap: 14 }}>
            <Input label="Name" required value={form.name} onChange={(e) => set('name', e.target.value)} />
            <Textarea
              label="Description"
              value={form.description}
              onChange={(e) => set('description', e.target.value)}
            />
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              <Select
                label="Report type"
                value={form.report_type}
                onChange={(e) => set('report_type', e.target.value)}
                options={REPORT_TYPE_OPTIONS}
              />
              <Input
                label="Cron schedule (e.g. 0 9 * * 1)"
                value={form.schedule_cron}
                onChange={(e) => set('schedule_cron', e.target.value)}
                placeholder="Optional"
              />
            </div>
            <Textarea
              label="Params (JSON)"
              value={form.params}
              onChange={(e) => set('params', e.target.value)}
            />
            <div style={{ display: 'flex', gap: 20 }}>
              <label style={{ display: 'flex', gap: 8, alignItems: 'center', fontSize: '0.88rem' }}>
                <input
                  type="checkbox"
                  checked={form.schedule_enabled}
                  onChange={(e) => set('schedule_enabled', e.target.checked)}
                />
                Enable schedule
              </label>
              <label style={{ display: 'flex', gap: 8, alignItems: 'center', fontSize: '0.88rem' }}>
                <input
                  type="checkbox"
                  checked={form.is_public}
                  onChange={(e) => set('is_public', e.target.checked)}
                />
                Public report
              </label>
            </div>
            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
              <Button type="button" variant="outline" onClick={() => navigate(-1)}>
                Cancel
              </Button>
              <Button type="submit" loading={saving}>
                {isEdit ? 'Save changes' : 'Create report'}
              </Button>
            </div>
          </div>
        </Card>
      </form>
    </div>
  )
}

function ReportFormModal({
  open,
  onClose,
  onSaved,
}: {
  open: boolean
  onClose: () => void
  onSaved: () => void
}) {
  const { toast } = useToast()
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [reportType, setReportType] = useState('Hires')
  const [scheduleCron, setScheduleCron] = useState('')
  const [scheduleEnabled, setScheduleEnabled] = useState(false)
  const [saving, setSaving] = useState(false)

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setSaving(true)
    try {
      await reportsApi.definitions.create({
        name,
        description,
        report_type: REPORT_TYPE_VALUES[reportType] as ReportDefinition['report_type'],
        schedule_cron: scheduleCron || null,
        schedule_enabled: scheduleEnabled,
        is_public: false,
        params: {},
      })
      toast('Report created', 'success')
      onSaved()
      setName('')
      setDescription('')
      setScheduleCron('')
      setScheduleEnabled(false)
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Create failed', 'error')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal open={open} onClose={onClose} title="New report definition">
      <form onSubmit={onSubmit} style={{ display: 'grid', gap: 12 }}>
        <Input label="Name" required value={name} onChange={(e) => setName(e.target.value)} />
        <Textarea
          label="Description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
        <Select
          label="Report type"
          value={reportType}
          onChange={(e) => setReportType(e.target.value)}
          options={REPORT_TYPE_OPTIONS}
        />
        <Input
          label="Cron schedule (optional)"
          value={scheduleCron}
          onChange={(e) => setScheduleCron(e.target.value)}
          placeholder="e.g. 0 9 * * 1"
        />
        <label style={{ display: 'flex', gap: 8, alignItems: 'center', fontSize: '0.88rem' }}>
          <input
            type="checkbox"
            checked={scheduleEnabled}
            onChange={(e) => setScheduleEnabled(e.target.checked)}
          />
          Enable schedule
        </label>
        <Button type="submit" loading={saving}>
          Create report
        </Button>
      </form>
    </Modal>
  )
}

export function DashboardWidgetsPage() {
  const { toast } = useToast()
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<DashboardWidget | null>(null)
  const widgets = useApi(() => reportsApi.widgets.list({ page_size: 100 }), [], { enabled: true })

  return (
    <div className="hf-page">
      <PageHeader
        title="Dashboard widgets"
        subtitle="Curate the metric cards shown on your reporting dashboard."
        actions={
          <Button
            leftIcon={<Plus size={16} />}
            onClick={() => {
              setEditing(null)
              setModalOpen(true)
            }}
          >
            Add widget
          </Button>
        }
      />
      <Card>
        {(widgets.data?.results || []).map((w, idx) => (
          <WidgetRow
            key={w.id}
            widget={w}
            first={idx === 0}
            last={idx === (widgets.data?.results.length || 0) - 1}
            onMove={async (dir) => {
              const rows = [...(widgets.data?.results || [])]
              const i = rows.findIndex((x) => x.id === w.id)
              const j = i + dir
              if (i < 0 || j < 0 || j >= rows.length) return
              const [item] = rows.splice(i, 1)
              rows.splice(j, 0, item)
              try {
                await reportsApi.widgets.reorder({ ordered_ids: rows.map((x) => x.id) })
                widgets.reload()
              } catch (err) {
                toast(err instanceof ApiError ? err.message : 'Reorder failed', 'error')
              }
            }}
            onToggle={async () => {
              try {
                await reportsApi.widgets.update(w.id, { is_visible: !w.is_visible })
                widgets.reload()
              } catch (err) {
                toast(err instanceof ApiError ? err.message : 'Update failed', 'error')
              }
            }}
            onEdit={() => {
              setEditing(w)
              setModalOpen(true)
            }}
            onDelete={async () => {
              try {
                await reportsApi.widgets.remove(w.id)
                widgets.reload()
              } catch (err) {
                toast(err instanceof ApiError ? err.message : 'Delete failed', 'error')
              }
            }}
          />
        ))}
        {!widgets.data?.results?.length && (
          <EmptyState
            title="No widgets yet"
            description="Add a widget to surface key metrics on the dashboard."
            actionLabel="Add widget"
            onAction={() => {
              setEditing(null)
              setModalOpen(true)
            }}
          />
        )}
      </Card>
      <WidgetFormModal
        open={modalOpen}
        editing={editing}
        onClose={() => setModalOpen(false)}
        onSaved={() => {
          widgets.reload()
          setModalOpen(false)
        }}
      />
    </div>
  )
}

function WidgetFormModal({
  open,
  editing,
  onClose,
  onSaved,
}: {
  open: boolean
  editing: DashboardWidget | null
  onClose: () => void
  onSaved: () => void
}) {
  const { toast } = useToast()
  const [title, setTitle] = useState('')
  const [widgetType, setWidgetType] = useState('Summary')
  const [position, setPosition] = useState(0)
  const [isVisible, setIsVisible] = useState(true)
  const [configText, setConfigText] = useState('{}')
  const [saving, setSaving] = useState(false)

  // Re-seed the form whenever the modal opens for a different widget.
  const [seed, setSeed] = useState('')
  if (open && seed !== (editing?.id || 'new')) {
    setSeed(editing?.id || 'new')
    setTitle(editing?.title || '')
    setWidgetType(widgetTypeLabel(editing?.widget_type) || 'Summary')
    setPosition(editing?.position ?? 0)
    setIsVisible(editing?.is_visible ?? true)
    setConfigText(JSON.stringify(editing?.config || {}, null, 2))
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    let config: Record<string, unknown>
    try {
      config = configText.trim() ? JSON.parse(configText) : {}
    } catch {
      toast('Config must be valid JSON', 'error')
      return
    }
    setSaving(true)
    const payload = {
      title,
      widget_type: WIDGET_TYPE_VALUES[widgetType] || widgetType,
      config,
      position: Number(position) || 0,
      is_visible: isVisible,
    }
    try {
      if (editing) {
        await reportsApi.widgets.update(editing.id, payload)
        toast('Widget updated', 'success')
      } else {
        await reportsApi.widgets.create(payload)
        toast('Widget created', 'success')
      }
      onSaved()
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Save failed', 'error')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal open={open} onClose={onClose} title={editing ? 'Edit widget' : 'Add widget'}>
      <form onSubmit={onSubmit} style={{ display: 'grid', gap: 12 }}>
        <Input label="Title" required value={title} onChange={(e) => setTitle(e.target.value)} />
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          <Select
            label="Widget type"
            value={widgetType}
            onChange={(e) => setWidgetType(e.target.value)}
            options={WIDGET_TYPE_OPTIONS}
          />
          <Input
            label="Position"
            type="number"
            value={position}
            onChange={(e) => setPosition(Number(e.target.value))}
          />
        </div>
        <Textarea
          label="Config (JSON)"
          value={configText}
          onChange={(e) => setConfigText(e.target.value)}
        />
        <label style={{ display: 'flex', gap: 8, alignItems: 'center', fontSize: '0.88rem' }}>
          <input
            type="checkbox"
            checked={isVisible}
            onChange={(e) => setIsVisible(e.target.checked)}
          />
          Visible on dashboard
        </label>
        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
          <Button type="button" variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={saving}>
            {editing ? 'Save changes' : 'Add widget'}
          </Button>
        </div>
      </form>
    </Modal>
  )
}
