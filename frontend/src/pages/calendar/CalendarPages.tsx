/**
 * CalendarPages.tsx — Interview scheduling frontend.
 *
 * Exported components & suggested routes (wired by main agent in App.tsx):
 *   CalendarPage              → /app/calendar
 *   AvailabilityRuleFormPage  → /app/calendar/availability/new, /app/calendar/availability/:id/edit
 *   SchedulingLinksPage       → /app/calendar/links
 *   SchedulingLinkFormPage    → /app/calendar/links/new, /app/calendar/links/:id/edit
 *   SchedulingLinkDetailPage  → /app/calendar/links/:id
 *   BookingRequestsPage       → /app/calendar/bookings
 */
import { useEffect, useState, type FormEvent } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { Copy, Pencil, Plus, RefreshCw, Trash2 } from 'lucide-react'
import {
  availabilityRulesApi,
  bookingRequestsApi,
  calendarAccountsApi,
  interviewSlotsApi,
  schedulingLinksApi,
} from '../../api/calendar'
import type { AvailabilityRule, BookingRequest, CalendarAccount, InterviewSlot, SchedulingLink } from '../../api/calendar'
import { jobsApi } from '../../api/jobs'
import { hiringTeamMembersApi } from '../../api/organizations'
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
  useToast,
} from '../../components/ui'
import { formatDate, formatDateTime, titleCase } from '../../utils/format'
import { ApiError } from '../../api/http'

const DAY_NAMES = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

function todayIso() {
  return new Date().toISOString().slice(0, 10)
}

function daysLabel(days: number[]) {
  if (!days?.length) return '—'
  return days.map((d) => DAY_NAMES[d] ?? d).join(', ')
}

function useMembers() {
  return useApi(() => hiringTeamMembersApi.list({ page_size: 100 }), [], { enabled: true })
}

export function CalendarPage() {
  const [tab, setTab] = useState('availability')

  return (
    <div className="hf-page">
      <PageHeader
        title="Interview scheduling"
        subtitle="Availability rules, generated interview slots, and connected calendars."
      />
      <Tabs
        value={tab}
        onChange={setTab}
        items={[
          { id: 'availability', label: 'Availability' },
          { id: 'slots', label: 'Slots' },
          { id: 'accounts', label: 'Calendar accounts' },
        ]}
      />
      {tab === 'availability' && <AvailabilityTab />}
      {tab === 'slots' && <SlotsTab />}
      {tab === 'accounts' && <AccountsTab />}
    </div>
  )
}

