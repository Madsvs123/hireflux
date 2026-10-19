import { useState, type FormEvent } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { interviewsApi } from '../../api/interviews'
import { useApi } from '../../hooks/useApi'
import { PageHeader } from '../../components/layout/PageHeader'
import { Badge, Button, Card, EmptyState, Input, Select, Spinner, Textarea, useToast } from '../../components/ui'
import { formatDateTime, titleCase } from '../../utils/format'
import { ApiError } from '../../api/http'

const COMPETENCIES = ['Technical skill', 'Communication', 'Problem solving', 'Culture fit', 'Ownership']

export function InterviewDetailPage() {
  const { id = '' } = useParams()
  const navigate = useNavigate()
  const { toast } = useToast()
  const interview = useApi(() => interviewsApi.get(id), [id], { enabled: Boolean(id) })
  const [ratings, setRatings] = useState<Record<string, number>>(
    Object.fromEntries(COMPETENCIES.map((c) => [c, 3])),
  )
  const [overall, setOverall] = useState(0)
  const [recommendation, setRecommendation] = useState('advance')
  const [comments, setComments] = useState('')
  const [saving, setSaving] = useState(false)

  async function submitScorecard(e: FormEvent) {
    e.preventDefault()
    setSaving(true)
    try {
      await interviewsApi.submitScorecard(id, {
        overall_rating: overall,
        recommendation,
        competencies: COMPETENCIES.map((name) => ({ name, rating: ratings[name] || 3 })),
        comments,
      })
      toast('Scorecard submitted', 'success')
      interview.reload()
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Submit failed', 'error')
    } finally {
      setSaving(false)
    }
  }

  if (interview.loading) {
    return (
      <div style={{ padding: 64, display: 'grid', placeItems: 'center' }}>
        <Spinner />
      </div>
    )
  }

  if (interview.error || !interview.data) {
    return (
      <EmptyState
        title="Interview not found"
        description={interview.error || 'Interviews API may not be available yet.'}
        actionLabel="Back"
        onAction={() => navigate('/app/interviews')}
      />
    )
  }

  const iv = interview.data

  return (
    <div className="hf-page">
      <PageHeader
        title={iv.title || 'Interview'}
        subtitle={`${iv.candidate_name || 'Candidate'} · ${iv.job_title || titleCase(iv.interview_type)}`}
        actions={<Badge status={iv.status} />}
      />
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.2fr', gap: 16 }}>
        <Card title="Details">
          <dl style={{ margin: 0, display: 'grid', gap: 10, fontSize: '0.9rem' }}>
            <Row label="When" value={formatDateTime(iv.scheduled_at)} />
            <Row label="Duration" value={`${iv.duration_minutes || 60} min`} />
            <Row label="Location" value={iv.location || '—'} />
            <Row label="Meeting" value={iv.meeting_url || '—'} />
          </dl>
          {iv.notes && (
            <p className="hf-muted" style={{ marginTop: 16, whiteSpace: 'pre-wrap' }}>
              {iv.notes}
            </p>
          )}
        </Card>
        <Card title="Scorecard">
          {!iv.scorecard?.submitted_at ? (
            <div>
              <p>
                Overall: <strong>{iv.scorecard.overall_rating}/5</strong>
              </p>
              <p className="hf-muted">Recommendation: {titleCase(iv.scorecard.recommendation)}</p>
              <p className="hf-muted" style={{ marginTop: 8 }}>
                {iv.scorecard.comments}
              </p>
            </div>
          ) : (
            <form onSubmit={submitScorecard} style={{ display: 'grid', gap: 12 }}>
              {COMPETENCIES.map((name) => (
                <div key={name} style={{ display: 'grid', gridTemplateColumns: '1fr 80px', gap: 8, alignItems: 'center' }}>
                  <span style={{ fontSize: '0.88rem' }}>{name}</span>
                  <Input
                    type="number"
                    min={1}
                    max={5}
                    value={ratings[name]}
                    onChange={(e) => setRatings((r) => ({ ...r, [name]: Number(e.target.value) }))}
                  />
                </div>
              ))}
              <Input
                label="Overall rating (1-5)"
                type="number"
                min={1}
                max={5}
                value={overall}
                onChange={(e) => setOverall(Number(e.target.value))}
              />
              <Select
                label="Recommendation"
                value={recommendation}
                onChange={(e) => setRecommendation(e.target.value)}
                options={[
                  { value: 'advance', label: 'Advance' },
                  { value: 'hold', label: 'Hold' },
                  { value: 'reject', label: 'Reject' },
                  { value: 'strong_yes', label: 'Strong yes' },
                ]}
              />
              <Textarea label="Comments" value={comments} onChange={(e) => setComments(e.target.value)} />
              <Button type="submit" loading={saving}>
                Submit scorecard
              </Button>
            </form>
          )}
        </Card>
      </div>
    </div>
  )
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}>
      <dt className="hf-muted">{label}</dt>
      <dd style={{ margin: 0, fontWeight: 600, textAlign: 'right', wordBreak: 'break-all' }}>{value}</dd>
    </div>
  )
}
