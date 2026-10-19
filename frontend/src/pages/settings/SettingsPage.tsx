import { useEffect, useState, type FormEvent } from 'react'
import {
  departmentsApi,
  hiringTeamsApi,
  officesApi,
  organizationsApi,
} from '../../api/organizations'
import { invitationsApi, membersApi, rolesApi } from '../../api/auth'
import { useApi } from '../../hooks/useApi'
import { useAuth } from '../../hooks/useAuth'
import { PageHeader } from '../../components/layout/PageHeader'
import {
  Badge,
  Button,
  Card,
  DataTable,
  Input,
  Modal,
  Select,
  Tabs,
  Textarea,
  useToast,
} from '../../components/ui'
import { formatDate } from '../../utils/format'
import { ApiError } from '../../api/http'

export function SettingsPage() {
  const [tab, setTab] = useState('org')
  const { orgId } = useAuth()
  const org = useApi(() => (orgId ? organizationsApi.get(orgId) : Promise.reject(new Error('No org'))), [orgId], {
    enabled: Boolean(orgId),
  })
  const departments = useApi(() => departmentsApi.list({ page_size: 100 }), [tab], { enabled: tab === 'departments' })
  const offices = useApi(() => officesApi.list({ page_size: 100 }), [tab], { enabled: tab === 'offices' })
  const teams = useApi(() => hiringTeamsApi.list({ page_size: 100 }), [tab], { enabled: tab === 'teams' })
  const roles = useApi(() => rolesApi.list({ page_size: 100 }), [tab], { enabled: tab === 'roles' })
  const members = useApi(() => membersApi.list({ page_size: 100 }), [tab], { enabled: tab === 'members' })
  const invites = useApi(() => invitationsApi.list({ page_size: 100 }), [tab], { enabled: tab === 'invites' })
  const { toast } = useToast()
  const [inviteOpen, setInviteOpen] = useState(false)

  const [orgForm, setOrgForm] = useState({ name: '', website: '', industry: '', size: '' })

  useEffect(() => {
    if (!org.data) return
    setOrgForm({
      name: org.data.name,
      website: org.data.website || '',
      industry: org.data.industry || '',
      size: org.data.size || '',
    })
  }, [org.data])

  async function saveOrg(e: FormEvent) {
    e.preventDefault()
    if (!orgId) return
    try {
      await organizationsApi.update(orgForm.name, orgForm)
      toast('Organization updated', 'success')
      org.reload()
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Update failed', 'error')
    }
  }

  return (
    <div className="hf-page">
      <PageHeader title="Settings" subtitle="Organization profile, structure, roles, and team access." />
      <Tabs
        value={tab}
        onChange={setTab}
        items={[
          { id: 'org', label: 'Organization' },
          { id: 'departments', label: 'Departments' },
          { id: 'offices', label: 'Offices' },
          { id: 'teams', label: 'Teams' },
          { id: 'roles', label: 'Roles' },
          { id: 'members', label: 'Members' },
          { id: 'invites', label: 'Invites' },
        ]}
      />

      {tab === 'org' && (
        <Card title="Organization profile">
          <form onSubmit={saveOrg} style={{ display: 'grid', gap: 12, maxWidth: 520 }}>
            <Input label="Name" value={orgForm.name} onChange={(e) => setOrgForm({ ...orgForm, name: e.target.value })} />
            <Input label="Website" value={orgForm.website} onChange={(e) => setOrgForm({ ...orgForm, industry: e.target.value })} />
            <Input label="Industry" value={orgForm.industry} onChange={(e) => setOrgForm({ ...orgForm, industry: e.target.value })} />
            <Input label="Size" value={orgForm.size} onChange={(e) => setOrgForm({ ...orgForm, size: e.target.value })} />
            <Button type="submit">Save changes</Button>
          </form>
        </Card>
      )}

      {tab === 'departments' && (
        <SimpleCrudList
          title="Departments"
          loading={departments.loading}
          rows={(departments.data?.results || []).map((d) => ({ id: d.id, name: d.name, meta: d.parent_name || '—' }))}
          onCreate={async (name) => {
            await departmentsApi.create({ name, description: '', is_active: true })
            departments.reload()
          }}
        />
      )}

      {tab === 'offices' && (
        <SimpleCrudList
          title="Offices"
          loading={offices.loading}
          rows={(offices.data?.results || []).map((o) => ({
            id: o.id,
            name: o.name,
            meta: [o.city, o.country].filter(Boolean).join(', ') || '—',
          }))}
          onCreate={async (name) => {
            await officesApi.create({
              name,
              address_line1: '',
              address_line2: '',
              city: '',
              state: '',
              postal_code: '',
              country: '',
              timezone: 'UTC',
              is_headquarters: false,
              is_active: true,
            })
            offices.reload()
          }}
        />
      )}

      {tab === 'teams' && (
        <SimpleCrudList
          title="Hiring teams"
          loading={teams.loading}
          rows={(teams.data?.results || []).map((t) => ({
            id: t.id,
            name: t.name,
            meta: `${t.members?.length || 0} members`,
          }))}
          onCreate={async (name) => {
            await hiringTeamsApi.create({ name, description: '', is_active: true })
            teams.reload()
          }}
        />
      )}

      {tab === 'roles' && (
        <Card padding={0} title="Roles">
          <DataTable
            loading={roles.loading}
            columns={[
              { key: 'name', header: 'Role', render: (r) => r.name },
              { key: 'slug', header: 'Slug', render: (r) => r.slug },
              {
                key: 'perms',
                header: 'Permissions',
                render: (r) => String(r.permissions?.length || 0),
              },
              {
                key: 'system',
                header: 'System',
                render: (r) => (r.is_system ? <Badge tone="info">System</Badge> : '—'),
              },
            ]}
            rows={roles.data?.results || []}
            rowKey={(r) => r.id}
            emptyTitle="No roles"
          />
        </Card>
      )}

      {tab === 'members' && (
        <Card padding={0} title="Members">
          <DataTable
            loading={members.loading}
            columns={[
              {
                key: 'user',
                header: 'Member',
                render: (m) => m.user?.full_name || m.user?.email,
              },
              { key: 'role', header: 'Role', render: (m) => m.role?.name || (m.is_owner ? 'Owner' : '—') },
              { key: 'title', header: 'Title', render: (m) => m.title || '—' },
              {
                key: 'active',
                header: 'Status',
                render: (m) => <Badge tone={m.is_active ? 'success' : 'neutral'}>{m.is_active ? 'Active' : 'Inactive'}</Badge>,
              },
            ]}
            rows={members.data?.results || []}
            rowKey={(m) => m.id}
            emptyTitle="No members"
          />
        </Card>
      )}

      {tab === 'invites' && (
        <Card
          title="Invitations"
          actions={<Button size="sm" onClick={() => setInviteOpen(true)}>Invite</Button>}
          padding={0}
        >
          <DataTable
            loading={invites.loading}
            columns={[
              { key: 'email', header: 'Email', render: (i) => i.email },
              { key: 'role', header: 'Role', render: (i) => i.role?.name || '—' },
              { key: 'status', header: 'Status', render: (i) => <Badge status={i.status} /> },
              { key: 'expires', header: 'Expires', render: (i) => formatDate(i.expires_at) },
            ]}
            rows={invites.data?.results || []}
            rowKey={(i) => i.id}
            emptyTitle="No invitations"
          />
        </Card>
      )}

      <InviteModal
        open={inviteOpen}
        onClose={() => setInviteOpen(false)}
        roles={roles.data?.results || []}
        onCreated={() => {
          setInviteOpen(false)
          invites.reload()
          toast('Invitation sent', 'success')
        }}
      />
    </div>
  )
}

