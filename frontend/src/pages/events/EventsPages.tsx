/**
 * EventsPages.tsx — Recruiting events frontend.
 *
 * Exported components & suggested routes (wired by main agent in App.tsx):
 *   EventsPage        → /app/events
 *   EventFormPage     → /app/events/new, /app/events/:id/edit
 *   EventDetailPage   → /app/events/:id
 */
import { useState, type FormEvent } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { Download, Pencil, Plus, Trash2 } from 'lucide-react'
import { eventsApi, eventRegistrationsApi, eventSessionsApi, eventTasksApi } from '../../api/events'
import type { EventSession, EventTask, RecruitingEvent } from '../../api/events'
import { useApi } from '../../hooks/useApi'
import { PageHeader } from '../../components/layout/PageHeader'
import {
  Badge,
  Button,
  Card,
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
  useToast,
} from '../../components/ui'
import { formatDate, formatDateTime, titleCase } from '../../utils/format'
import { ApiError } from '../../api/http'

const EVENT_TYPES = [
  { value: 'career_fair', label: 'Career fair' },
  { value: 'webinar', label: 'Webinar' },
  { value: 'campus', label: 'Campus' },
  { value: 'onsite', label: 'On-site' },
  { value: 'other', label: 'Other' },
]

const EVENT_STATUSES = [
  { value: 'draft', label: 'Draft' },
  { value: 'scheduled', label: 'Scheduled' },
  { value: 'ongoing', label: 'Ongoing' },
  { value: 'completed', label: 'Completed' },
  { value: 'cancelled', label: 'Cancelled' },
]

export function EventsPage() {
  const navigate = useNavigate()
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('')
  const [eventType, setEventType] = useState('')
  const { data, loading, error, reload } = useApi(
    () =>
      eventsApi.list({
        page,
        page_size: 20,
        search: search || undefined,
        status: status || undefined,
        event_type: eventType || undefined,
      }),
    [page, search, status, eventType],
    { enabled: true },
  )

  return (
    <div className="hf-page">
      <PageHeader
        title="Events"
        subtitle="Plan career fairs, webinars, campus events, and track registrations."
        actions={
          <Button leftIcon={<Plus size={16} />} onClick={() => navigate('/app/events/new')}>
            New event
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
          searchPlaceholder="Search events…"
          filters={[
            {
              key: 'status',
              label: 'Status',
              value: status,
              onChange: (v) => {
                setPage(1)
                setStatus(v)
              },
              options: EVENT_STATUSES,
            },
            {
              key: 'event_type',
              label: 'Type',
              value: eventType,
              onChange: (v) => {
                setPage(1)
                setEventType(v)
              },
              options: EVENT_TYPES,
            },
          ]}
          onClear={() => {
            setSearch('')
            setStatus('')
            setEventType('')
            setPage(1)
          }}
        />
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
              header: 'Event',
              render: (e: RecruitingEvent) => (
                <div>
                  <Link to={`/app/events/${e.id}`} style={{ fontWeight: 650, textDecoration: 'none' }}>
                    {e.name}
                  </Link>
                  <div className="hf-subtle" style={{ fontSize: '0.75rem' }}>
                    {titleCase(e.event_type)} · {e.is_virtual ? 'Virtual' : e.location || 'In person'}
                  </div>
                </div>
              ),
            },
            {
              key: 'when',
              header: 'When',
              render: (e: RecruitingEvent) => (
                <div>
                  <div>{formatDateTime(e.start_at)}</div>
                  {e.end_at && (
                    <div className="hf-subtle" style={{ fontSize: '0.75rem' }}>
                      → {formatDateTime(e.end_at)}
                    </div>
                  )}
                </div>
              ),
            },
            {
              key: 'registrations',
              header: 'Registrations',
              render: (e: RecruitingEvent) => `${e.registration_count}${e.capacity ? ` / ${e.capacity}` : ''}`,
            },
            { key: 'sessions', header: 'Sessions', render: (e: RecruitingEvent) => e.session_count },
            { key: 'status', header: 'Status', render: (e: RecruitingEvent) => <Badge status={e.status} /> },
          ]}
          rows={data?.results || []}
          rowKey={(e) => e.id}
          emptyTitle="No events found"
          emptyDescription="Create your first recruiting event to get started."
          onRowClick={(e) => navigate(`/app/events/${e.id}`)}
        />
        {data && <Pagination page={page} pageSize={20} total={data.count} onChange={setPage} />}
      </Card>
    </div>
  )
}

