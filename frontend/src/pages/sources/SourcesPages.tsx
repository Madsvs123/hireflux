/**
 * Sourcing pages.
 *
 * Exported components and suggested routes (wire into App.tsx):
 *   - SourceChannelsPage        -> /app/sources/channels
 *   - SourcingCampaignsPage     -> /app/sources
 *   - SourcingCampaignFormPage  -> /app/sources/campaigns/new, /app/sources/campaigns/:id/edit
 *   - SourcingCampaignDetailPage-> /app/sources/campaigns/:id
 *   - SourceAttributionPage     -> /app/sources/attribution
 */
import { useEffect, useState, type FormEvent, type ReactNode } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import {
  BarChart3,
  Flag,
  Link2,
  Mail,
  Megaphone,
  Pause,
  Pencil,
  Play,
  Plus,
  RotateCw,
  Send,
  Trash2,
  Users,
} from 'lucide-react'
import {
  sourcesApi,
  type CampaignRecipient,
  type SourceChannel,
  type SourcingCampaign,
} from '../../api/sources'
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
  useToast,
} from '../../components/ui'
import { formatCurrency, formatDate, formatDateTime, titleCase } from '../../utils/format'
import { ApiError } from '../../api/http'

// NOTE: the shared <Select> emits option labels as values, so options carry
// display labels and are mapped back to API values on submit.
const CHANNEL_TYPE_OPTIONS = [
  { value: 'Job Board', label: 'Job Board' },
  { value: 'Social', label: 'Social' },
  { value: 'Agency', label: 'Agency' },
  { value: 'Referral', label: 'Referral' },
  { value: 'Direct', label: 'Direct' },
  { value: 'Other', label: 'Other' },
]
const CHANNEL_TYPE_VALUES: Record<string, string> = {
  'Job Board': 'job_board',
  Social: 'social',
  Agency: 'agency',
  Referral: 'referral',
  Direct: 'direct',
  Other: 'other',
}

const CAMPAIGN_STATUS_OPTIONS = [
  { value: 'Draft', label: 'Draft' },
  { value: 'Active', label: 'Active' },
  { value: 'Paused', label: 'Paused' },
  { value: 'Completed', label: 'Completed' },
]
const CAMPAIGN_STATUS_VALUES: Record<string, string> = {
  Draft: 'draft',
  Active: 'active',
  Paused: 'paused',
  Completed: 'completed',
}

const RECIPIENT_STATUS_OPTIONS = [
  { value: 'Queued', label: 'Queued' },
  { value: 'Sent', label: 'Sent' },
  { value: 'Opened', label: 'Opened' },
  { value: 'Replied', label: 'Replied' },
  { value: 'Opted Out', label: 'Opted Out' },
]
const RECIPIENT_STATUS_VALUES: Record<string, string> = {
  Queued: 'queued',
  Sent: 'sent',
  Opened: 'opened',
  Replied: 'replied',
  'Opted Out': 'opted_out',
}

function channelTypeLabel(value?: string) {
  if (!value) return ''
  return CHANNEL_TYPE_OPTIONS.find((o) => CHANNEL_TYPE_VALUES[o.value] === value)?.value ?? value
}