function SimpleCrudList({
  title,
  rows,
  loading,
  onCreate,
}: {
  title: string
  rows: Array<{ id: string; name: string; meta: string }>
  loading: boolean
  onCreate: (name: string) => Promise<void>
}) {
  const [name, setName] = useState('')
  const [saving, setSaving] = useState(false)
  const { toast } = useToast()

  async function submit(e: FormEvent) {
    e.preventDefault()
    if (!name.trim()) return
    setSaving(true)
    try {
      await onCreate(name.trim())
      setName('')
      toast('Created', 'success')
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Failed', 'error')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Card title={title}>
      <form onSubmit={submit} style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
        <Input placeholder={`New ${title.slice(0, -1).toLowerCase()} name`} value={name} onChange={(e) => setName(e.target.value)} />
        <Button type="submit" loading={saving}>
          Add
        </Button>
      </form>
      <DataTable
        loading={loading}
        columns={[
          { key: 'name', header: 'Name', render: (r) => r.name },
          { key: 'meta', header: 'Details', render: (r) => r.meta },
        ]}
        rows={rows}
        rowKey={(r) => r.id}
        emptyTitle={`No ${title.toLowerCase()}`}
      />
    </Card>
  )
}

function InviteModal({
  open,
  onClose,
  roles,
  onCreated,
}: {
  open: boolean
  onClose: () => void
  roles: Array<{ id: string; name: string }>
  onCreated: () => void
}) {
  const [email, setEmail] = useState('')
  const [roleId, setRoleId] = useState('')
  const [message, setMessage] = useState('')
  const [loading, setLoading] = useState(false)
  const { toast } = useToast()

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setLoading(true)
    try {
      await invitationsApi.create({ email, role_id: roleId || null, message })
      onCreated()
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Invite failed', 'error')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Modal open={open} onClose={onClose} title="Invite teammate">
      <form onSubmit={onSubmit} style={{ display: 'grid', gap: 12 }}>
        <Input label="Email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
        <Select
          label="Role"
          value={roleId}
          onChange={(e) => setRoleId(e.target.value)}
          placeholder="Default"
          options={roles.map((r) => ({ value: r.id, label: r.name }))}
        />
        <Textarea label="Message" value={message} onChange={(e) => setMessage(e.target.value)} />
        <Button type="submit" loading={loading}>
          Send invite
        </Button>
      </form>
    </Modal>
  )
}