const emptyEvent = {
  name: '',
  event_type: 'other',
  description: '',
  location: '',
  is_virtual: false,
  start_at: '',
  end_at: '',
  capacity: '',
}

export function EventFormPage() {
  const { id } = useParams()
  const isEdit = Boolean(id)
  const navigate = useNavigate()
  const { toast } = useToast()
  const [form, setForm] = useState(emptyEvent)
  const [loading, setLoading] = useState(isEdit)
  const [saving, setSaving] = useState(false)

  const event = useApi(() => eventsApi.get(id!), [id], { enabled: isEdit })

  function set<K extends keyof typeof emptyEvent>(key: K, value: (typeof emptyEvent)[K]) {
    setForm((f) => ({ ...f, [key]: value }))
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    if (!form.name.trim()) {
      toast('Event name is required', 'error')
      return
    }
    setSaving(true)
    const payload = {
      name: form.name,
      event_type: form.event_type,
      description: form.description,
      location: form.location,
      is_virtual: form.is_virtual,
      start_at: form.start_at || null,
      end_at: form.end_at || null,
      capacity: form.capacity ? Number(form.capacity) : null,
    }
    try {
      const saved = isEdit ? await eventsApi.update(id!, payload) : await eventsApi.create(payload)
      toast(isEdit ? 'Event updated' : 'Event created', 'success')
      navigate(`/app/events/${saved.id}`)
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Save failed', 'error')
    } finally {
      setSaving(false)
    }
  }

  if (loading && !event.data) {
    return (
      <div style={{ padding: 64, display: 'grid', placeItems: 'center' }}>
        <Spinner label="Loading event…" />
      </div>
    )
  }

  if (isEdit && !event.loading && event.error) {
    return (
      <EmptyState title="Event not found" description={event.error} actionLabel="Back" onAction={() => navigate('/app/events')} />
    )
  }

  return (
    <div className="hf-page">
      <PageHeader
        title={isEdit ? 'Edit event' : 'Create event'}
        subtitle="Define the event details, schedule, and capacity."
      />
      <form onSubmit={onSubmit}>
        <Card>
          <div style={{ display: 'grid', gap: 14 }}>
            <Input label="Event name" required value={form.name} onChange={(e) => set('name', e.target.value)} />
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              <Select
                label="Event type"
                value={form.event_type}
                onChange={(e) => set('event_type', e.target.value)}
                options={EVENT_TYPES}
              />
              <Input
                label="Location"
                value={form.location}
                onChange={(e) => set('location', e.target.value)}
                placeholder="Venue or online platform"
              />
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              <Input
                label="Starts at"
                type="datetime-local"
                required
                value={form.start_at}
                onChange={(e) => set('start_at', e.target.value)}
              />
              <Input
                label="Ends at"
                type="datetime-local"
                value={form.end_at}
                onChange={(e) => set('end_at', e.target.value)}
              />
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              <Input
                label="Capacity"
                type="number"
                min={1}
                value={form.capacity}
                onChange={(e) => set('capacity', e.target.value)}
                placeholder="Optional"
              />
              <label style={{ display: 'flex', gap: 8, alignItems: 'flex-end', fontSize: '0.88rem', paddingBottom: 10 }}>
                <input
                  type="checkbox"
                  checked={form.is_virtual}
                  onChange={(e) => set('is_virtual', e.target.checked)}
                />
                Virtual event
              </label>
            </div>
            <Textarea label="Description" value={form.description} onChange={(e) => set('description', e.target.value)} />
            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
              <Button type="button" variant="outline" onClick={() => navigate(-1)}>
                Cancel
              </Button>
              <Button type="submit" loading={saving}>
                {isEdit ? 'Save changes' : 'Create event'}
              </Button>
            </div>
          </div>
        </Card>
      </form>
    </div>
  )
}

