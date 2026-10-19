import { useState, type FormEvent } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { assessmentsApi } from '../../api/assessments'
import { useApi } from '../../hooks/useApi'
import { PageHeader } from '../../components/layout/PageHeader'
import {
  Badge,
  Button,
  Card,
  DataTable,
  EmptyState,
  Input,
  Modal,
  Pagination,
  Spinner,
  Tabs,
  Textarea,
  useToast,
} from '../../components/ui'
import { formatDate, titleCase } from '../../utils/format'
import { ApiError } from '../../api/http'

export function AssessmentListPage() {
  const navigate = useNavigate()
  const [tab, setTab] = useState('assignments')
  const [page, setPage] = useState(1)
  const [builderOpen, setBuilderOpen] = useState(false)
  const assignments = useApi(() => assessmentsApi.listAssignments({ page, page_size: 20 }), [page, tab], {
    enabled: tab === 'assignments',
  })
  const templates = useApi(() => assessmentsApi.listTemplates({ page_size: 50 }), [tab], {
    enabled: tab === 'templates',
  })

  return (
    <div className="hf-page">
      <PageHeader
        title="Assessments"
        subtitle="Build templates and track candidate assignments."
        actions={
          <Button onClick={() => setBuilderOpen(true)}>New template</Button>
        }
      />
      <Tabs
        value={tab}
        onChange={setTab}
        items={[
          { id: 'assignments', label: 'Assignments' },
          { id: 'templates', label: 'Templates', count: templates.data?.count },
        ]}
      />
      {tab === 'assignments' && (
        <Card padding={0}>
          {(assignments.error || templates.error) && (
            <p style={{ padding: 16, color: 'var(--hf-text-muted)' }}>
              {assignments.error || 'Assessments API may not be available yet.'}
            </p>
          )}
          <DataTable
            loading={assignments.loading}
            columns={[
              { key: 'candidate', header: 'Candidate', render: (a) => a.candidate_name || '—' },
              { key: 'template', header: 'Template', render: (a) => a.template_name || a.template },
              { key: 'job', header: 'Job', render: (a) => a.job_title || '—' },
              { key: 'status', header: 'Status', render: (a) => <Badge status={a.status} /> },
              {
                key: 'score',
                header: 'Score',
                render: (a) => (a.score != null ? String(a.score) : '—'),
              },
              { key: 'due', header: 'Due', render: (a) => formatDate(a.due_at) },
            ]}
            rows={assignments.data?.results || []}
            rowKey={(a) => a.id}
            emptyTitle="No assignments"
            onRowClick={(a) => navigate(`/app/assessments/${a.id}`)}
          />
          {assignments.data && (
            <Pagination page={page} pageSize={20} total={assignments.data.count} onChange={setPage} />
          )}
        </Card>
      )}
      {tab === 'templates' && (
        <Card padding={0}>
          <DataTable
            loading={templates.loading}
            columns={[
              { key: 'name', header: 'Name', render: (t) => t.name },
              { key: 'type', header: 'Type', render: (t) => titleCase(t.assessment_type) },
              { key: 'duration', header: 'Duration', render: (t) => `${t.duration_minutes} min` },
              {
                key: 'questions',
                header: 'Questions',
                render: (t) => String(t.questions?.length || 0),
              },
              {
                key: 'active',
                header: 'Active',
                render: (t) => <Badge tone={t.is_active ? 'success' : 'neutral'}>{t.is_active ? 'Yes' : 'No'}</Badge>,
              },
            ]}
            rows={templates.data?.results || []}
            rowKey={(t) => t.id}
            emptyTitle="No templates"
            emptyDescription="Create an assessment template to assign to candidates."
          />
        </Card>
      )}
      <TemplateBuilderModal open={builderOpen} onClose={() => setBuilderOpen(false)} onCreated={templates.reload} />
    </div>
  )
}

function TemplateBuilderModal({
  open,
  onClose,
  onCreated,
}: {
  open: boolean
  onClose: () => void
  onCreated: () => void
}) {
  const { toast } = useToast()
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [prompt, setPrompt] = useState('')
  const [loading, setLoading] = useState(false)

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setLoading(true)
    try {
      await assessmentsApi.createTemplate({
        name,
        description,
        assessment_type: 'custom',
        duration_minutes: 45,
        questions: prompt ? [{ prompt, question_type: 'text' }] : [],
        is_active: true,
      })
      toast('Template created', 'success')
      onCreated()
      onClose()
      setName('')
      setDescription('')
      setPrompt('')
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Create failed', 'error')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Modal open={open} onClose={onClose} title="Assessment template builder">
      <form onSubmit={onSubmit} style={{ display: 'grid', gap: 12 }}>
        <Input label="Name" required value={name} onChange={(e) => setName(e.target.value)} />
        <Textarea label="Description" value={description} onChange={(e) => setDescription(e.target.value)} />
        <Textarea label="First question" value={prompt} onChange={(e) => setName(e.target.value)} />
        <Button type="submit" loading={loading}>
          Create template
        </Button>
      </form>
    </Modal>
  )
}

export function AssessmentDetailPage() {
  const { id = '' } = useParams()
  const navigate = useNavigate()
  const { toast } = useToast()
  const assignment = useApi(() => assessmentsApi.getAssignment(id), [id], { enabled: Boolean(id) })
  const [score, setScore] = useState('')
  const [saving, setSaving] = useState(false)

  async function saveScore() {
    setSaving(true)
    try {
      await assessmentsApi.score(id, { score: Number(score) })
      toast('Score saved', 'success')
      assignment.reload()
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Failed', 'error')
    } finally {
      setSaving(false)
    }
  }

  if (assignment.loading) {
    return (
      <div style={{ padding: 64, display: 'grid', placeItems: 'center' }}>
        <Spinner />
      </div>
    )
  }
  if (assignment.error || !assignment.data) {
    return (
      <EmptyState
        title="Assignment not found"
        description={assignment.error || undefined}
        actionLabel="Back"
        onAction={() => navigate('/app/assessments')}
      />
    )
  }
  const a = assignment.data
  return (
    <div className="hf-page">
      <PageHeader
        title={a.template_name || 'Assessment'}
        subtitle={`${a.candidate_name || 'Candidate'} · ${a.job_title || ''}`}
        actions={<Badge status={a.status} />}
      />
      <Card title="Scoring">
        <p className="hf-muted">Current score: {a.score ?? '—'}</p>
        <div style={{ display: 'flex', gap: 8, marginTop: 12, maxWidth: 280 }}>
          <Input type="number" value={score} onChange={(e) => setScore(e.target.value)} placeholder="Score" />
          <Button loading={saving} onClick={() => void saveScore()}>
            Save
          </Button>
        </div>
      </Card>
    </div>
  )
}