export function SourceChannelsPage() {
  const navigate = useNavigate()
  const { toast } = useToast()
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [type, setType] = useState('')
  const [active, setActive] = useState('')
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<SourceChannel | null>(null)
  const [deleting, setDeleting] = useState<SourceChannel | null>(null)

  const channels = useApi(
    () =>
      sourcesApi.channels.list({
        page,
        page_size: 20,
        search: search || undefined,
        channel_type: type ? CHANNEL_TYPE_VALUES[type] : undefined,
        is_active: active === 'Active' ? true : active === 'Inactive' ? false : undefined,
      }),
    [page, search, type, active],
    { enabled: true },
  )
  const stats = useApi(() => sourcesApi.channels.stats(), [channels.data?.count], { enabled: true })

  return (
    <div className="hf-page">
      <PageHeader
        title="Source channels"
        subtitle="Track where your candidates come from and how much each channel costs."
        breadcrumbs={[{ label: 'Sourcing', to: '/app/sources' }, { label: 'Channels' }]}
        actions={
          <Button
            leftIcon={<Plus size={16} />}
            onClick={() => {
              setEditing(null)
              setModalOpen(true)
            }}
          >
            New channel
          </Button>
        }
      />

      {(stats.data?.channels || []).length > 0 && (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
            gap: 12,
          }}
        >
          <StatCard
            label="Channels"
            value={stats.data?.channels.length ?? 0}
            icon={<Link2 size={16} />}
          />
          <StatCard
            label="Campaigns"
            value={stats.data?.channels.reduce((n, c) => n + c.campaigns, 0) ?? 0}
            icon={<Megaphone size={16} />}
          />
          <StatCard
            label="Recipients"
            value={stats.data?.channels.reduce((n, c) => n + c.recipients, 0) ?? 0}
            icon={<Mail size={16} />}
          />
          <StatCard
            label="Attributions"
            value={stats.data?.channels.reduce((n, c) => n + c.attributions, 0) ?? 0}
            icon={<Users size={16} />}
          />
        </div>
      )}

      <Card padding="1rem">
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, alignItems: 'flex-end' }}>
          <div style={{ flex: '1 1 220px', minWidth: 200 }}>
            <Input
              value={search}
              onChange={(e) => {
                setPage(1)
                setSearch(e.target.value)
              }}
              placeholder="Search channels…"
            />
          </div>
          <div style={{ minWidth: 150, flex: '0 1 160px' }}>
            <Select
              label="Type"
              value={type}
              onChange={(e) => {
                setPage(1)
                setType(e.target.value)
              }}
              options={[{ value: '', label: 'All' }, ...CHANNEL_TYPE_OPTIONS]}
            />
          </div>
          <div style={{ minWidth: 150, flex: '0 1 160px' }}>
            <Select
              label="Status"
              value={active}
              onChange={(e) => {
                setPage(1)
                setActive(e.target.value)
              }}
              options={[
                { value: '', label: 'All' },
                { value: 'Active', label: 'Active' },
                { value: 'Inactive', label: 'Inactive' },
              ]}
            />
          </div>
          <div style={{ display: 'flex', gap: 8, marginLeft: 'auto' }}>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                setSearch('')
                setType('')
                setActive('')
                setPage(1)
              }}
            >
              Clear
            </Button>
          </div>
        </div>
      </Card>

      <Card padding={0}>
        <DataTable
          loading={channels.loading}
          columns={[
            {
              key: 'name',
              header: 'Channel',
              render: (c: SourceChannel) => (
                <div>
                  <span style={{ fontWeight: 650 }}>{c.name}</span>
                  <div className="hf-subtle" style={{ fontSize: '0.75rem' }}>
                    {channelTypeLabel(c.channel_type)}
                  </div>
                </div>
              ),
            },
            { key: 'url', header: 'URL', render: (c: SourceChannel) => c.url || '—' },
            {
              key: 'cost',
              header: 'Cost / post',
              render: (c: SourceChannel) => formatCurrency(c.cost_per_post),
            },
            {
              key: 'active',
              header: 'Status',
              render: (c: SourceChannel) => (
                <Badge tone={c.is_active ? 'success' : 'neutral'}>
                  {c.is_active ? 'Active' : 'Inactive'}
                </Badge>
              ),
            },
            {
              key: 'actions',
              header: '',
              render: (c: SourceChannel) => (
                <div style={{ display: 'flex', gap: 4 }}>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={(e) => {
                      e.stopPropagation()
                      setEditing(c)
                      setModalOpen(true)
                    }}
                  >
                    <Pencil size={14} />
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={(e) => {
                      e.stopPropagation()
                      setDeleting(c)
                    }}
                  >
                    <Trash2 size={14} />
                  </Button>
                </div>
              ),
            },
          ]}
          rows={channels.data?.results || []}
          rowKey={(c) => c.id}
          emptyTitle="No channels"
          emptyDescription="Add a source channel to start attributing candidates."
        />
        {channels.data && (
          <Pagination page={page} pageSize={20} total={channels.data.count} onChange={setPage} />
        )}
      </Card>

      <ChannelFormModal
        open={modalOpen}
        editing={editing}
        onClose={() => setModalOpen(false)}
        onSaved={() => {
          channels.reload()
          stats.reload()
          setModalOpen(false)
        }}
      />
      <ConfirmDialog
        open={Boolean(deleting)}
        title="Delete channel"
        message={`Delete "${deleting?.name}"? Existing attributions will keep their history.`}
        confirmLabel="Delete"
        danger
        onCancel={() => setDeleting(null)}
        onConfirm={() => {
          if (!deleting) return
          sourcesApi.channels
            .remove(deleting.id)
            .then(() => {
              toast('Channel deleted', 'success')
              channels.reload()
              stats.reload()
            })
            .catch((err: unknown) =>
              toast(err instanceof ApiError ? err.message : 'Delete failed', 'error'),
            )
            .finally(() => setDeleting(null))
        }}
      />
    </div>
  )
}