function AvailabilityTab() {
  const navigate = useNavigate()
  const { toast } = useToast()
  const [page, setPage] = useState(1)
  const [deleting, setDeleting] = useState<AvailabilityRule | null>(null)
  const [removing, setRemoving] = useState(false)
  const rules = useApi(() => availabilityRulesApi.list({ page, page_size: 20 }), [page, deleting], {
    enabled: true,
  })

  async function toggleActive(rule: AvailabilityRule) {
    try {
      await availabilityRulesApi.update(rule.id, { is_active: !rule.is_active })
      toast(rule.is_active ? 'Rule disabled' : 'Rule enabled', 'success')
      rules.reload()
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Action failed', 'error')
    }
  }

  async function onDelete() {
    if (!deleting) return
    setRemoving(true)
    try {
      await availabilityRulesApi.remove(deleting.id)
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
    <>
      <Card
        padding={0}
        title="Availability rules"
        actions={
          <Button size="sm" leftIcon={<Plus size={14} />} onClick={() => navigate('/app/calendar/availability/new')}>
            New rule
          </Button>
        }
      >
        <DataTable
          loading={rules.loading}
          columns={[
            {
              key: 'title',
              header: 'Rule',
              render: (r: AvailabilityRule) => (
                <div>
                  <div style={{ fontWeight: 600 }}>{r.title || 'Untitled rule'}</div>
                  <div className="hf-subtle" style={{ fontSize: '0.75rem' }}>{daysLabel(r.days_of_week)}</div>
                </div>
              ),
            },
            {
              key: 'window',
              header: 'Window',
              render: (r: AvailabilityRule) => `${r.start_time} – ${r.end_time} (${r.timezone})`,
            },
            { key: 'buffer', header: 'Buffer', render: (r: AvailabilityRule) => `${r.buffer_minutes} min` },
            {
              key: 'active',
              header: 'Active',
              render: (r: AvailabilityRule) => (
                <Badge tone={r.is_active ? 'success' : 'neutral'}>{r.is_active ? 'Yes' : 'No'}</Badge>
              ),
            },
            {
              key: 'actions',
              header: '',
              render: (r: AvailabilityRule) => (
                <div style={{ display: 'flex', gap: 6, justifyContent: 'flex-end' }}>
                  <Button size="sm" variant="outline" onClick={() => void toggleActive(r)}>
                    {r.is_active ? 'Disable' : 'Enable'}
                  </Button>
                  <Button size="sm" variant="ghost" onClick={() => navigate(`/app/calendar/availability/${r.id}/edit`)} aria-label="Edit">
                    <Pencil size={14} />
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
          emptyTitle="No availability rules"
          emptyDescription="Define recurring windows so interview slots can be generated."
        />
        {rules.data && <Pagination page={page} pageSize={20} total={rules.data.count} onChange={setPage} />}
      </Card>
      <ConfirmDialog
        open={Boolean(deleting)}
        title="Delete availability rule"
        message={`Delete "${deleting?.title || 'this rule'}"?`}
        confirmLabel="Delete"
        danger
        loading={removing}
        onConfirm={() => void onDelete()}
        onCancel={() => setDeleting(null)}
      />
    </>
  )
}

function SlotsTab() {
  const { toast } = useToast()
  const [page, setPage] = useState(1)
  const [status, setStatus] = useState('')
  const [startDate, setStartDate] = useState(todayIso())
  const [endDate, setEndDate] = useState(() => {
    const d = new Date()
    d.setDate(d.getDate() + 7)
    return d.toISOString().slice(0, 10)
  })
  const [generateOpen, setGenerateOpen] = useState(false)
  const [holdSlot, setHoldSlot] = useState<InterviewSlot | null>(null)
  const [holdMinutes, setHoldMinutes] = useState(30)
  const [acting, setActing] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const members = useMembers()
  const slots = useApi(
    () =>
      interviewSlotsApi.list({
        page,
        page_size: 20,
        status: status || undefined,
        start_date: startDate || undefined,
        end_date: endDate || undefined,
      }),
    [page, status, startDate, endDate],
    { enabled: true },
  )
  const [genForm, setGenForm] = useState({
    user: '',
    start_date: todayIso(),
    end_date: '',
    duration_minutes: 60,
    rule_ids: '',
  })

  async function runAction(slotId: string, action: () => Promise<unknown>, ok: string) {
    setActing(slotId)
    try {
      await action()
      toast(ok, 'success')
      slots.reload()
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Action failed', 'error')
    } finally {
      setActing(null)
    }
  }

  async function onGenerate(e: FormEvent) {
    e.preventDefault()
    setSaving(true)
    try {
      await interviewSlotsApi.bulkGenerate({
        user: genForm.user,
        start_date: genForm.start_date,
        end_date: genForm.end_date,
        duration_minutes: Number(genForm.duration_minutes) || 60,
        rule_ids: genForm.rule_ids
          .split(',')
          .map((s) => s.trim())
          .filter(Boolean),
      })
      toast('Slots generated', 'success')
      setGenerateOpen(false)
      slots.reload()
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Generation failed', 'error')
    } finally {
      setSaving(false)
    }
  }

  async function onHold(e: FormEvent) {
    e.preventDefault()
    if (!holdSlot) return
    setSaving(true)
    try {
      await interviewSlotsApi.hold(holdSlot.id, { hold_minutes: holdMinutes })
      toast('Slot held', 'success')
      setHoldSlot(null)
      slots.reload()
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Hold failed', 'error')
    } finally {
      setSaving(false)
    }
  }

  return (
    <>
      <Card
        padding={0}
        title="Interview slots"
        actions={
          <Button size="sm" leftIcon={<Plus size={14} />} onClick={() => setGenerateOpen(true)}>
            Bulk generate
          </Button>
        }
      >
        <div style={{ padding: '0.75rem 1.25rem', borderBottom: '1px solid var(--hf-border)', display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'flex-end' }}>
          <div style={{ minWidth: 160 }}>
            <Input label="From" type="date" value={startDate} onChange={(e) => { setPage(1); setStartDate(e.target.value) }} />
          </div>
          <div style={{ minWidth: 160 }}>
            <Input label="To" type="date" value={endDate} onChange={(e) => { setPage(1); setEndDate(e.target.value) }} />
          </div>
          <div style={{ minWidth: 160 }}>
            <Select
              label="Status"
              value={status}
              onChange={(e) => {
                setPage(1)
                setStatus(e.target.value)
              }}
              options={[
                { value: '', label: 'All' },
                { value: 'available', label: 'Available' },
                { value: 'booked', label: 'Booked' },
                { value: 'held', label: 'Held' },
                { value: 'expired', label: 'Expired' },
              ]}
            />
          </div>
          <Button variant="ghost" size="sm" onClick={() => { setStartDate(todayIso()); setEndDate('') }}>
            Reset range
          </Button>
        </div>
        <DataTable
          loading={slots.loading}
          columns={[
            {
              key: 'when',
              header: 'When',
              render: (s: InterviewSlot) => (
                <div>
                  <div>{formatDateTime(s.start_at)}</div>
                  <div className="hf-subtle" style={{ fontSize: '0.75rem' }}>→ {formatDateTime(s.end_at)}</div>
                </div>
              ),
            },
            { key: 'status', header: 'Status', render: (s: InterviewSlot) => <Badge status={s.status} /> },
            { key: 'held_until', header: 'Held until', render: (s: InterviewSlot) => formatDateTime(s.held_until) },
            {
              key: 'actions',
              header: '',
              render: (s: InterviewSlot) => (
                <div style={{ display: 'flex', gap: 6, justifyContent: 'flex-end' }}>
                  {s.status === 'available' && (
                    <Button size="sm" variant="outline" loading={acting === s.id} onClick={() => { setHoldSlot(s); setHoldMinutes(30) }}>
                      Hold
                    </Button>
                  )}
                  {s.status === 'held' && (
                    <Button size="sm" variant="outline" loading={acting === s.id} onClick={() => void runAction(s.id, () => interviewSlotsApi.release(s.id), 'Slot released')}>
                      Release
                    </Button>
                  )}
                  {['available', 'held'].includes(s.status) && (
                    <Button size="sm" variant="ghost" loading={acting === s.id} onClick={() => void runAction(s.id, () => interviewSlotsApi.cancelSlot(s.id), 'Slot cancelled')}>
                      Cancel
                    </Button>
                  )}
                </div>
              ),
            },
          ]}
          rows={slots.data?.results || []}
          rowKey={(s) => s.id}
          emptyTitle="No slots in range"
          emptyDescription="Generate slots from availability rules to fill this period."
        />
        {slots.data && <Pagination page={page} pageSize={20} total={slots.data.count} onChange={setPage} />}
      </Card>

      <Modal open={generateOpen} onClose={() => setGenerateOpen(false)} title="Bulk generate slots">
        <form onSubmit={onGenerate} style={{ display: 'grid', gap: 12 }}>
          <Select
            label="User"
            required
            value={genForm.user}
            onChange={(e) => setGenForm((f) => ({ ...f, user: e.target.value }))}
            placeholder="Select user"
            options={(members.data?.results || []).map((m) => ({ value: m.user, label: m.user_name }))}
          />
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <Input label="Start date" type="date" required value={genForm.start_date} onChange={(e) => setGenForm((f) => ({ ...f, start_date: e.target.value }))} />
            <Input label="End date" type="date" required value={genForm.end_date} onChange={(e) => setGenForm((f) => ({ ...f, end_date: e.target.value }))} />
          </div>
          <Input label="Duration (minutes)" type="number" min={15} max={480} value={genForm.duration_minutes} onChange={(e) => setGenForm((f) => ({ ...f, duration_minutes: Number(e.target.value) || 60 }))} />
          <Input label="Rule IDs (comma-separated, optional)" value={genForm.rule_ids} onChange={(e) => setGenForm((f) => ({ ...f, rule_ids: e.target.value }))} />
          <Button type="submit" loading={saving}>
            Generate slots
          </Button>
        </form>
      </Modal>

      <Modal open={Boolean(holdSlot)} onClose={() => setHoldSlot(null)} title="Hold slot" width={360}>
        <form onSubmit={onHold} style={{ display: 'grid', gap: 12 }}>
          <Input label="Hold for (minutes)" type="number" min={5} max={1440} value={holdMinutes} onChange={(e) => setHoldMinutes(Number(e.target.value) || 30)} />
          <Button type="submit" loading={saving}>
            Hold slot
          </Button>
        </form>
      </Modal>
    </>
  )
}

function AccountsTab() {
  const { toast } = useToast()
  const [page, setPage] = useState(1)
  const [open, setOpen] = useState(false)
  const [acting, setActing] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [form, setForm] = useState({ provider: 'google', email: '', is_primary: false, sync_enabled: true })
  const accounts = useApi(() => calendarAccountsApi.list({ page, page_size: 20 }), [page, open], {
    enabled: true,
  })

  async function runAction(accountId: string, action: () => Promise<unknown>, ok: string) {
    setActing(accountId)
    try {
      await action()
      toast(ok, 'success')
      accounts.reload()
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Action failed', 'error')
    } finally {
      setActing(null)
    }
  }

  async function onCreate(e: FormEvent) {
    e.preventDefault()
    if (!form.email.trim()) {
      toast('Email is required', 'error')
      return
    }
    setSaving(true)
    try {
      await calendarAccountsApi.create(form)
      toast('Calendar account added', 'success')
      setOpen(false)
      setForm({ provider: 'google', email: '', is_primary: false, sync_enabled: true })
      accounts.reload()
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Save failed', 'error')
    } finally {
      setSaving(false)
    }
  }

  return (
    <>
      <Card
        padding={0}
        title="Calendar accounts"
        actions={
          <Button size="sm" leftIcon={<Plus size={14} />} onClick={() => setOpen(true)}>
            Add account
          </Button>
        }
      >
        <DataTable
          loading={accounts.loading}
          columns={[
            {
              key: 'email',
              header: 'Account',
              render: (a: CalendarAccount) => (
                <div>
                  <div style={{ fontWeight: 600 }}>{a.email}</div>
                  <div className="hf-subtle" style={{ fontSize: '0.75rem' }}>{titleCase(a.provider)}</div>
                </div>
              ),
            },
            {
              key: 'primary',
              header: 'Primary',
              render: (a: CalendarAccount) => (a.is_primary ? <Badge tone="info">Primary</Badge> : '—'),
            },
            {
              key: 'sync',
              header: 'Sync',
              render: (a: CalendarAccount) => (
                <Badge tone={a.sync_enabled ? 'success' : 'neutral'}>{a.sync_enabled ? 'Enabled' : 'Disabled'}</Badge>
              ),
            },
            { key: 'last_synced', header: 'Last synced', render: (a: CalendarAccount) => formatDateTime(a.last_synced_at) },
            {
              key: 'actions',
              header: '',
              render: (a: CalendarAccount) => (
                <div style={{ display: 'flex', gap: 6, justifyContent: 'flex-end' }}>
                  <Button size="sm" variant="outline" loading={acting === a.id} onClick={() => void runAction(a.id, () => calendarAccountsApi.sync(a.id), 'Sync queued')}>
                    <RefreshCw size={13} /> Sync
                  </Button>
                  <Button size="sm" variant="ghost" loading={acting === a.id} onClick={() => void runAction(a.id, () => calendarAccountsApi.disconnect(a.id), 'Account disconnected')}>
                    Disconnect
                  </Button>
                </div>
              ),
            },
          ]}
          rows={accounts.data?.results || []}
          rowKey={(a) => a.id}
          emptyTitle="No calendar accounts"
          emptyDescription="Connect a Google or Outlook account to enable syncing."
        />
        {accounts.data && <Pagination page={page} pageSize={20} total={accounts.data.count} onChange={setPage} />}
      </Card>

      <Modal open={open} onClose={() => setOpen(false)} title="Add calendar account">
        <form onSubmit={onCreate} style={{ display: 'grid', gap: 12 }}>
          <Select
            label="Provider"
            value={form.provider}
            onChange={(e) => setForm((f) => ({ ...f, provider: e.target.value }))}
            options={[
              { value: 'google', label: 'Google' },
              { value: 'outlook', label: 'Outlook' },
            ]}
          />
          <Input label="Email" type="email" required value={form.email} onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))} />
          <label style={{ display: 'flex', gap: 8, alignItems: 'center', fontSize: '0.88rem' }}>
            <input type="checkbox" checked={form.is_primary} onChange={(e) => setForm((f) => ({ ...f, is_primary: e.target.checked }))} />
            Primary account
          </label>
          <label style={{ display: 'flex', gap: 8, alignItems: 'center', fontSize: '0.88rem' }}>
            <input type="checkbox" checked={form.sync_enabled} onChange={(e) => setForm((f) => ({ ...f, sync_enabled: e.target.checked }))} />
            Sync enabled
          </label>
          <Button type="submit" loading={saving}>
            Add account
          </Button>
        </form>
      </Modal>
    </>
  )
}

const emptyRule = {
  user: '',
  title: '',
  days_of_week: [] as number[],
  start_time: '09:00',
  end_time: '17:00',
  timezone: 'UTC',
  buffer_minutes: 0,
  is_active: true,
}

export function AvailabilityRuleFormPage() {
  const { id } = useParams()
  const isEdit = Boolean(id)
  const navigate = useNavigate()
  const { toast } = useToast()
  const members = useMembers()
  const [form, setForm] = useState(emptyRule)
  const [loading, setLoading] = useState(isEdit)
  const [saving, setSaving] = useState(false)
  const rule = useApi(() => availabilityRulesApi.get(id!), [id], { enabled: isEdit })

  useEffect(() => {
    if (!rule.data) return
    setForm({
      user: rule.data.user,
      title: rule.data.title || '',
      days_of_week: rule.data.days_of_week || [],
      start_time: rule.data.start_time.slice(0, 5),
      end_time: rule.data.end_time.slice(0, 5),
      timezone: rule.data.timezone,
      buffer_minutes: rule.data.buffer_minutes,
      is_active: rule.data.is_active,
    })
    setLoading(false)
  }, [rule.data])

  function toggleDay(day: number) {
    setForm((f) => ({
      ...f,
      days_of_week: f.days_of_week.includes(day) ? f.days_of_week.filter((d) => d !== day) : [...f.days_of_week, day].sort(),
    }))
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    if (!form.user) {
      toast('User is required', 'error')
      return
    }
    setSaving(true)
    const payload = {
      user: form.user,
      title: form.title,
      days_of_week: form.days_of_week,
      start_time: form.start_time,
      end_time: form.end_time,
      timezone: form.timezone,
      buffer_minutes: Number(form.buffer_minutes) || 0,
      is_active: form.is_active,
    }
    try {
      const saved = isEdit ? await availabilityRulesApi.update(id!, payload) : await availabilityRulesApi.create(payload)
      toast(isEdit ? 'Rule updated' : 'Rule created', 'success')
      navigate('/app/calendar')
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
      <EmptyState title="Rule not found" description={rule.error} actionLabel="Back" onAction={() => navigate('/app/calendar')} />
    )
  }

  return (
    <div className="hf-page">
      <PageHeader
        title={isEdit ? 'Edit availability rule' : 'New availability rule'}
        subtitle="Recurring windows used to generate interview slots."
      />
      <form onSubmit={onSubmit}>
        <Card>
          <div style={{ display: 'grid', gap: 14 }}>
            <Select
              label="User"
              required
              value={form.user}
              onChange={(e) => setForm((f) => ({ ...f, user: e.target.value }))}
              placeholder="Select user"
              options={(members.data?.results || []).map((m) => ({ value: m.user, label: m.user_name }))}
            />
            <Input label="Title" value={form.title} onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))} />
            <div>
              <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--hf-text-muted)' }}>Days of week</span>
              <div style={{ display: 'flex', gap: 10, marginTop: 8, flexWrap: 'wrap' }}>
                {DAY_NAMES.map((day, idx) => (
                  <label key={day} style={{ display: 'flex', gap: 5, alignItems: 'center', fontSize: '0.85rem' }}>
                    <input type="checkbox" checked={form.days_of_week.includes(idx)} onChange={() => toggleDay(idx)} />
                    {day}
                  </label>
                ))}
              </div>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12 }}>
              <Input label="Start time" type="time" required value={form.start_time} onChange={(e) => setForm((f) => ({ ...f, start_time: e.target.value }))} />
              <Input label="End time" type="time" required value={form.end_time} onChange={(e) => setForm((f) => ({ ...f, end_time: e.target.value }))} />
              <Input label="Buffer (minutes)" type="number" min={0} value={form.buffer_minutes} onChange={(e) => setForm((f) => ({ ...f, buffer_minutes: Number(e.target.value) || 0 }))} />
            </div>
            <Input label="Timezone" value={form.timezone} onChange={(e) => setForm((f) => ({ ...f, timezone: e.target.value }))} />
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

