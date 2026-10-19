import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { jobsApi } from '../../api/jobs'
import { applicationsApi } from '../../api/pipelines'
import { useApi } from '../../hooks/useApi'
import { PageHeader } from '../../components/layout/PageHeader'
import {
  Badge,
  Button,
  Card,
  DataTable,
  EmptyState,
  Spinner,
  Tabs,
  useToast,
} from '../../components/ui'
import { formatCurrency, formatDate, titleCase } from '../../utils/format'
import { ApiError } from '../../api/http'

export function JobDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { toast } = useToast()
  const [tab, setTab] = useState('overview')
  const job = useApi(() => jobsApi.get(id), [id], { enabled: Boolean(id) })
  const applicants = useApi(
    () => applicationsApi.list({ job: id, page_size: 50 }),
    [id, tab],
    { enabled: Boolean(id) && tab === 'applicants' },
  )
  const [acting, setActing] = useState(false)

  async function runAction(action: () => Promise<unknown>, ok: string) {
    setActing(true)
    try {
      await action()
      toast(ok, 'success')
      job.reload()
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Action failed', 'error')
    } finally {
      setActing(false)
    }
  }

  if (!job.loading) {
    return (
      <div style={{ padding: 64, display: 'grid', placeItems: 'center' }}>
        <Spinner label="Loading job…" />
      </div>
    )
  }

  if (job.error || !job.data) {
    return (
      <EmptyState
        title="Job not found"
        description={job.error || 'This job may have been deleted.'}
        actionLabel="Back to jobs"
        onAction={() => navigate('/app/jobs')}
      />
    )
  }

  const j = job.data

  return (
    <div className="hf-page">
      <PageHeader
        title={j.title}
        subtitle={`${titleCase(j.employment_type)} · ${titleCase(j.experience_level)} · ${titleCase(j.remote_policy)}`}
        actions={
          <>
            <Badge status={j.status} />
            <Button variant="outline" onClick={() => navigate(`/app/jobs/${id}/edit`)}>
              Edit
            </Button>
            {j.status === 'draft' && (
              <Button
                loading={acting}
                onClick={() => runAction(() => jobsApi.publish(id), 'Job published')}
              >
                Publish
              </Button>
            )}
            {j.status === 'draft' && (
              <Button
                variant="secondary"
                loading={acting}
                onClick={() =>
                  runAction(() => jobsApi.submitApproval(id), 'Submitted for approval')
                }
              >
                Submit approval
              </Button>
            )}
            {j.status === 'pending_approval' && (
              <Button
                loading={acting}
                onClick={() => runAction(() => jobsApi.approve(id), 'Job approved')}
              >
                Approve
              </Button>
            )}
            {j.status === 'published' && (
              <Button
                variant="outline"
                loading={acting}
                onClick={() => runAction(() => jobsApi.pause(id), 'Job paused')}
              >
                Pause
              </Button>
            )}
            {['published', 'paused'].includes(j.status) && (
              <Button
                variant="danger"
                loading={acting}
                onClick={() => runAction(() => jobsApi.close(id), 'Job closed')}
              >
                Close
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
          { id: 'questions', label: 'Questions', count: j.screening_questions?.length },
          { id: 'applicants', label: 'Applicants' },
          { id: 'approvals', label: 'Approvals', count: j.approvals?.length },
        ]}
      />

      {tab === 'overview' && (
        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 16 }}>
          <Card title="Description">
            <div style={{ whiteSpace: 'pre-wrap', lineHeight: 1.6 }} className="hf-muted">
              {j.description || 'No description yet.'}
            </div>
            {j.requirements && (
              <>
                <h3 style={{ marginTop: 20, marginBottom: 8 }}>Requirements</h3>
                <div style={{ whiteSpace: 'pre-wrap', lineHeight: 1.6 }} className="hf-muted">
                  {j.requirements}
                </div>
              </>
            )}
            {j.responsibilities && (
              <>
                <h3 style={{ marginTop: 20, marginBottom: 8 }}>Responsibilities</h3>
                <div style={{ whiteSpace: 'pre-wrap', lineHeight: 1.6 }} className="hf-muted">
                  {j.responsibilities}
                </div>
              </>
            )}
          </Card>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <Card title="Details">
              <dl style={{ display: 'grid', gap: 10, margin: 0, fontSize: '0.88rem' }}>
                <Row label="Openings" value={String(j.openings)} />
                <Row
                  label="Salary"
                  value={
                    j.salary_visible
                      ? `${formatCurrency(j.salary_min, j.currency)} – ${formatCurrency(j.salary_max, j.currency)}`
                      : 'Hidden'
                  }
                />
                <Row label="Published" value={formatDate(j.published_at)} />
                <Row label="Closes" value={formatDate(j.closes_at)} />
                <Row label="Career page" value={j.career_page_visible ? 'Visible' : 'Hidden'} />
              </dl>
            </Card>
            <Card title="Skills">
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                {(j.required_skills || []).map((s) => (
                  <Badge key={s} tone="teal">
                    {s}
                  </Badge>
                ))}
                {!j.required_skills?.length && <span className="hf-muted">No skills listed</span>}
              </div>
            </Card>
            <Card title="Recruiters">
              {(j.recruiters || []).map((r) => (
                <div key={r.id} style={{ marginBottom: 8, fontSize: '0.88rem' }}>
                  {r.user_name} {r.is_primary && <Badge tone="info">Primary</Badge>}
                </div>
              ))}
              {!j.recruiters?.length && <span className="hf-muted">No recruiters assigned</span>}
            </Card>
          </div>
        </div>
      )}

      {tab === 'questions' && (
        <Card title="Screening questions">
          {(j.screening_questions || []).length ? (
            <ol style={{ margin: 0, paddingLeft: 18, display: 'flex', flexDirection: 'column', gap: 12 }}>
              {j.screening_questions.map((q) => (
                <li key={q.id}>
                  <div style={{ fontWeight: 600 }}>{q.prompt}</div>
                  <div className="hf-subtle" style={{ fontSize: '0.8rem' }}>
                    {titleCase(q.question_type)}
                    {q.is_required ? ' · Required' : ''}
                    {q.is_knockout ? ' · Knockout' : ''}
                  </div>
                </li>
              ))}
            </ol>
          ) : (
            <EmptyState title="No screening questions" description="Add knockout and screening questions when editing the job." />
          )}
        </Card>
      )}

      {tab === 'applicants' && (
        <Card padding={0} title="Applicants">
          <DataTable
            loading={applicants.loading}
            columns={[
              { key: 'name', header: 'Candidate', render: (a) => a.candidate_name },
              { key: 'stage', header: 'Stage', render: (a) => a.stage_name || titleCase(a.status) },
              {
                key: 'score',
                header: 'Score',
                render: (a) => (a.relevance_score != null ? `${Math.round(a.relevance_score)}%` : '—'),
              },
              { key: 'applied', header: 'Applied', render: (a) => formatDate(a.applied_at) },
            ]}
            rows={applicants.data?.results || []}
            rowKey={(a) => a.id}
            emptyTitle="No applicants"
            onRowClick={(a) => navigate(`/app/pipeline/applications/${a.id}`)}
          />
        </Card>
      )}

      {tab === 'approvals' && (
        <Card title="Approval history">
          {(j.approvals || []).length ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {j.approvals.map((a) => (
                <div
                  key={a.id}
                  style={{
                    padding: 12,
                    borderRadius: 10,
                    border: '1px solid var(--hf-border)',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
                    <Badge status={a.decision || 'pending'} />
                    <span className="hf-subtle" style={{ fontSize: '0.75rem' }}>
                      {formatDate(a.decided_at || a.created_at)}
                    </span>
                  </div>
                  {a.comment && <p className="hf-muted" style={{ marginTop: 8 }}>{a.comment}</p>}
                </div>
              ))}
            </div>
          ) : (
            <EmptyState title="No approvals yet" />
          )}
        </Card>
      )}
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