function ChannelFormModal({
  open,
  editing,
  onClose,
  onSaved,
}: {
  open: boolean
  editing: SourceChannel | null
  onClose: () => void
  onSaved: () => void
}) {
  const { toast } = useToast()
  const [name, setName] = useState('')
  const [channelType, setChannelType] = useState('Job Board')
  const [url, setUrl] = useState('')
  const [cost, setCost] = useState('')
  const [notes, setNotes] = useState('')
  const [isActive, setIsActive] = useState(true)
  const [saving, setSaving] = useState(false)
  const [seed, setSeed] = useState('')

  if (open && seed !== (editing?.id || 'new')) {
    setSeed(editing?.id || 'new')
    setName(editing?.name || '')
    setChannelType(channelTypeLabel(editing?.channel_type) || 'Job Board')
    setUrl(editing?.url || '')
    setCost(editing?.cost_per_post || '')
    setNotes(editing?.notes || '')
    setIsActive(editing?.is_active ?? true)
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setSaving(true)
    const payload = {
      name,
      channel_type: CHANNEL_TYPE_VALUES[channelType] || channelType,
      url: url || null,
      cost_per_post: cost || null,
      notes: notes || '',
      is_active: isActive,
    }
    try {
      if (editing) {
        await sourcesApi.channels.update(editing.id, payload)
        toast('Channel updated', 'success')
      } else {
        await sourcesApi.channels.create(payload)
        toast('Channel created', 'success')
      }
      onSaved()
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Save failed', 'error')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal open={open} onClose={onClose} title={editing ? 'Edit channel' : 'New channel'}>
      <form onSubmit={onSubmit} style={{ display: 'grid', gap: 12 }}>
        <Input label="Name" required value={name} onChange={(e) => setName(e.target.value)} />
        <Select
          label="Channel type"
          value={channelType}
          onChange={(e) => setChannelType(e.target.value)}
          options={CHANNEL_TYPE_OPTIONS}
        />
        <Input label="URL" value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://…" />
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          <Input
            label="Cost per post"
            value={cost}
            onChange={(e) => setCost(e.target.value)}
            placeholder="0.00"
          />
          <div style={{ display: 'flex', alignItems: 'flex-end', paddingBottom: 10 }}>
            <label style={{ display: 'flex', gap: 8, alignItems: 'center', fontSize: '0.88rem' }}>
              <input
                type="checkbox"
                checked={isActive}
                onChange={(e) => setIsActive(e.target.checked)}
              />
              Active
            </label>
          </div>
        </div>
        <Input label="Notes" value={notes} onChange={(e) => setNotes(e.target.value)} />
        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
          <Button type="button" variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={saving}>
            {editing ? 'Save changes' : 'Create channel'}
          </Button>
        </div>
      </form>
    </Modal>
  )
}

export function SourcingCampaignsPage() {
  const navigate = useNavigate()
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('')
  const [channel, setChannel] = useState('')

  const campaigns = useApi(
    () =>
      sourcesApi.campaigns.list({
        page,
        page_size: 20,
        search: search || undefined,
        status: status ? CAMPAIGN_STATUS_VALUES[status] : undefined,
        channel: channel || undefined,
      }),
    [page, search, status, channel],
    { enabled: true },
  )
  const channels = useApi(() => sourcesApi.channels.list({ page_size: 100 }), [], { enabled: true })

  return (
    <div className="hf-page">
      <PageHeader
        title="Sourcing campaigns"
        subtitle="Launch outreach campaigns across channels and track delivery."
        actions={
          <Button leftIcon={<Plus size={16} />} onClick={() => navigate('/app/sources/campaigns/new')}>
            New campaign
          </Button>
        }
      />
      <Card padding="1rem">
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, alignItems: 'flex-end' }}>
          <div style={{ flex: '1 1 220px', minWidth: 200 }}>
            <Input
              value={search}
              onChange={(e) => {
                setPage(1)
                setSearch(e.target.value)
              }}
              placeholder="Search campaigns…"
            />
          </div>
          <div style={{ minWidth: 150, flex: '0 1 160px' }}>
            <Select
              label="Status"
              value={status}
              onChange={(e) => {
                setPage(1)
                setStatus(e.target.value)
              }}
              options={[{ value: '', label: 'All' }, ...CAMPAIGN_STATUS_OPTIONS]}
            />
          </div>
          <div style={{ minWidth: 160, flex: '0 1 180px' }}>
            <Select
              label="Channel"
              value={channel}
              onChange={(e) => {
                setPage(1)
                setChannel(e.target.value)
              }}
              options={[
                { value: '', label: 'All' },
                ...(channels.data?.results || []).map((c) => ({ value: c.id, label: c.name })),
              ]}
            />
          </div>
          <div style={{ display: 'flex', gap: 8, marginLeft: 'auto' }}>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                setSearch('')
                setStatus('')
                setChannel('')
                setPage(1)
              }}
            >
              Clear
            </Button>
          </div>
        </div>
      </Card>
      <Card padding={0}>
        <DataTable
          loading={campaigns.loading}
          columns={[
            {
              key: 'name',
              header: 'Campaign',
              render: (c: SourcingCampaign) => (
                <div>
                  <Link
                    to={`/app/sources/campaigns/${c.id}`}
                    style={{ fontWeight: 650, textDecoration: 'none' }}
                  >
                    {c.name}
                  </Link>
                  <div className="hf-subtle" style={{ fontSize: '0.75rem' }}>
                    {c.channel_name || '—'}
                    {c.job_title ? ` · ${c.job_title}` : ''}
                  </div>
                </div>
              ),
            },
            {
              key: 'status',
              header: 'Status',
              render: (c: SourcingCampaign) => <Badge status={c.status} />,
            },
            {
              key: 'recipients',
              header: 'Recipients',
              render: (c: SourcingCampaign) => c.recipient_count,
            },
            {
              key: 'budget',
              header: 'Budget',
              render: (c: SourcingCampaign) => formatCurrency(c.budget),
            },
            { key: 'started', header: 'Started', render: (c: SourcingCampaign) => formatDate(c.started_at) },
            { key: 'ended', header: 'Ended', render: (c: SourcingCampaign) => formatDate(c.ended_at) },
          ]}
          rows={campaigns.data?.results || []}
          rowKey={(c) => c.id}
          emptyTitle="No campaigns"
          emptyDescription="Create a sourcing campaign to start outreach."
          onRowClick={(c) => navigate(`/app/sources/campaigns/${c.id}`)}
        />
        {campaigns.data && (
          <Pagination page={page} pageSize={20} total={campaigns.data.count} onChange={setPage} />
        )}
      </Card>
    </div>
  )
}