export function SchedulingLinksPage() {
  const navigate = useNavigate()
  const { toast } = useToast()
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [acting, setActing] = useState<string | null>(null)
  const links = useApi(
    () => schedulingLinksApi.list({ page, page_size: 20, search: search || undefined }),
    [page, search],
    { enabled: true },
  )

  async function onDuplicate(linkId: string) {
    setActing(linkId)
    try {
      await schedulingLinksApi.duplicate(linkId)
      toast('Link duplicated', 'success')
      links.reload()
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Duplicate failed', 'error')
    } finally {
      setActing(null)
    }
  }

  return (
    <div className="hf-page">
      <PageHeader
        title="Scheduling links"
        subtitle="Public booking links candidates can use to pick an interview time."
        actions={
          <Button leftIcon={<Plus size={16} />} onClick={() => navigate('/app/calendar/links/new')}>
            New link
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
          searchPlaceholder="Search links…"
          onClear={() => {
            setSearch('')
            setPage(1)
          }}
        />
      </Card>
      <Card padding={0}>
        <DataTable
          loading={links.loading}
          columns={[
            {
              key: 'name',
              header: 'Link',
              render: (l: SchedulingLink) => (
                <div>
                  <Link to={`/app/calendar/links/${l.id}`} style={{ fontWeight: 650, textDecoration: 'none' }}>
                    {l.name}
                  </Link>
                  <div className="hf-subtle" style={{ fontSize: '0.75rem' }}>/{l.slug}</div>
                </div>
              ),
            },
            { key: 'duration', header: 'Duration', render: (l: SchedulingLink) => `${l.duration_minutes} min` },
            { key: 'bookings', header: 'Bookings', render: (l: SchedulingLink) => l.booking_count },
            {
              key: 'active',
              header: 'Active',
              render: (l: SchedulingLink) => <Badge tone={l.is_active ? 'success' : 'neutral'}>{l.is_active ? 'Yes' : 'No'}</Badge>,
            },
            { key: 'created', header: 'Created', render: (l: SchedulingLink) => formatDate(l.created_at) },
            {
              key: 'actions',
              header: '',
              render: (l: SchedulingLink) => (
                <div style={{ display: 'flex', gap: 6, justifyContent: 'flex-end' }}>
                  <Button size="sm" variant="outline" loading={acting === l.id} onClick={() => void onDuplicate(l.id)}>
                    Duplicate
                  </Button>
                </div>
              ),
            },
          ]}
          rows={links.data?.results || []}
          rowKey={(l) => l.id}
          emptyTitle="No scheduling links"
          emptyDescription="Create a booking link to share with candidates."
          onRowClick={(l) => navigate(`/app/calendar/links/${l.id}`)}
        />
        {links.data && <Pagination page={page} pageSize={20} total={links.data.count} onChange={setPage} />}
      </Card>
    </div>
  )
}

const emptyLink = {
  name: '',
  owner: '',
  job: '',
  duration_minutes: 60,
  start_date: '',
  end_date: '',
  timezone: 'UTC',
  is_active: true,
}

export function SchedulingLinkFormPage() {
  const { id } = useParams()
  const isEdit = Boolean(id)
  const navigate = useNavigate()
  const { toast } = useToast()
  const members = useMembers()
  const jobs = useApi(() => jobsApi.list({ page_size: 100, status: 'published' }), [], { enabled: true })
  const [form, setForm] = useState(emptyLink)
  const [loading, setLoading] = useState(isEdit)
  const [saving, setSaving] = useState(false)
  const link = useApi(() => schedulingLinksApi.get(id!), [id], { enabled: isEdit })

  useEffect(() => {
    if (!link.data) return
    setForm({
      name: link.data.name,
      owner: link.data.owner,
      job: link.data.job || '',
      duration_minutes: link.data.duration_minutes,
      start_date: link.data.start_date || '',
      end_date: link.data.end_date || '',
      timezone: link.data.timezone,
      is_active: link.data.is_active,
    })
    setLoading(false)
  }, [link.data])

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    if (!form.name.trim() || !form.owner) {
      toast('Name and owner are required', 'error')
      return
    }
    setSaving(true)
    const payload = {
      name: form.name,
      owner: form.owner,
      job: form.job || null,
      duration_minutes: Number(form.duration_minutes) || 60,
      start_date: form.start_date || null,
      end_date: form.end_date || null,
      timezone: form.timezone,
      is_active: form.is_active,
    }
    try {
      const saved = isEdit ? await schedulingLinksApi.update(id!, payload) : await schedulingLinksApi.create(payload)
      toast(isEdit ? 'Link updated' : 'Link created', 'success')
      navigate(`/app/calendar/links/${saved.id}`)
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Save failed', 'error')
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div style={{ padding: 64, display: 'grid', placeItems: 'center' }}>
        <Spinner label="Loading link…" />
      </div>
    )
  }

  if (isEdit && !link.loading && link.error) {
    return (
      <EmptyState title="Link not found" description={link.error} actionLabel="Back" onAction={() => navigate('/app/calendar/links')} />
    )
  }

  return (
    <div className="hf-page">
      <PageHeader
        title={isEdit ? 'Edit scheduling link' : 'New scheduling link'}
        subtitle="Configure a public booking link for candidates."
      />
      <form onSubmit={onSubmit}>
        <Card>
          <div style={{ display: 'grid', gap: 14 }}>
            <Input label="Name" required value={form.name} onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))} />
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              <Select
                label="Owner"
                required
                value={form.owner}
                onChange={(e) => setForm((f) => ({ ...f, owner: e.target.value }))}
                placeholder="Select owner"
                options={(members.data?.results || []).map((m) => ({ value: m.user, label: m.user_name }))}
              />
              <Select
                label="Job"
                value={form.job}
                onChange={(e) => setForm((f) => ({ ...f, job: e.target.value }))}
                placeholder="Optional linked job"
                options={(jobs.data?.results || []).map((j) => ({ value: j.id, label: j.title }))}
              />
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12 }}>
              <Input label="Duration (minutes)" type="number" min={15} value={form.duration_minutes} onChange={(e) => setForm((f) => ({ ...f, duration_minutes: Number(e.target.value) || 60 }))} />
              <Input label="Start date" type="date" value={form.start_date} onChange={(e) => setForm((f) => ({ ...f, start_date: e.target.value }))} />
              <Input label="End date" type="date" value={form.end_date} onChange={(e) => setForm((f) => ({ ...f, end_date: e.target.value }))} />
            </div>
            <Input label="Timezone" value={form.timezone} onChange={(e) => setForm((f) => ({ ...f, timezone: e.target.value }))} />
            <label style={{ display: 'flex', gap: 8, alignItems: 'center', fontSize: '0.88rem' }}>
              <input type="checkbox" checked={form.is_active} onChange={(e) => setForm((f) => ({ ...f, is_active: e.target.checked }))} />
              Link active
            </label>
            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
              <Button type="button" variant="outline" onClick={() => navigate(-1)}>
                Cancel
              </Button>
              <Button type="submit" loading={saving}>
                {isEdit ? 'Save changes' : 'Create link'}
              </Button>
            </div>
          </div>
        </Card>
      </form>
    </div>
  )
}