export function EventDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { toast } = useToast()
  const [tab, setTab] = useState('overview')
  const [acting, setActing] = useState(false)
  const event = useApi(() => eventsApi.get(id!), [id], { enabled: Boolean(id) })
  const sessions = useApi(() => eventsApi.listSessions(id!), [id, tab], {
    enabled: Boolean(id) && tab === 'sessions',
  })
  const tasks = useApi(() => eventTasksApi.list({ event: id, page_size: 50 }), [id, tab], {
    enabled: Boolean(id) && tab === 'tasks',
  })

  async function runAction(action: () => Promise<unknown>, ok: string) {
    setActing(true)
    try {
      await action()
      toast(ok, 'success')
      event.reload()
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Action failed', 'error')
    } finally {
      setActing(false)
    }
  }

  if (event.loading) {
    return (
      <div style={{ padding: 64, display: 'grid', placeItems: 'center' }}>
        <Spinner label="Loading event…" />
      </div>
    )
  }

  if (event.error || !event.data) {
    return (
      <EmptyState
        title="Event not found"
        description={event.error || 'This event may have been deleted.'}
        actionLabel="Back to events"
        onAction={() => navigate('/app/events')}
      />
    )
  }

  const e = event.data

  return (
    <div className="hf-page">
      <PageHeader
        title={e.name}
        subtitle={`${titleCase(e.event_type)} · ${formatDateTime(e.start_at)} · ${e.is_virtual ? 'Virtual' : e.location || 'In person'}`}
        actions={
          <>
            <Badge status={e.status} />
            <Button variant="outline" leftIcon={<Pencil size={14} />} onClick={() => navigate(`/app/events/${id}/edit`)}>
              Edit
            </Button>
            <Button variant="outline" leftIcon={<Download size={14} />} onClick={() => void exportCsv()}>
              Export CSV
            </Button>
            {e.status === 'draft' && (
              <Button
                loading={acting}
                onClick={() => runAction(() => eventsApi.publish(id!), 'Event published')}
              >
                Publish
              </Button>
            )}
            {['scheduled', 'ongoing'].includes(e.status) && (
              <Button
                variant="outline"
                loading={acting}
                onClick={() => runAction(() => eventsApi.complete(id!), 'Event completed')}
              >
                Mark complete
              </Button>
            )}
            {['draft', 'scheduled', 'ongoing'].includes(e.status) && (
              <Button
                variant="danger"
                loading={acting}
                onClick={() => runAction(() => eventsApi.cancel(id!), 'Event cancelled')}
              >
                Cancel event
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
          { id: 'sessions', label: 'Sessions', count: e.session_count },
          { id: 'registrations', label: 'Registrations', count: e.registration_count },
          { id: 'tasks', label: 'Tasks' },
        ]}
      />

      {tab === 'overview' && (
        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 16 }}>
          <Card title="Description">
            <div style={{ whiteSpace: 'pre-wrap', lineHeight: 1.6 }} className="hf-muted">
              {e.description || 'No description yet.'}
            </div>
          </Card>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <Card title="Details">
              <dl style={{ display: 'grid', gap: 10, margin: 0, fontSize: '0.88rem' }}>
                <Row label="Type" value={titleCase(e.event_type)} />
                <Row label="Starts" value={formatDateTime(e.start_at)} />
                <Row label="Ends" value={formatDateTime(e.end_at)} />
                <Row label="Format" value={e.is_virtual ? 'Virtual' : 'In person'} />
                <Row label="Location" value={e.location || '—'} />
                <Row label="Capacity" value={e.capacity ? String(e.capacity) : 'Unlimited'} />
              </dl>
            </Card>
            <Card title="Stats">
              <dl style={{ display: 'grid', gap: 10, margin: 0, fontSize: '0.88rem' }}>
                <Row label="Registrations" value={String(e.registration_count)} />
                <Row label="Sessions" value={String(e.session_count)} />
                <Row label="Created" value={formatDate(e.created_at)} />
              </dl>
            </Card>
          </div>
        </div>
      )}

      {tab === 'sessions' && (
        <SessionsTab eventId={e.id} sessions={sessions} onChanged={() => sessions.reload()} />
      )}

      {tab === 'registrations' && <RegistrationsTab eventId={e.id} />}

      {tab === 'tasks' && <TasksTab eventId={e.id} tasks={tasks} />}
    </div>
  )

  async function exportCsv() {
    try {
      await eventsApi.exportRegistrations(id!)
      toast('Registrations exported', 'success')
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Export failed', 'error')
    }
  }
}

