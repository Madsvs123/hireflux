import { useState, type ReactNode } from 'react'
import { Link, NavLink, Outlet } from 'react-router-dom'
import { portalApi } from '../../api/portal'
import { useApi } from '../../hooks/useApi'
import { useAuth } from '../../hooks/useAuth'
import { Badge, Button, Card, DataTable, EmptyState, Spinner, StatCard, useToast } from '../../components/ui'
import { PageHeader } from '../../components/layout/PageHeader'
import { formatDate, formatDateTime, titleCase } from '../../utils/format'
import { ApiError } from '../../api/http'

function PortalShell({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth()
  const links = [
    { to: '/portal', label: 'Home', end: true },
    { to: '/portal/applications', label: 'Applications' },
    { to: '/portal/interviews', label: 'Interviews' },
    { to: '/portal/assessments', label: 'Assessments' },
    { to: '/portal/offers', label: 'Offers' },
    { to: '/portal/messages', label: 'Messages' },
    { to: '/portal/documents', label: 'Documents' },
  ]
  return (
    <div style={{ minHeight: '100vh' }}>
      <header
        style={{
          height: 64,
          borderBottom: '1px solid var(--hf-border)',
          background: 'var(--hf-surface)',
          backdropFilter: 'blur(10px)',
          display: 'flex',
          alignItems: 'center',
          gap: 16,
          padding: '0 1.25rem',
          position: 'sticky',
          top: 0,
          zIndex: 20,
        }}
      >
        <Link to="/portal" style={{ textDecoration: 'none', color: 'inherit', fontFamily: 'var(--hf-font-display)', fontWeight: 700 }}>
          HireFlux Portal
        </Link>
        <nav style={{ display: 'flex', gap: 4, overflowX: 'auto', flex: 1 }}>
          {links.map((l) => (
            <NavLink
              key={l.to}
              to={l.to}
              end={l.end}
              style={({ isActive }) => ({
                padding: '0.4rem 0.7rem',
                borderRadius: 8,
                textDecoration: 'none',
                fontSize: '0.85rem',
                color: isActive ? 'var(--hf-text-muted)' : 'var(--hf-teal-800)',
                background: isActive ? 'transparent' : 'var(--hf-primary-soft)',
                fontWeight: isActive ? 650 : 500,
                whiteSpace: 'nowrap',
              })}
            >
              {l.label}
            </NavLink>
          ))}
        </nav>
        <span className="hf-muted" style={{ fontSize: '0.8rem' }}>
          {user?.full_name || user?.email}
        </span>
        <Button variant="ghost" size="sm" onClick={() => void logout()}>
          Log out
        </Button>
      </header>
      <main style={{ maxWidth: 1100, margin: '0 auto', padding: '1.5rem 1.25rem 2.5rem' }}>{children}</main>
    </div>
  )
}

export function PortalLayout() {
  return (
    <PortalShell>
      <Outlet />
    </PortalShell>
  )
}

export function PortalHomePage() {
  const home = useApi(() => portalApi.home(), [])
  if (home.loading) {
    return (
      <div style={{ padding: 48, display: 'grid', placeItems: 'center' }}>
        <Spinner />
      </div>
    )
  }
  const d = home.data
  return (
    <div className="hf-page">
      <PageHeader title="Candidate portal" subtitle="Track applications, interviews, assessments, and offers." />
      {home.error && <Card><p className="hf-muted">{home.error}</p></Card>}
      <div className="hf-grid-stats">
        <StatCard label="Applications" value={d?.applications_count ?? '—'} />
        <StatCard label="Upcoming interviews" value={d?.interviews_upcoming ?? '—'} />
        <StatCard label="Assessments due" value={d?.assessments_pending ?? '—'} />
        <StatCard label="Open offers" value={d?.offers_open ?? '—'} />
      </div>
    </div>
  )
}

export function MyApplicationsPage() {
  const apps = useApi(() => portalApi.myApplications({ page_size: 50 }), [])
  return (
    <div className="hf-page">
      <PageHeader title="My applications" />
      <Card padding={0}>
        <DataTable
          loading={apps.loading}
          columns={[
            { key: 'job', header: 'Role', render: (a) => a.job_title },
            { key: 'stage', header: 'Stage', render: (a) => a.stage_name || titleCase(a.status) },
            { key: 'status', header: 'Status', render: (a) => <Badge status={a.status} /> },
            { key: 'applied', header: 'Applied', render: (a) => formatDate(a.applied_at) },
          ]}
          rows={apps.data?.results || []}
          rowKey={(a) => a.id}
          emptyTitle="No applications"
          emptyDescription={apps.error || 'Apply to roles on the career page.'}
        />
      </Card>
    </div>
  )
}

export function MyInterviewsPage() {
  const data = useApi(() => portalApi.myInterviews({ page_size: 50 }), [])
  return (
    <div className="hf-page">
      <PageHeader title="My interviews" />
      <Card padding={0}>
        <DataTable
          loading={data.loading}
          columns={[
            { key: 'title', header: 'Interview', render: (i) => i.title },
            { key: 'job', header: 'Job', render: (i) => i.job_title || '—' },
            { key: 'when', header: 'When', render: (i) => formatDateTime(i.scheduled_at) },
            { key: 'status', header: 'Status', render: (i) => <Badge status={i.status} /> },
          ]}
          rows={data.data?.results || []}
          rowKey={(i) => i.id}
          emptyTitle="No interviews"
          emptyDescription={data.error || undefined}
        />
      </Card>
    </div>
  )
}

export function MyAssessmentsPage() {
  const data = useApi(() => portalApi.myAssessments({ page_size: 50 }), [])
  return (
    <div className="hf-page">
      <PageHeader title="My assessments" />
      <Card padding={0}>
        <DataTable
          loading={data.loading}
          columns={[
            { key: 'template', header: 'Assessment', render: (a) => a.template_name || a.template },
            { key: 'job', header: 'Job', render: (a) => a.job_title || '—' },
            { key: 'due', header: 'Due', render: (a) => formatDate(a.due_at) },
            { key: 'status', header: 'Status', render: (a) => <Badge status={a.status} /> },
          ]}
          rows={data.data?.results || []}
          rowKey={(a) => a.id}
          emptyTitle="No assessments"
          emptyDescription={data.error || undefined}
        />
      </Card>
    </div>
  )
}

export function MyOffersPage() {
  const { toast } = useToast()
  const data = useApi(() => portalApi.myOffers({ page_size: 50 }), [])

  async function respond(id: string, action: 'accept' | 'decline') {
    try {
      await portalApi.respondOffer(id, action)
      toast(action === 'accept' ? 'Offer accepted' : 'Offer declined', 'success')
      data.reload()
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Failed', 'error')
    }
  }

  return (
    <div className="hf-page">
      <PageHeader title="My offers" />
      <Card padding={0}>
        <DataTable
          loading={data.loading}
          columns={[
            { key: 'job', header: 'Role', render: (o) => o.job_title || '—' },
            { key: 'salary', header: 'Salary', render: (o) => `${o.salary} ${o.currency}` },
            { key: 'status', header: 'Status', render: (o) => <Badge status={o.status} /> },
            {
              key: 'actions',
              header: '',
              render: (o) =>
                o.status === 'sent' || o.status === 'pending' ? (
                  <div style={{ display: 'flex', gap: 6 }}>
                    <Button size="sm" onClick={() => void respond(o.id, 'accept')}>
                      Accept
                    </Button>
                    <Button size="sm" variant="outline" onClick={() => void respond(o.id, 'decline')}>
                      Decline
                    </Button>
                  </div>
                ) : null,
            },
          ]}
          rows={data.data?.results || []}
          rowKey={(o) => o.id}
          emptyTitle="No offers"
          emptyDescription={data.error || undefined}
        />
      </Card>
    </div>
  )
}

export function PortalMessagesPage() {
  const threads = useApi(() => portalApi.messages({ page_size: 50 }), [])
  return (
    <div className="hf-page">
      <PageHeader title="Messages" />
      <Card>
        {(threads.data?.results || []).map((t) => (
          <div key={t.id} style={{ padding: '0.75rem 0', borderBottom: '1px solid var(--hf-border)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <strong>{t.subject}</strong>
              {t.unread_count > 0 && <Badge tone="info">{t.unread_count}</Badge>}
            </div>
            <p className="hf-muted" style={{ fontSize: '0.85rem', marginTop: 4 }}>
              {t.last_message || 'No messages yet'}
            </p>
          </div>
        ))}
        {!threads.loading && !threads.data?.results?.length && (
          <EmptyState title="No messages" description={threads.error || undefined} />
        )}
      </Card>
    </div>
  )
}

export function PortalDocumentsPage() {
  const docs = useApi(() => portalApi.documents({ page_size: 50 }), [])
  const { toast } = useToast()
  const [uploading, setUploading] = useState(false

  async function onUpload(file: File) {
    setUploading(true)
    try {
      const form = new FormData()
      form.append('file', file)
      form.append('title', file.name)
      form.append('doc_type', 'resume')
      await portalApi.uploadDocument(form)
      toast('Document uploaded', 'success')
      docs.reload()
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Upload failed', 'error')
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="hf-page">
      <PageHeader
        title="Documents"
        actions={
          <>
            <Button loading={uploading} onClick={() => document.getElementById('portal-doc')?.click()}>
              Upload
            </Button>
            <input
              id="portal-doc"
              type="file"
              hidden
              onChange={(e) => {
                const f = e.target.files?.[0]
                if (f) void onUpload(f)
              }}
            />
          </>
        }
      />
      <Card padding={0}>
        <DataTable
          loading={docs.loading}
          columns={[
            { key: 'title', header: 'Document', render: (d) => d.title || d.file_name },
            { key: 'type', header: 'Type', render: (d) => d.doc_type },
            { key: 'status', header: 'Parse', render: (d) => d.parse_status },
            { key: 'date', header: 'Uploaded', render: (d) => formatDate(d.created_at) },
          ]}
          rows={docs.data?.results || []}
          rowKey={(d) => d.id}
          emptyTitle="No documents"
          emptyDescription={docs.error || 'Upload your resume and supporting files.'}
        />
      </Card>
    </div>
  )
}