export function SourcingCampaignFormPage() {
  const { id } = useParams()
  const isEdit = Boolean(id)
  const navigate = useNavigate()
  const { toast } = useToast()
  const [saving, setSaving] = useState(false)
  const [loading, setLoading] = useState(isEdit)
  const channels = useApi(() => sourcesApi.channels.list({ page_size: 100 }), [], { enabled: true })
  const [form, setForm] = useState({
    name: '',
    channel: '',
    goal: '',
    budget: '',
    job: '',
    talent_pool: '',
  })

  function set<K extends keyof typeof form>(key: K, value: (typeof form)[K]) {
    setForm((f) => ({ ...f, [key]: value }))
  }

  useEffect(() => {
    if (!id) return
    setLoading(true)
    sourcesApi.campaigns
      .get(id)
      .then((c) => {
        setForm({
          name: c.name,
          channel: c.channel,
          goal: c.goal || '',
          budget: c.budget || '',
          job: c.job || '',
          talent_pool: c.talent_pool || '',
        })
      })
      .catch((err: unknown) =>
        toast(err instanceof ApiError ? err.message : 'Failed to load campaign', 'error'),
      )
      .finally(() => setLoading(false))
  }, [id, toast])

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setSaving(true)
    const payload = {
      name: form.name,
      channel: form.channel || null,
      goal: form.goal || '',
      budget: form.budget || null,
      job: form.job || null,
      talent_pool: form.talent_pool || null,
    }
    try {
      const saved = isEdit
        ? await sourcesApi.campaigns.update(id!, payload)
        : await sourcesApi.campaigns.create(payload)
      toast(isEdit ? 'Campaign updated' : 'Campaign created', 'success')
      navigate(`/app/sources/campaigns/${saved.id}`)
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
        title={isEdit ? 'Edit campaign' : 'New sourcing campaign'}
        subtitle="Configure the channel, goal, and budget for this outreach campaign."
      />
      <form onSubmit={onSubmit}>
        <Card>
          <div style={{ display: 'grid', gap: 14 }}>
            <Input label="Name" required value={form.name} onChange={(e) => set('name', e.target.value)} />
            <Select
              label="Channel"
              value={form.channel}
              onChange={(e) => set('channel', e.target.value)}
              placeholder="Select channel"
              options={(channels.data?.results || []).map((c) => ({ value: c.id, label: c.name }))}
            />
            <Textarea label="Goal" value={form.goal} onChange={(e) => set('goal', e.target.value)} />
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12 }}>
              <Input
                label="Budget"
                value={form.budget}
                onChange={(e) => set('budget', e.target.value)}
                placeholder="0.00"
              />
              <Input
                label="Job ID (optional)"
                value={form.job}
                onChange={(e) => set('job', e.target.value)}
                placeholder="UUID"
              />
              <Input
                label="Talent pool ID (optional)"
                value={form.talent_pool}
                onChange={(e) => set('talent_pool', e.target.value)}
                placeholder="UUID"
              />
            </div>
            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
              <Button type="button" variant="outline" onClick={() => navigate(-1)}>
                Cancel
              </Button>
              <Button type="submit" loading={saving}>
                {isEdit ? 'Save changes' : 'Create campaign'}
              </Button>
            </div>
          </div>
        </Card>
      </form>
    </div>
  )
}