function SessionsTab({
  eventId,
  sessions,
  onChanged,
}: {
  eventId: string
  sessions: { data: EventSession[] | null; loading: boolean; error: string | null }
  onChanged: () => void
}) {
  const { toast } = useToast()
  const [open, setOpen] = useState(false)
  const [form, setForm] = useState({ title: '', speaker: '', start_at: '', end_at: '', room: '', description: '' })
  const [saving, setSaving] = useState(false)
  const [removing, setRemoving] = useState<string | null>(null)

  function set<K extends keyof typeof form>(key: K, value: string) {
    setForm((f) => ({ ...f, [key]: value }))
  }

  async function onCreate(e: FormEvent) {
    e.preventDefault()
    setSaving(true)
    try {
      await eventsApi.addSession(eventId, {
        title: form.title,
        speaker: form.speaker,
        start_at: form.start_at || null,
        end_at: form.end_at || null,
        room: form.room,
        description: form.description,
      })
      toast('Session added', 'success')
      setOpen(false)
      setForm({ title: '', speaker: '', start_at: '', end_at: '', room: '', description: '' })
      onChanged()
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Failed to add session', 'error')
    } finally {
      setSaving(false)
    }
  }

  async function onRemove(sessionId: string) {
    setRemoving(sessionId)
    try {
      await eventSessionsApi.remove(sessionId)
      toast('Session removed', 'success')
      onChanged()
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Failed to remove session', 'error')
    } finally {
      setRemoving(null)
    }
  }

  return (
    <Card
      title="Sessions"
      actions={
        <Button size="sm" leftIcon={<Plus size={14} />} onClick={() => setOpen(true)}>
          Add session
        </Button>
      }
    >
      {sessions.loading ? (
        <div style={{ padding: 40, display: 'grid', placeItems: 'center' }}>
          <Spinner />
        </div>
      ) : (sessions.data || []).length ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {(sessions.data || []).map((s) => (
            <div
              key={s.id}
              style={{
                padding: 12,
                borderRadius: 10,
                border: '1px solid var(--hf-border)',
                display: 'flex',
                justifyContent: 'space-between',
                gap: 12,
                alignItems: 'flex-start',
              }}
            >
              <div>
                <div style={{ fontWeight: 600 }}>{s.title}</div>
                <div className="hf-subtle" style={{ fontSize: '0.8rem', marginTop: 2 }}>
                  {formatDateTime(s.start_at)}
                  {s.end_at ? ` → ${formatDateTime(s.end_at)}` : ''}
                  {s.speaker ? ` · ${s.speaker}` : ''}
                  {s.room ? ` · ${s.room}` : ''}
                </div>
                {s.description && (
                  <p className="hf-muted" style={{ marginTop: 6, fontSize: '0.85rem' }}>
                    {s.description}
                  </p>
                )}
              </div>
              <Button
                variant="ghost"
                size="sm"
                loading={removing === s.id}
                onClick={() => void onRemove(s.id)}
                aria-label="Remove session"
              >
                <Trash2 size={14} />
              </Button>
            </div>
          ))}
        </div>
      ) : (
        <EmptyState title="No sessions" description="Add agenda items for this event." />
      )}
      <Modal open={open} onClose={() => setOpen(false)} title="Add session">
        <form onSubmit={onCreate} style={{ display: 'grid', gap: 12 }}>
          <Input label="Title" required value={form.title} onChange={(e) => set('title', e.target.value)} />
          <Input label="Speaker" value={form.speaker} onChange={(e) => set('speaker', e.target.value)} />
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <Input label="Starts at" type="datetime-local" value={form.start_at} onChange={(e) => set('start_at', e.target.value)} />
            <Input label="Ends at" type="datetime-local" value={form.end_at} onChange={(e) => set('end_at', e.target.value)} />
          </div>
          <Input label="Room" value={form.room} onChange={(e) => set('room', e.target.value)} />
          <Textarea label="Description" value={form.description} onChange={(e) => set('description', e.target.value)} />
          <Button type="submit" loading={saving}>
            Add session
          </Button>
        </form>
      </Modal>
    </Card>
  )
}