export function SchedulingLinkDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { toast } = useToast()
  const [tab, setTab] = useState('overview')
  const [acting, setActing] = useState(false)
  const [bookingActing, setBookingActing] = useState<string | null>(null)
  const link = useApi(() => schedulingLinksApi.get(id!), [id], { enabled: Boolean(id) })
  const bookings = useApi(
    () => bookingRequestsApi.list({ scheduling_link: id, page_size: 50 }),
    [id, tab],
    { enabled: Boolean(id) && tab === 'bookings' },
  )

  async function runAction(action: () => Promise<unknown>, ok: string) {
    setActing(true)
    try {
      await action()
      toast(ok, 'success')
      link.reload()
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Action failed', 'error')
    } finally {
      setActing(false)
    }
  }

  async function onBookingAction(bookingId: string, action: () => Promise<unknown>, ok: string) {
    setBookingActing(bookingId)
    try {
      await action()
      toast(ok, 'success')
      bookings.reload()
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Action failed', 'error')
    } finally {
      setBookingActing(null)
    }
  }

  function copySlug() {
    void navigator.clipboard?.writeText(`${window.location.origin}/s/${link.data?.slug || ''}`)
    toast('Public link copied', 'success')
  }

  if (link.loading) {
    return (
      <div style={{ padding: 64, display: 'grid', placeItems: 'center' }}>
        <Spinner label="Loading link…" />
      </div>
    )
  }

  if (link.error || !link.data) {
    return (
      <EmptyState
        title="Scheduling link not found"
        description={link.error || 'This link may have been deleted.'}
        actionLabel="Back to links"
        onAction={() => navigate('/app/calendar/links')}
      />
    )
  }

  const l = link.data

  return (
    <div className="hf-page">
      <PageHeader
        title={l.name}
        subtitle={`/${l.slug} · ${l.duration_minutes} min · ${l.timezone}`}
        actions={
          <>
            <Badge tone={l.is_active ? 'success' : 'neutral'}>{l.is_active ? 'Active' : 'Inactive'}</Badge>
            <Button variant="outline" leftIcon={<Copy size={14} />} onClick={copySlug}>
              Copy link
            </Button>
            <Button variant="outline" leftIcon={<Pencil size={14} />} onClick={() => navigate(`/app/calendar/links/${id}/edit`)}>
              Edit
            </Button>
            <Button variant="outline" loading={acting} onClick={() => void runAction(() => schedulingLinksApi.duplicate(id!), 'Link duplicated')}>
              Duplicate
            </Button>
          </>
        }
      />
      <Tabs
        value={tab}
        onChange={setTab}
        items={[
          { id: 'overview', label: 'Overview' },
          { id: 'bookings', label: 'Bookings', count: l.booking_count },
        ]}
      />
      {tab === 'overview' && (
        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 16 }}>
          <Card title="Details">
            <dl style={{ display: 'grid', gap: 10, margin: 0, fontSize: '0.88rem' }}>
              <Row label="Slug" value={`/${l.slug}`} />
              <Row label="Duration" value={`${l.duration_minutes} minutes`} />
              <Row label="Owner" value={String(l.owner)} />
              <Row label="Job" value={l.job ? String(l.job) : '—'} />
              <Row label="Available from" value={formatDate(l.start_date)} />
              <Row label="Available until" value={formatDate(l.end_date)} />
              <Row label="Timezone" value={l.timezone} />
              <Row label="Created" value={formatDate(l.created_at)} />
            </dl>
          </Card>
          <Card title="Stats">
            <dl style={{ display: 'grid', gap: 10, margin: 0, fontSize: '0.88rem' }}>
              <Row label="Bookings" value={String(l.booking_count)} />
              <Row label="Status" value={l.is_active ? 'Active' : 'Inactive'} />
            </dl>
          </Card>
        </div>
      )}
      {tab === 'bookings' && (
        <Card padding={0} title="Bookings">
          <DataTable
            loading={bookings.loading}
            columns={[
              {
                key: 'who',
                header: 'Booked by',
                render: (b: BookingRequest) => (
                  <div>
                    <div style={{ fontWeight: 600 }}>{b.name}</div>
                    <div className="hf-subtle" style={{ fontSize: '0.75rem' }}>{b.email}</div>
                  </div>
                ),
              },
              { key: 'slot', header: 'Requested slot', render: (b: BookingRequest) => formatDateTime(b.requested_slot_start) },
              { key: 'status', header: 'Status', render: (b: BookingRequest) => <Badge status={b.status} /> },
              { key: 'confirmed', header: 'Confirmed', render: (b: BookingRequest) => formatDateTime(b.confirmed_at) },
              {
                key: 'actions',
                header: '',
                render: (b: BookingRequest) => (
                  <div style={{ display: 'flex', gap: 6, justifyContent: 'flex-end' }}>
                    {b.status === 'pending' && (
                      <Button size="sm" variant="outline" loading={bookingActing === b.id} onClick={() => void onBookingAction(b.id, () => bookingRequestsApi.confirm(b.id), 'Booking confirmed')}>
                        Confirm
                      </Button>
                    )}
                    {['pending', 'confirmed'].includes(b.status) && (
                      <Button size="sm" variant="ghost" loading={bookingActing === b.id} onClick={() => void onBookingAction(b.id, () => bookingRequestsApi.cancelBooking(b.id), 'Booking cancelled')}>
                        Cancel
                      </Button>
                    )}
                    {b.status === 'pending' && (
                      <Button size="sm" variant="ghost" loading={bookingActing === b.id} onClick={() => void onBookingAction(b.id, () => bookingRequestsApi.decline(b.id), 'Booking declined')}>
                        Decline
                      </Button>
                    )}
                  </div>
                ),
              },
            ]}
            rows={bookings.data?.results || []}
            rowKey={(b) => b.id}
            emptyTitle="No bookings yet"
            emptyDescription="Share the scheduling link to receive booking requests."
          />
        </Card>
      )}
    </div>
  )
}