export function SourcingCampaignDetailPage() {
  const { id = '' } = useParams()
  const navigate = useNavigate()
  const { toast } = useToast()
  const [tab, setTab] = useState('overview')
  const [acting, setActing] = useState(false)
  const [page, setPage] = useState(1)
  const [addOpen, setAddOpen] = useState(false)

  const campaign = useApi(() => sourcesApi.campaigns.get(id), [id], { enabled: Boolean(id) })
  const recipients = useApi(
    () => sourcesApi.recipients.list({ campaign: id, page, page_size: 20 }),
    [id, tab, page],
    { enabled: Boolean(id) && tab === 'recipients' },
  )

  async function runAction(action: () => Promise<unknown>, ok: string) {
    setActing(true)
    try {
      await action()
      toast(ok, 'success')
      campaign.reload()
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Action failed', 'error')
    } finally {
      setActing(false)
    }
  }

  if (campaign.loading) {
    return (
      <div style={{ padding: 64, display: 'grid', placeItems: 'center' }}>
        <Spinner label="Loading campaign…" />
      </div>
    )
  }
  if (campaign.error || !campaign.data) {
    return (
      <EmptyState
        title="Campaign not found"
        description={campaign.error || 'This campaign may have been deleted.'}
        actionLabel="Back to campaigns"
        onAction={() => navigate('/app/sources')}
      />
    )
  }

  const c = campaign.data

  return (
    <div className="hf-page">
      <PageHeader
        title={c.name}
        subtitle={`${c.channel_name || 'No channel'} · ${c.goal || 'No goal'}`}
        breadcrumbs={[{ label: 'Sourcing', to: '/app/sources' }, { label: c.name }]}
        actions={
          <>
            <Badge status={c.status} />
            <Button variant="outline" onClick={() => navigate(`/app/sources/campaigns/${id}/edit`)}>
              Edit
            </Button>
            {c.status === 'draft' && (
              <Button
                loading={acting}
                leftIcon={<Play size={14} />}
                onClick={() => runAction(() => sourcesApi.campaigns.launch(id), 'Campaign launched')}
              >
                Launch
              </Button>
            )}
            {c.status === 'active' && (
              <Button
                variant="outline"
                loading={acting}
                leftIcon={<Pause size={14} />}
                onClick={() => runAction(() => sourcesApi.campaigns.pause(id), 'Campaign paused')}
              >
                Pause
              </Button>
            )}
            {c.status === 'paused' && (
              <Button
                loading={acting}
                leftIcon={<Play size={14} />}
                onClick={() => runAction(() => sourcesApi.campaigns.resume(id), 'Campaign resumed')}
              >
                Resume
              </Button>
            )}
            {['active', 'paused'].includes(c.status) && (
              <Button
                variant="outline"
                loading={acting}
                leftIcon={<Flag size={14} />}
                onClick={() => runAction(() => sourcesApi.campaigns.complete(id), 'Campaign completed')}
              >
                Complete
              </Button>
            )}
            {c.talent_pool && (
              <Button
                variant="outline"
                loading={acting}
                leftIcon={<Users size={14} />}
                onClick={() =>
                  runAction(() => sourcesApi.campaigns.syncRecipients(id), 'Recipients synced')
                }
              >
                Sync recipients
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
          { id: 'recipients', label: 'Recipients', count: recipients.data?.count },
        ]}
      />

      {tab === 'overview' && (
        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 16 }}>
          <Card title="Campaign details">
            <dl style={{ display: 'grid', gap: 10, margin: 0, fontSize: '0.88rem' }}>
              <Row label="Channel" value={c.channel_name || '—'} />
              <Row label="Job" value={c.job_title || '—'} />
              <Row label="Talent pool" value={c.talent_pool_name || '—'} />
              <Row label="Budget" value={formatCurrency(c.budget)} />
              <Row label="Started" value={formatDateTime(c.started_at)} />
              <Row label="Ended" value={formatDateTime(c.ended_at)} />
            </dl>
          </Card>
          <div style={{ display: 'grid', gap: 12 }}>
            <StatCard label="Recipients" value={c.recipient_count} icon={<Mail size={16} />} />
            <StatCard label="Status" value={titleCase(c.status)} icon={<Megaphone size={16} />} />
          </div>
        </div>
      )}

      {tab === 'recipients' && (
        <Card padding={0}>
          <CardHeader
            title="Recipients"
            actions={
              <>
                <Button
                  variant="outline"
                  size="sm"
                  leftIcon={<RotateCw size={14} />}
                  onClick={() =>
                    sourcesApi.recipients
                      .sendAll({ campaign_id: id })
                      .then((res) => toast(`Queued ${res.pending} emails`, 'success'))
                      .then(() => recipients.reload())
                      .catch((err: unknown) =>
                        toast(err instanceof ApiError ? err.message : 'Send failed', 'error'),
                      )
                  }
                >
                  Send all
                </Button>
                <Button size="sm" leftIcon={<Plus size={14} />} onClick={() => setAddOpen(true)}>
                  Add recipient
                </Button>
              </>
            }
          />
          <DataTable
            loading={recipients.loading}
            columns={[
              {
                key: 'email',
                header: 'Recipient',
                render: (r: CampaignRecipient) => (
                  <div>
                    <span style={{ fontWeight: 600 }}>{r.email}</span>
                    {r.candidate_name && (
                      <div className="hf-subtle" style={{ fontSize: '0.75rem' }}>
                        {r.candidate_name}
                      </div>
                    )}
                  </div>
                ),
              },
              { key: 'status', header: 'Status', render: (r: CampaignRecipient) => <Badge status={r.status} /> },
              { key: 'sent', header: 'Sent', render: (r: CampaignRecipient) => formatDateTime(r.sent_at) },
              {
                key: 'actions',
                header: '',
                render: (r: CampaignRecipient) => (
                  <div style={{ display: 'flex', gap: 4 }}>
                    {r.status === 'queued' && (
                      <Button
                        variant="outline"
                        size="sm"
                        leftIcon={<Send size={13} />}
                        onClick={(e) => {
                          e.stopPropagation()
                          sourcesApi.recipients
                            .send(r.id)
                            .then(() => {
                              toast('Email sent', 'success')
                              recipients.reload()
                            })
                            .catch((err: unknown) =>
                              toast(err instanceof ApiError ? err.message : 'Send failed', 'error'),
                            )
                        }}
                      >
                        Send
                      </Button>
                    )}
                    {r.status !== 'queued' && r.status !== 'opted_out' && (
                      <Button
                        variant="ghost"
                        size="sm"
                        leftIcon={<RotateCw size={13} />}
                        onClick={(e) => {
                          e.stopPropagation()
                          sourcesApi.recipients
                            .resend(r.id)
                            .then(() => {
                              toast('Email re-sent', 'success')
                              recipients.reload()
                            })
                            .catch((err: unknown) =>
                              toast(err instanceof ApiError ? err.message : 'Resend failed', 'error'),
                            )
                        }}
                      >
                        Resend
                      </Button>
                    )}
                  </div>
                ),
              },
            ]}
            rows={recipients.data?.results || []}
            rowKey={(r) => r.id}
            emptyTitle="No recipients"
            emptyDescription="Add recipients manually or attach a talent pool and sync."
          />
          {recipients.data && (
            <Pagination page={page} pageSize={20} total={recipients.data.count} onChange={setPage} />
          )}
        </Card>
      )}

      <AddRecipientModal
        open={addOpen}
        campaignId={id}
        onClose={() => setAddOpen(false)}
        onSaved={() => {
          recipients.reload()
          campaign.reload()
          setAddOpen(false)
        }}
      />
    </div>
  )
}

