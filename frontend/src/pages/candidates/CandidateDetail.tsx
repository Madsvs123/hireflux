import { useState, type FormEvent } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { candidatesApi } from '../../api/candidates'
import { screeningApi } from '../../api/screening'
import { applicationsApi } from '../../api/pipelines'
import { useApi } from '../../hooks/useApi'
import { PageHeader } from '../../components/layout/PageHeader'
import {
  Avatar,
  Badge,
  Button,
  Card,
  EmptyState,
  Spinner,
  Tabs,
  Textarea,
  Timeline,
  useToast,
} from '../../components/ui'
import { formatDate, formatRelative } from '../../utils/format'
import { ApiError } from '../../api/http'

export function CandidateDetailPage() {
  const { id = '' } = useParams()
  const navigate = useNavigate()
  const { toast } = useToast()
  const [tab, setTab] = useState('profile')
  const [note, setNote] = useState('')
  const [savingNote, setSavingNote] = useState(false)
  const candidate = useApi(() => candidatesApi.get(id), [id], { enabled: Boolean(id) })
  const apps = useApi(() => applicationsApi.list({ job: id, page_size: 20 }), [id])
  const matches = useApi(() => screeningApi.listMatches({ candidate: id, page_size: 20 }), [id, tab], {
    enabled: tab === 'matches',
  })

  async function addNote(e: FormEvent) {
    e.preventDefault()
    if (!note.trim()) return
    setSavingNote(true)
    try {
      await candidatesApi.addNote(id, { body: note })
      setNote('')
      toast('Note added', 'success')
      candidate.reload()
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Failed to add note', 'error')
    } finally {
      setSavingNote(false)
    }
  }

  if (candidate.loading) {
    return (
      <div style={{ padding: 64, display: 'grid', placeItems: 'center' }}>
        <Spinner label="Loading candidate…" />
      </div>
    )
  }

  if (candidate.error || !candidate.data) {
    return (
      <EmptyState
        title="Candidate not found"
        description={candidate.error || undefined}
        actionLabel="Back"
        onAction={() => navigate('/app/candidates')}
      />
    )
  }

  const c = candidate.data

  return (
    <div className="hf-page">
      <PageHeader
        title={c.full_name || c.name}
        subtitle={c.headline || c.email}
        actions={
          <>
            {c.do_not_hire && <Badge tone="danger">Do not hire</Badge>}
            {c.is_talent_pool && <Badge tone="teal">Talent pool</Badge>}
            <Button variant="outline" onClick={() => navigate('/app/pipeline')}>
              View pipeline
            </Button>
          </>
        }
      />

      <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
        <Avatar name={c.full_name} size={64} />
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
          {(c.skills || []).slice(0, 8).map((s) => (
            <Badge key={s} tone="teal">
              {s}
            </Badge>
          ))}
        </div>
      </div>

      <Tabs
        value={tab}
        onChange={setTab}
        items={[
          { id: 'profile', label: 'Profile' },
          { id: 'experience', label: 'Experience' },
          { id: 'docs', label: 'Documents', count: c.documents?.length },
          { id: 'notes', label: 'Notes', count: c.notes?.length },
          { id: 'matches', label: 'Matches' },
          { id: 'activity', label: 'Activity' },
        ]}
      />

      {tab === 'profile' && (
        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 16 }}>
          <Card title="Summary">
            <p className="hf-muted" style={{ whiteSpace: 'pre-wrap', lineHeight: 1.6 }}>
              {c.summary || 'No summary yet.'}
            </p>
          </Card>
          <Card title="Contact">
            <dl style={{ margin: 0, display: 'grid', gap: 10, fontSize: '0.88rem' }}>
              <Info label="Email" value={c.email} /
              <Info label="Phone" value={c.phone || '—'} />
              <Info label="Location" value={c.location || '—'} />
              <Info label="Source" value={c.source || '—'} />
              <Info label="Experience" value={c.years_experience != null ? `${c.years_experience} yrs` : '—'} />
              <Info label="LinkedIn" value={c.linkedin_url || '—'} />
            </dl>
          </Card>
        </div>
      )}

      {tab === 'experience' && (
        <div style={{ display: 'grid', gap: 16 }}>
          <Card title="Work experience">
            {(c.experience || []).length ? (
              c.experience.map((exp) => (
                <div key={exp.id} style={{ padding: '0.75rem 0', borderBottom: '1px solid var(--hf-border)' }}>
                  <div style={{ fontWeight: 650 }}>
                    {exp.title} · {exp.company}
                  </div>
                  <div className="hf-subtle" style={{ fontSize: '0.8rem' }}>
                    {formatDate(exp.start_date)} – {exp.is_current ? 'Present' : formatDate(exp.end_date)}
                  </div>
                  {exp.description && (
                    <p className="hf-muted" style={{ marginTop: 6, fontSize: '0.88rem', whiteSpace: 'pre-wrap' }}>
                      {exp.description}
                    </p>
                  )}
                </div>
              ))
            ) : (
              <EmptyState title="No experience listed" />
            )}
          </Card>
          <Card title="Education">
            {(c.education || []).length ? (
              c.education.map((ed) => (
                <div key={ed.id} style={{ padding: '0.65rem 0', borderBottom: '1px solid var(--hf-border)' }}>
                  <div style={{ fontWeight: 650 }}>
                    {ed.degree} · {ed.institution}
                  </div>
                  <div className="hf-subtle" style={{ fontSize: '0.8rem' }}>
                    {ed.field_of_study}
                  </div>
                </div>
              ))
            ) : (
              <EmptyState title="No education listed" />
            )}
          </Card>
        </div>
      )}

      {tab === 'docs' && (
        <Card title="Documents">
          {(c.documents || []).length ? (
            c.documents.map((d) => (
              <div
                key={d.id}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  padding: '0.65rem 0',
                  borderBottom: '1px solid var(--hf-border)',
                }}
              >
                <div>
                  <div style={{ fontWeight: 600 }}>{d.title || d.file_name}</div>
                  <div className="hf-subtle" style={{ fontSize: '0.75rem' }}>
                    {d.doc_type} · {d.parse_status}
                  </div>
                </div>
                {d.is_primary && <Badge tone="info">Primary</Badge>}
              </div>
            ))
          ) : (
            <EmptyState title="No documents" description="Resumes and files will appear here." />
          )}
        </Card>
      )}

      {tab === 'notes' && (
        <Card title="Notes">
          <form onSubmit={addNote} style={{ display: 'grid', gap: 10, marginBottom: 20 }}>
            <Textarea
              label="Add a note"
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="Share context for the hiring team…"
            />
            <div>
              <Button type="submit" loading={savingNote} disabled={!note.trim()}>
                Save note
              </Button>
            </div>
          </form>
          {(c.notes || []).map((n) => (
            <div key={n.id} style={{ padding: '0.75rem 0', borderTop: '1px solid var(--hf-border)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
                <strong style={{ fontSize: '0.85rem' }}>{n.author_email || 'Team'}</strong>
                <span className="hf-subtle" style={{ fontSize: '0.75rem' }}>
                  {formatRelative(n.created_at)}
                </span>
              </div>
              <p className="hf-muted" style={{ marginTop: 6, whiteSpace: 'pre-wrap' }}>
                {n.body}
              </p>
            </div>
          ))}
        </Card>
      )}

      {tab === 'matches' && (
        <Card title="Job matches">
          {matches.error ? (
            <p className="hf-muted">Matching API unavailable: {matches.error}</p>
          ) : matches.loading ? (
            <Spinner />
          ) : (matches.data?.results || []).length ? (
            matches.data!.results.map((m) => (
              <div key={m.id} style={{ display: 'flex', justifyContent: 'space-between', padding: '0.65rem 0' }}>
                <span>{m.job_title || m.job}</span>
                <Badge tone="teal">{Math.round(m.score)}% match</Badge>
              </div>
            ))
          ) : (
            <EmptyState title="No matches yet" />
          )}
        </Card>
      )}

      {tab === 'activity' && (
        <Card title="Applications & activity">
          <Timeline
            items={(apps.data?.results || []).map((a) => ({
              id: a.id,
              title: `Applied to ${a.job_title}`,
              description: a.stage_name || a.status,
              at: a.applied_at,
            }))}
          />
        </Card>
      )}
    </div>
  )
}

function Info({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}>
      <dt className="hf-muted">{label}</dt>
      <dd style={{ margin: 0, fontWeight: 600, textAlign: 'right', wordBreak: 'break-all' }}>{value}</dd>
    </div>
  )
}