function RegistrationsTab({ eventId }: { eventId: string }) {
  const navigate = useNavigate()
  const { toast } = useToast()
  const [page, setPage] = useState(1)
  const [status, setStatus] = useState('')
  const [open, setOpen] = useState(false)
  const [acting, setActing] = useState<string | null>(null)
  const [form, setForm] = useState({ email: '', first_name: '', last_name: '' })
  const [saving, setSaving] = useState(false)
  const regs = useApi(
    () => eventsApi.listRegistrations(eventId, { page, page_size: 20, status: status || undefined }),
    [eventId, page, status],
    { enabled: true },
  )

  async function runAction(regId: string, action: () => Promise<unknown>, ok: string) {
    setActing(regId)
    try {
      await action()
      toast(ok, 'success')
      regs.reload()
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
      await eventRegistrationsApi.create({ event: eventId, ...form })
      toast('Registration added', 'success')
      setOpen(false)
      setForm({ email: '', first_name: '', last_name: '' })
      regs.reload()
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Failed to register', 'error')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Card
      padding={0}
      title="Registrations"
      actions={
        <div style={{ display: 'flex', gap: 8 }}>
          <Button size="sm" variant="outline" leftIcon={<Download size={14} />} onClick={() => void exportCsv()}>
            Export
          </Button>
          <Button size="sm" leftIcon={<Plus size={14} />} onClick={() => setOpen(true)}>
            Add registration
          </Button>
        </div>
      }
    >
      <div style={{ padding: '0.75rem 1.25rem', borderBottom: '1px solid var(--hf-border)' }}>
        <FilterBar
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
                { value: 'registered', label: 'Registered' },
                { value: 'attended', label: 'Attended' },
                { value: 'no_show', label: 'No show' },
                { value: 'cancelled', label: 'Cancelled' },
                { value: 'waitlisted', label: 'Waitlisted' },
              ],
            },
          ]}
          onClear={() => {
            setStatus('')
            setPage(1)
          }}
        />
      </div>
      <DataTable
        loading={regs.loading}
        columns={[
          {
            key: 'name',
            header: 'Attendee',
            render: (r) => (
              <div>
                <div style={{ fontWeight: 600 }}>
                  {r.first_name || r.last_name ? `${r.first_name} ${r.last_name}`.trim() : r.email}
                </div>
                <div className="hf-subtle" style={{ fontSize: '0.75rem' }}>{r.email}</div>
              </div>
            ),
          },
          { key: 'status', header: 'Status', render: (r) => <Badge status={r.status} /> },
          { key: 'registered', header: 'Registered', render: (r) => formatDateTime(r.registered_at) },
          {
            key: 'checked_in',
            header: 'Checked in',
            render: (r) => (r.checked_in_at ? formatDateTime(r.checked_in_at) : '—'),
          },
          {
            key: 'actions',
            header: '',
            render: (r) => (
              <div style={{ display: 'flex', gap: 6, justifyContent: 'flex-end' }}>
                {r.status === 'registered' && (
                  <Button size="sm" variant="outline" loading={acting === r.id} onClick={() => void runAction(r.id, () => eventRegistrationsApi.checkIn(r.id), 'Checked in')}>
                    Check in
                  </Button>
                )}
                {['registered', 'attended', 'waitlisted'].includes(r.status) && (
                  <Button size="sm" variant="ghost" loading={acting === r.id} onClick={() => void runAction(r.id, () => eventRegistrationsApi.cancelRegistration(r.id), 'Registration cancelled')}>
                    Cancel
                  </Button>
                )}
                {['registered', 'cancelled'].includes(r.status) && (
                  <Button size="sm" variant="ghost" loading={acting === r.id} onClick={() => void runAction(r.id, () => eventRegistrationsApi.waitlist(r.id), 'Moved to waitlist')}>
                    Waitlist
                  </Button>
                )}
              </div>
            ),
          },
        ]}
        rows={regs.data?.results || []}
        rowKey={(r) => r.id}
        emptyTitle="No registrations"
        emptyDescription="Add attendees or share the event link."
      />
      {regs.data && <Pagination page={page} pageSize={20} total={regs.data.count} onChange={setPage} />}

      <Modal open={open} onClose={() => setOpen(false)} title="Add registration">
        <form onSubmit={onCreate} style={{ display: 'grid', gap: 12 }}>
          <Input label="Email" type="email" required value={form.email} onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))} />
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <Input label="First name" value={form.first_name} onChange={(e) => setForm((f) => ({ ...f, first_name: e.target.value }))} />
            <Input label="Last name" value={form.last_name} onChange={(e) => setForm((f) => ({ ...f, last_name: e.target.value }))} />
          </div>
          <Button type="submit" loading={saving}>
            Register
          </Button>
        </form>
      </Modal>
    </Card>
  )

  async function exportCsv() {
    try {
      await eventsApi.exportRegistrations(eventId)
      toast('Registrations exported', 'success')
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Export failed', 'error')
    }
  }
}