function CardHeader({ title, actions }: { title: string; actions?: ReactNode }) {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: 12,
        padding: '1rem 1.25rem',
        borderBottom: '1px solid var(--hf-border)',
      }}
    >
      <h3 style={{ fontSize: '1.05rem', margin: 0 }}>{title}</h3>
      <div style={{ display: 'flex', gap: 8 }}>{actions}</div>
    </div>
  )
}

function AddRecipientModal({
  open,
  campaignId,
  onClose,
  onSaved,
}: {
  open: boolean
  campaignId: string
  onClose: () => void
  onSaved: () => void
}) {
  const { toast } = useToast()
  const [email, setEmail] = useState('')
  const [candidate, setCandidate] = useState('')
  const [saving, setSaving] = useState(false)

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setSaving(true)
    try {
      await sourcesApi.recipients.create({
        campaign: campaignId,
        email,
        candidate: candidate || null,
      })
      toast('Recipient added', 'success')
      setEmail('')
      setCandidate('')
      onSaved()
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Save failed', 'error')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal open={open} onClose={onClose} title="Add recipient">
      <form onSubmit={onSubmit} style={{ display: 'grid', gap: 12 }}>
        <Input
          label="Email"
          type="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <Input
          label="Candidate ID (optional)"
          value={candidate}
          onChange={(e) => setCandidate(e.target.value)}
          placeholder="UUID"
        />
        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
          <Button type="button" variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={saving}>
            Add recipient
          </Button>
        </div>
      </form>
    </Modal>
  )
}