export function BookingRequestsPage() {
  const { toast } = useToast()
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('')
  const [acting, setActing] = useState<string | null>(null)
  const bookings = useApi(
    () =>
      bookingRequestsApi.list({
        page,
        page_size: 20,
        search: search || undefined,
        status: status || undefined,
      }),
    [page, search, status],
    { enabled: true },
  )

  async function runAction(bookingId: string, action: () => Promise<unknown>, ok: string) {
    setActing(bookingId)
    try {
      await action()
      toast(ok, 'success')
      bookings.reload()
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Action failed', 'error')
    } finally {
      setActing(null)
    }
  }

  return (
    <div className="hf-page">
      <PageHeader
        title="Booking requests"
        subtitle="Review and manage interview booking requests from candidates."
      />
      <Card padding="1rem">
        <FilterBar
          search={search}
          onSearchChange={(v) => {
            setPage(1)
            setSearch(v)
          }}
          searchPlaceholder="Search by name or email…"
          filters={[
            {
              key: 'status',
              label: 'Status',
              value: status,
              onChange: (v) => {
                setPage(1)
                setStatus(v)
              },
              options: [
                { value: 'pending', label: 'Pending' },
                { value: 'confirmed', label: 'Confirmed' },
                { value: 'cancelled', label: 'Cancelled' },
                { value: 'declined', label: 'Declined' },
              ],
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
          loading={bookings.loading}
          columns={[
            {
              key: 'who',
              header: 'Candidate',
              render: (b: BookingRequest) => (
                <div>
                  <div style={{ fontWeight: 600 }}>{b.name}</div>
                  <div className="hf-subtle" style={{ fontSize: '0.75rem' }}>{b.email}</div>
                </div>
              ),
            },
            { key: 'link', header: 'Link', render: (b: BookingRequest) => b.link_name || b.scheduling_link },
            { key: 'slot', header: 'Requested slot', render: (b: BookingRequest) => formatDateTime(b.requested_slot_start) },
            { key: 'status', header: 'Status', render: (b: BookingRequest) => <Badge status={b.status} /> },
            {
              key: 'actions',
              header: '',
              render: (b: BookingRequest) => (
                <div style={{ display: 'flex', gap: 6, justifyContent: 'flex-end' }}>
                  {b.status === 'pending' && (
                    <Button size="sm" variant="outline" loading={acting === b.id} onClick={() => void runAction(b.id, () => bookingRequestsApi.confirm(b.id), 'Booking confirmed')}>
                      Confirm
                    </Button>
                  )}
                  {['pending', 'confirmed'].includes(b.status) && (
                    <Button size="sm" variant="ghost" loading={acting === b.id} onClick={() => void runAction(b.id, () => bookingRequestsApi.cancelBooking(b.id), 'Booking cancelled')}>
                      Cancel
                    </Button>
                  )}
                  {b.status === 'pending' && (
                    <Button size="sm" variant="ghost" loading={acting === b.id} onClick={() => void runAction(b.id, () => bookingRequestsApi.decline(b.id), 'Booking declined')}>
                      Decline
                    </Button>
                  )}
                </div>
              ),
            },
          ]}
          rows={bookings.data?.results || []}
          rowKey={(b) => b.id}
          emptyTitle="No booking requests"
          emptyDescription="Requests will appear here when candidates book through your links."
        />
        {bookings.data && <Pagination page={page} pageSize={20} total={bookings.data.count} onChange={setPage} />}
      </Card>
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
