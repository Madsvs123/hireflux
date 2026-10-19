import { useNavigate, useParams } from 'react-router-dom'
import { applicationsApi } from '../../api/pipelines'
import { useApi } from '../../hooks/useApi'
import { PageHeader } from '../../components/layout/PageHeader'
import { Badge, Button, Card, EmptyState, Spinner, Timeline } from '../../components/ui'
import { formatDateTime, titleCase } from '../../utils/format'

export function ApplicationDetailPage() {
  const { id = '' } = useParams()
  const navigate = useNavigate()
  const app = useApi(() => applicationsApi.get(id), [id], { enabled: Boolean(id) })

  if (app.loading) {
    return (
      <div style={{ padding: 64, display: 'grid', placeItems: 'center' }}>
        <Spinner label="Loading application…" />
      </div>
    )
  }

  if (app.error || !app.data) {
    return (
      <EmptyState
        title="Application not found"
        description={app.error || undefined}
        actionLabel="Back to pipeline"
        onAction={() => navigate('/app/pipeline')}
      />
    )
  }

  const a = app.data

  return (
    <div className="hf-page">
      <PageHeader
        title={a.candidate_name}
        subtitle={`${a.job_title} · Applied ${formatDateTime(a.applied_at)}`}
        actions={
          <>
            <Badge status={a.status} />
            <Button variant="outline" onClick={() => navigate(`/app/candidates/${a.candidate}`)}>
              View candidate
            </Button>
            <Button variant="outline" onClick={() => navigate(`/app/jobs/${a.job}`)}>
              View job
            </Button>
          </>
        }
      />

      <div style={{ display: 'grid', gridTemplateColumns: '1.4fr 1fr', gap: 16 }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <Card title="Cover letter">
            <p className="hf-muted" style={{ whiteSpace: 'pre-wrap', lineHeight: 1.55 }}>
              {a.cover_letter || 'No cover letter provided.'}
            </p>
          </Card>
          <Card title="Screening answers">
            {Object.keys(a.answers || {}).length ? (
              <dl style={{ margin: 0, display: 'grid', gap: 10 }}>
                {Object.entries(a.answers).map(([k, v]) => (
                  <div key={k}>
                    <dt className="hf-muted" style={{ fontSize: '0.8rem' }}>
                      {k}
                    </dt>
                    <dd style={{ margin: '4px 0 0', fontWeight: 600 }}>{String(v)}</dd>
                  </div>
                ))}
              </dl>
            ) : (
              <p className="hf-muted">No answers recorded.</p>
            )}
          </Card>
          <Card title="Activity">
            <Timeline
              items={(a.activities || []).map((act) => ({
                id: act.id,
                title: titleCase(act.activity_type),
                description: act.message,
                at: act.created_at,
              }))}
            />
          </Card>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <Card title="Status">
            <dl style={{ margin: 0, display: 'grid', gap: 10, fontSize: '0.88rem' }}>
              <Row label="Stage entered" value={formatDateTime(a.updated_at)} />
              <Row
                label="Relevance"
                value={a.relevance_score != null ? `${Math.round(a.relevance_score)}%` : '—'}
              />
              <Row label="Source" value={a.source || '—'} />
              <Row label="Knockout" value={a.knockout_failed ? 'Failed' : 'Passed'} />
              {a.rejection_reason && <Row label="Rejection" value={a.rejection_reason} />}
            </dl>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 12 }}>
              {(a.tags || []).map((t) => (
                <Badge key={t}>{t}</Badge>
              ))}
            </div>
          </Card>
          <Card title="Stage history">
            <Timeline
              items={(a.stage_history || []).map((h) => ({
                id: h.id,
                title: `${h.from_stage_name || 'Start'} → ${h.to_stage_name}`,
                description: h.note,
                at: h.created_at,
              }))}
            />
          </Card>
        </div>
      </div>
    </div>
  )
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}>
      <dt className="hf-muted">{label}</dt>
      <dd style={{ margin: 0, fontWeight: 600, textAlign: 'right' }}>{value}</dd>
    </div>
  )
}