export function SourceAttributionPage() {
  const [from, setFrom] = useState('')
  const [to, setTo] = useState('')
  const [channel, setChannel] = useState('')
  const [page, setPage] = useState(1)

  const attributions = useApi(
    () =>
      sourcesApi.attributions.list({
        page,
        page_size: 20,
        channel: channel || undefined,
      }),
    [page, channel],
    { enabled: true },
  )
  const stats = useApi(
    () => sourcesApi.attributions.stats({ from: from || undefined, to: to || undefined }),
    [from, to],
    { enabled: true },
  )

  return (
    <div className="hf-page">
      <PageHeader
        title="Source attribution"
        subtitle="See which channels and campaigns drive candidate volume."
        breadcrumbs={[{ label: 'Sourcing', to: '/app/sources' }, { label: 'Attribution' }]}
      />
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
          gap: 12,
        }}
      >
        <StatCard
          label="Total attributions"
          value={stats.data?.total_attributions ?? 0}
          icon={<Users size={16} />}
        />
        <StatCard
          label="Active channels"
          value={stats.data?.channels.length ?? 0}
          icon={<BarChart3 size={16} />}
        />
      </div>
      <Card padding="1rem">
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, alignItems: 'flex-end' }}>
          <div style={{ minWidth: 160, flex: '0 1 180px' }}>
            <Input
              label="From"
              type="date"
              value={from}
              onChange={(e) => setFrom(e.target.value)}
            />
          </div>
          <div style={{ minWidth: 160, flex: '0 1 180px' }}>
            <Input label="To" type="date" value={to} onChange={(e) => setTo(e.target.value)} />
          </div>
          <div style={{ minWidth: 160, flex: '0 1 180px' }}>
            <Input
              label="Channel ID (optional)"
              value={channel}
              onChange={(e) => {
                setPage(1)
                setChannel(e.target.value)
              }}
              placeholder="UUID"
            />
          </div>
          <Button
            variant="ghost"
            size="sm"
            style={{ marginBottom: 4 }}
            onClick={() => {
              setFrom('')
              setTo('')
              setChannel('')
              setPage(1)
            }}
          >
            Clear
          </Button>
        </div>
      </Card>
      <Card title="By channel" subtitle="Attributions aggregated per channel for the selected period.">
        <DataTable
          loading={stats.loading}
          columns={[
            {
              key: 'channel',
              header: 'Channel',
              render: (r) => (
                <div>
                  <span style={{ fontWeight: 600 }}>{r.channel}</span>
                  <div className="hf-subtle" style={{ fontSize: '0.75rem' }}>
                    {channelTypeLabel(r.channel_type)}
                  </div>
                </div>
              ),
            },
            { key: 'attributions', header: 'Attributions', render: (r) => r.attributions },
            { key: 'campaigns', header: 'Campaigns', render: (r) => r.campaigns },
          ]}
          rows={stats.data?.channels || []}
          rowKey={(r) => r.channel}
          emptyTitle="No attribution data"
          emptyDescription="Attributions will appear once candidates are sourced through channels."
        />
      </Card>
      <Card padding={0} title="Recent attributions">
        <DataTable
          loading={attributions.loading}
          columns={[
            {
              key: 'candidate',
              header: 'Candidate',
              render: (a) => a.candidate_name || '—',
            },
            {
              key: 'channel',
              header: 'Channel',
              render: (a) => a.channel_name || '—',
            },
            {
              key: 'campaign',
              header: 'Campaign',
              render: (a) => a.campaign_name || '—',
            },
            { key: 'detail', header: 'Detail', render: (a) => a.source_detail || '—' },
            {
              key: 'utm',
              header: 'UTM',
              render: (a) =>
                [a.utm_source, a.utm_medium, a.utm_campaign].filter(Boolean).join(' / ') || '—',
            },
            { key: 'date', header: 'Date', render: (a) => formatDate(a.attribution_date) },
          ]}
          rows={attributions.data?.results || []}
          rowKey={(a) => a.id}
          emptyTitle="No attributions"
        />
        {attributions.data && (
          <Pagination page={page} pageSize={20} total={attributions.data.count} onChange={setPage} />
        )}
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