function TasksTab({
  eventId,
  tasks,
}: {
  eventId: string
  tasks: { data: { results: EventTask[] } | null; loading: boolean; error: string | null; reload: () => void }
}) {
  const { toast } = useToast()
  const [open, setOpen] = useState(false)
  const [acting, setActing] = useState<string | null>(null)
  const [form, setForm] = useState({ title: '', notes: '', due_at: '' })
  const [saving, setSaving] = useState(false)

  async function onCreate(e: FormEvent) {
    e.preventDefault()
    setSaving(true)
    try {
      await eventTasksApi.create({ event: eventId, title: form.title, notes: form.notes, due_at: form.due_at || null })
      toast('Task created', 'success')
      setOpen(false)
      setForm({ title: '', notes: '', due_at: '' })
      tasks.reload()
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Failed to create task', 'error')
    } finally {
      setSaving(false)
    }
  }

  async function onComplete(taskId: string) {
    setActing(taskId)
    try {
      await eventTasksApi.complete(taskId)
      toast('Task completed', 'success')
      tasks.reload()
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Action failed', 'error')
    } finally {
      setActing(null)
    }
  }

  return (
    <Card
      title="Tasks"
      actions={
        <Button size="sm" leftIcon={<Plus size={14} />} onClick={() => setOpen(true)}>
          Add task
        </Button>
      }
    >
      {tasks.loading ? (
        <div style={{ padding: 40, display: 'grid', placeItems: 'center' }}>
          <Spinner />
        </div>
      ) : (tasks.data?.results || []).length ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {(tasks.data?.results || []).map((t) => (
            <div
              key={t.id}
              style={{
                padding: 12,
                borderRadius: 10,
                border: '1px solid var(--hf-border)',
                display: 'flex',
                justifyContent: 'space-between',
                gap: 12,
                alignItems: 'flex-start',
              }}
            >
              <div>
                <div style={{ fontWeight: 600 }}>{t.title}</div>
                <div className="hf-subtle" style={{ fontSize: '0.8rem', marginTop: 2 }}>
                  Due {formatDateTime(t.due_at)}
                </div>
                {t.notes && (
                  <p className="hf-muted" style={{ marginTop: 6, fontSize: '0.85rem' }}>
                    {t.notes}
                  </p>
                )}
              </div>
              <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                <Badge status={t.status} />
                {t.status !== 'completed' && (
                  <Button size="sm" variant="outline" loading={acting === t.id} onClick={() => void onComplete(t.id)}>
                    Complete
                  </Button>
                )}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <EmptyState title="No tasks" description="Add to-dos to run this event smoothly." />
      )}
      <Modal open={open} onClose={() => setOpen(false)} title="Add task">
        <form onSubmit={onCreate} style={{ display: 'grid', gap: 12 }}>
          <Input label="Title" required value={form.title} onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))} />
          <Input label="Due at" type="datetime-local" value={form.due_at} onChange={(e) => setForm((f) => ({ ...f, due_at: e.target.value }))} />
          <Textarea label="Notes" value={form.notes} onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))} />
          <Button type="submit" loading={saving}>
            Create task
          </Button>
        </form>
      </Modal>
    </Card>
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
