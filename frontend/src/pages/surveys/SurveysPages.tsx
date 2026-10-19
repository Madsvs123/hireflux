/**
 * Surveys pages.
 *
 * Exported components and suggested routes (wire into App.tsx):
 *   - SurveyTemplatesPage      -> /app/surveys/templates
 *   - SurveyTemplateFormPage   -> /app/surveys/templates/new, /app/surveys/templates/:id/edit
 *   - SurveyTemplateDetailPage -> /app/surveys/templates/:id
 *   - SurveyInstancesPage      -> /app/surveys/instances
 *   - SurveyInstanceDetailPage -> /app/surveys/instances/:id
 *   - SurveyAnalyticsPage      -> /app/surveys/analytics
 */
import { useEffect, useState, type FormEvent, type ReactNode } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import {
  BarChart3,
  BellRing,
  Copy,
  Mail,
  Pencil,
  Plus,
  Send,
  Trash2,
  XCircle,
} from 'lucide-react'
import {
  surveysApi,
  type SurveyInstance,
  type SurveyQuestion,
  type SurveyTemplate,
} from '../../api/surveys'
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
  Textarea,
  useToast,
} from '../../components/ui'
import { formatDate, formatDateTime, titleCase } from '../../utils/format'
import { ApiError } from '../../api/http'

// NOTE: the shared <Select> emits option labels as values, so options carry
// display labels and are mapped back to API values on submit.
const SURVEY_TYPE_OPTIONS = [
  { value: 'Candidate Experience', label: 'Candidate Experience' },
  { value: 'Onboarding', label: 'Onboarding' },
  { value: 'EEO', label: 'EEO' },
  { value: 'Internal', label: 'Internal' },
]
const SURVEY_TYPE_VALUES: Record<string, string> = {
  'Candidate Experience': 'candidate_experience',
  Onboarding: 'onboarding',
  EEO: 'eeo',
  Internal: 'internal',
}

const QUESTION_TYPE_OPTIONS = [
  { value: 'Rating', label: 'Rating' },
  { value: 'Text', label: 'Text' },
  { value: 'Choice', label: 'Choice' },
  { value: 'Boolean', label: 'Boolean' },
]
const QUESTION_TYPE_VALUES: Record<string, string> = {
  Rating: 'rating',
  Text: 'text',
  Choice: 'choice',
  Boolean: 'boolean',
}

const INSTANCE_STATUS_OPTIONS = [
  { value: 'Draft', label: 'Draft' },
  { value: 'Sent', label: 'Sent' },
  { value: 'Partially Completed', label: 'Partially Completed' },
  { value: 'Completed', label: 'Completed' },
  { value: 'Expired', label: 'Expired' },
]
const INSTANCE_STATUS_VALUES: Record<string, string> = {
  Draft: 'draft',
  Sent: 'sent',
  'Partially Completed': 'partially_completed',
  Completed: 'completed',
  Expired: 'expired',
}

function surveyTypeLabel(value?: string) {
  if (!value) return ''
  return SURVEY_TYPE_OPTIONS.find((o) => SURVEY_TYPE_VALUES[o.value] === value)?.value ?? value
}
function questionTypeLabel(value?: string) {
  if (!value) return ''
  return QUESTION_TYPE_OPTIONS.find((o) => QUESTION_TYPE_VALUES[o.value] === value)?.value ?? value
}

export function SurveyTemplatesPage() {
  const navigate = useNavigate()
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [type, setType] = useState('')
  const [active, setActive] = useState('')
  const [modalOpen, setModalOpen] = useState(false)

  const templates = useApi(
    () =>
      surveysApi.templates.list({
        page,
        page_size: 20,
        search: search || undefined,
        survey_type: type ? SURVEY_TYPE_VALUES[type] : undefined,
        is_active: active === 'Active' ? true : active === 'Inactive' ? false : undefined,
      }),
    [page, search, type, active],
    { enabled: true },
  )

  return (
    <div className="hf-page">
      <PageHeader
        title="Survey templates"
        subtitle="Design candidate experience, onboarding, EEO, and internal surveys."
        actions={
          <Button leftIcon={<Plus size={16} />} onClick={() => navigate('/app/surveys/templates/new')}>
            New template
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
              placeholder="Search templates…"
            />
          </div>
          <div style={{ minWidth: 170, flex: '0 1 190px' }}>
            <Select
              label="Type"
              value={type}
              onChange={(e) => {
                setPage(1)
                setType(e.target.value)
              }}
              options={[{ value: '', label: 'All' }, ...SURVEY_TYPE_OPTIONS]}
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
          loading={templates.loading}
          columns={[
            {
              key: 'name',
              header: 'Template',
              render: (t: SurveyTemplate) => (
                <div>
                  <Link
                    to={`/app/surveys/templates/${t.id}`}
                    style={{ fontWeight: 650, textDecoration: 'none' }}
                  >
                    {t.name}
                  </Link>
                  <div className="hf-subtle" style={{ fontSize: '0.75rem' }}>
                    {surveyTypeLabel(t.survey_type)}
                  </div>
                </div>
              ),
            },
            {
              key: 'questions',
              header: 'Questions',
              render: (t: SurveyTemplate) => t.question_count,
            },
            {
              key: 'active',
              header: 'Status',
              render: (t: SurveyTemplate) => (
                <Badge tone={t.is_active ? 'success' : 'neutral'}>
                  {t.is_active ? 'Active' : 'Inactive'}
                </Badge>
              ),
            },
            { key: 'created', header: 'Created', render: (t: SurveyTemplate) => formatDate(t.created_at) },
          ]}
          rows={templates.data?.results || []}
          rowKey={(t) => t.id}
          emptyTitle="No templates"
          emptyDescription="Create a survey template to gather candidate experience feedback."
          onRowClick={(t) => navigate(`/app/surveys/templates/${t.id}`)}
        />
        {templates.data && (
          <Pagination page={page} pageSize={20} total={templates.data.count} onChange={setPage} />
        )}
      </Card>
    </div>
  )
}

export function SurveyTemplateFormPage() {
  const { id } = useParams()
  const isEdit = Boolean(id)
  const navigate = useNavigate()
  const { toast } = useToast()
  const [saving, setSaving] = useState(false)
  const [loading, setLoading] = useState(isEdit)
  const [form, setForm] = useState({
    name: '',
    description: '',
    survey_type: 'Candidate Experience',
    thank_you_message: '',
    is_active: true,
  })

  function set<K extends keyof typeof form>(key: K, value: (typeof form)[K]) {
    setForm((f) => ({ ...f, [key]: value }))
  }

  useEffect(() => {
    if (!id) return
    setLoading(true)
    surveysApi.templates
      .get(id)
      .then((t) => {
        setForm({
          name: t.name,
          description: t.description || '',
          survey_type: surveyTypeLabel(t.survey_type),
          thank_you_message: t.thank_you_message || '',
          is_active: t.is_active,
        })
      })
      .catch((err: unknown) =>
        toast(err instanceof ApiError ? err.message : 'Failed to load template', 'error'),
      )
      .finally(() => setLoading(false))
  }, [id, toast])

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setSaving(true)
    const payload = {
      name: form.name,
      description: form.description,
      survey_type: SURVEY_TYPE_VALUES[form.survey_type] || form.survey_type,
      thank_you_message: form.thank_you_message,
      is_active: form.is_active,
    }
    try {
      const saved = isEdit
        ? await surveysApi.templates.update(id!, payload)
        : await surveysApi.templates.create(payload)
      toast(isEdit ? 'Template updated' : 'Template created', 'success')
      navigate(`/app/surveys/templates/${saved.id}`)
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
        title={isEdit ? 'Edit survey template' : 'New survey template'}
        subtitle="Set the survey type, description, and thank-you message."
      />
      <form onSubmit={onSubmit}>
        <Card>
          <div style={{ display: 'grid', gap: 14 }}>
            <Input label="Name" required value={form.name} onChange={(e) => set('name', e.target.value)} />
            <Textarea
              label="Description"
              value={form.description}
              onChange={(e) => set('description', e.target.value)}
            />
            <Select
              label="Survey type"
              value={form.survey_type}
              onChange={(e) => set('survey_type', e.target.value)}
              options={SURVEY_TYPE_OPTIONS}
            />
            <Textarea
              label="Thank-you message"
              value={form.thank_you_message}
              onChange={(e) => set('thank_you_message', e.target.value)}
              placeholder="Shown to respondents after they complete the survey."
            />
            <label style={{ display: 'flex', gap: 8, alignItems: 'center', fontSize: '0.88rem' }}>
              <input
                type="checkbox"
                checked={form.is_active}
                onChange={(e) => set('is_active', e.target.checked)}
              />
              Active template
            </label>
            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
              <Button type="button" variant="outline" onClick={() => navigate(-1)}>
                Cancel
              </Button>
              <Button type="submit" loading={saving}>
                {isEdit ? 'Save changes' : 'Create template'}
              </Button>
            </div>
          </div>
        </Card>
      </form>
    </div>
  )
}

export function SurveyTemplateDetailPage() {
  const { id = '' } = useParams()
  const navigate = useNavigate()
  const { toast } = useToast()
  const [tab, setTab] = useState('overview')
  const [acting, setActing] = useState(false)
  const [questionOpen, setQuestionOpen] = useState(false)
  const [editingQuestion, setEditingQuestion] = useState<SurveyQuestion | null>(null)
  const [deletingQuestion, setDeletingQuestion] = useState<SurveyQuestion | null>(null)

  const template = useApi(() => surveysApi.templates.get(id), [id], { enabled: Boolean(id) })
  const questions = useApi(
    () => surveysApi.questions.list({ template: id, page_size: 100 }),
    [id, tab],
    { enabled: Boolean(id) && tab === 'questions' },
  )

  async function runAction(action: () => Promise<unknown>, ok: string) {
    setActing(true)
    try {
      await action()
      toast(ok, 'success')
      template.reload()
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Action failed', 'error')
    } finally {
      setActing(false)
    }
  }

  if (template.loading) {
    return (
      <div style={{ padding: 64, display: 'grid', placeItems: 'center' }}>
        <Spinner label="Loading template…" />
      </div>
    )
  }
  if (template.error || !template.data) {
    return (
      <EmptyState
        title="Template not found"
        description={template.error || 'This template may have been deleted.'}
        actionLabel="Back to templates"
        onAction={() => navigate('/app/surveys/templates')}
      />
    )
  }

  const t = template.data

  return (
    <div className="hf-page">
      <PageHeader
        title={t.name}
        subtitle={surveyTypeLabel(t.survey_type)}
        breadcrumbs={[{ label: 'Surveys', to: '/app/surveys' }, { label: t.name }]}
        actions={
          <>
            <Badge tone={t.is_active ? 'success' : 'neutral'}>
              {t.is_active ? 'Active' : 'Inactive'}
            </Badge>
            <Button variant="outline" onClick={() => navigate(`/app/surveys/templates/${id}/edit`)}>
              Edit
            </Button>
            <Button
              variant="outline"
              loading={acting}
              leftIcon={<Copy size={14} />}
              onClick={() =>
                runAction(() => surveysApi.templates.duplicate(id), 'Template duplicated')
              }
            >
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
          { id: 'questions', label: 'Questions', count: questions.data?.count },
        ]}
      />

      {tab === 'overview' && (
        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 16 }}>
          <Card title="Description">
            <p className="hf-muted" style={{ lineHeight: 1.6 }}>
              {t.description || 'No description yet.'}
            </p>
            <h3 style={{ marginTop: 18, marginBottom: 8 }}>Thank-you message</h3>
            <p className="hf-muted" style={{ lineHeight: 1.6 }}>
              {t.thank_you_message || '—'}
            </p>
          </Card>
          <div style={{ display: 'grid', gap: 12 }}>
            <StatCard label="Questions" value={t.question_count} icon={<Mail size={16} />} />
            <StatCard label="Type" value={titleCase(t.survey_type)} />
          </div>
        </div>
      )}

      {tab === 'questions' && (
        <Card>
          <CardHeader
            title="Questions"
            actions={
              <Button
                size="sm"
                leftIcon={<Plus size={14} />}
                onClick={() => {
                  setEditingQuestion(null)
                  setQuestionOpen(true)
                }}
              >
                Add question
              </Button>
            }
          />
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {(questions.data?.results || []).map((q) => (
              <div
                key={q.id}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 12,
                  padding: '0.75rem 1rem',
                  border: '1px solid var(--hf-border)',
                  borderRadius: 10,
                }}
              >
                <span className="hf-subtle" style={{ fontWeight: 700, minWidth: 24 }}>
                  {q.order}
                </span>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontWeight: 600 }}>{q.question_text}</div>
                  <div className="hf-subtle" style={{ fontSize: '0.75rem' }}>
                    {questionTypeLabel(q.question_type)}
                    {q.is_required ? ' · Required' : ''}
                    {q.options?.length ? ` · ${q.options.join(', ')}` : ''}
                  </div>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    setEditingQuestion(q)
                    setQuestionOpen(true)
                  }}
                >
                  <Pencil size={14} />
                </Button>
                <Button variant="ghost" size="sm" onClick={() => setDeletingQuestion(q)}>
                  <Trash2 size={14} />
                </Button>
              </div>
            ))}
            {!questions.data?.results?.length && (
              <EmptyState
                title="No questions yet"
                description="Add a question to start building this survey."
                actionLabel="Add question"
                onAction={() => {
                  setEditingQuestion(null)
                  setQuestionOpen(true)
                }}
              />
            )}
          </div>
        </Card>
      )}

      <QuestionFormModal
        open={questionOpen}
        templateId={id}
        editing={editingQuestion}
        onClose={() => setQuestionOpen(false)}
        onSaved={() => {
          questions.reload()
          template.reload()
          setQuestionOpen(false)
        }}
      />
      <ConfirmDialog
        open={Boolean(deletingQuestion)}
        title="Delete question"
        message={`Delete "${deletingQuestion?.question_text}"? Responses to it will be removed.`}
        confirmLabel="Delete"
        danger
        onCancel={() => setDeletingQuestion(null)}
        onConfirm={() => {
          if (!deletingQuestion) return
          surveysApi.questions
            .remove(deletingQuestion.id)
            .then(() => {
              toast('Question deleted', 'success')
              questions.reload()
              template.reload()
            })
            .catch((err: unknown) =>
              toast(err instanceof ApiError ? err.message : 'Delete failed', 'error'),
            )
            .finally(() => setDeletingQuestion(null))
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
        padding: '0 0 1rem',
      }}
    >
      <h3 style={{ fontSize: '1.05rem', margin: 0 }}>{title}</h3>
      <div style={{ display: 'flex', gap: 8 }}>{actions}</div>
    </div>
  )
}

function QuestionFormModal({
  open,
  templateId,
  editing,
  onClose,
  onSaved,
}: {
  open: boolean
  templateId: string
  editing: SurveyQuestion | null
  onClose: () => void
  onSaved: () => void
}) {
  const { toast } = useToast()
  const [text, setText] = useState('')
  const [questionType, setQuestionType] = useState('Rating')
  const [options, setOptions] = useState('')
  const [isRequired, setIsRequired] = useState(true)
  const [order, setOrder] = useState(0)
  const [saving, setSaving] = useState(false)
  const [seed, setSeed] = useState('')

  if (open && seed !== (editing?.id || 'new')) {
    setSeed(editing?.id || 'new')
    setText(editing?.question_text || '')
    setQuestionType(questionTypeLabel(editing?.question_type) || 'Rating')
    setOptions((editing?.options || []).join(', '))
    setIsRequired(editing?.is_required ?? true)
    setOrder(editing?.order ?? 0)
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setSaving(true)
    const payload = {
      template: templateId,
      question_text: text,
      question_type: QUESTION_TYPE_VALUES[questionType] || questionType,
      options: options
        .split(',')
        .map((o) => o.trim())
        .filter(Boolean),
      is_required: isRequired,
      order: Number(order) || 0,
    }
    try {
      if (editing) {
        await surveysApi.questions.update(editing.id, payload)
        toast('Question updated', 'success')
      } else {
        await surveysApi.questions.create(payload)
        toast('Question added', 'success')
      }
      onSaved()
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Save failed', 'error')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal open={open} onClose={onClose} title={editing ? 'Edit question' : 'Add question'}>
      <form onSubmit={onSubmit} style={{ display: 'grid', gap: 12 }}>
        <Textarea label="Question text" required value={text} onChange={(e) => setText(e.target.value)} />
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          <Select
            label="Type"
            value={questionType}
            onChange={(e) => setQuestionType(e.target.value)}
            options={QUESTION_TYPE_OPTIONS}
          />
          <Input
            label="Order"
            type="number"
            value={order}
            onChange={(e) => setOrder(Number(e.target.value))}
          />
        </div>
        <Input
          label="Options (comma-separated, for choice questions)"
          value={options}
          onChange={(e) => setOptions(e.target.value)}
        />
        <label style={{ display: 'flex', gap: 8, alignItems: 'center', fontSize: '0.88rem' }}>
          <input
            type="checkbox"
            checked={isRequired}
            onChange={(e) => setIsRequired(e.target.checked)}
          />
          Required question
        </label>
        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
          <Button type="button" variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={saving}>
            {editing ? 'Save changes' : 'Add question'}
          </Button>
        </div>
      </form>
    </Modal>
  )
}

export function SurveyInstancesPage() {
  const navigate = useNavigate()
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('')
  const [template, setTemplate] = useState('')
  const [modalOpen, setModalOpen] = useState(false)

  const instances = useApi(
    () =>
      surveysApi.instances.list({
        page,
        page_size: 20,
        search: search || undefined,
        status: status ? INSTANCE_STATUS_VALUES[status] : undefined,
        template: template || undefined,
      }),
    [page, search, status, template],
    { enabled: true },
  )
  const templates = useApi(() => surveysApi.templates.list({ page_size: 100 }), [], { enabled: true })

  return (
    <div className="hf-page">
      <PageHeader
        title="Survey instances"
        subtitle="Send surveys to candidates and track completion."
        actions={
          <Button leftIcon={<Plus size={16} />} onClick={() => setModalOpen(true)}>
            New instance
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
              placeholder="Search instances…"
            />
          </div>
          <div style={{ minWidth: 170, flex: '0 1 190px' }}>
            <Select
              label="Status"
              value={status}
              onChange={(e) => {
                setPage(1)
                setStatus(e.target.value)
              }}
              options={[{ value: '', label: 'All' }, ...INSTANCE_STATUS_OPTIONS]}
            />
          </div>
          <div style={{ minWidth: 170, flex: '0 1 190px' }}>
            <Select
              label="Template"
              value={template}
              onChange={(e) => {
                setPage(1)
                setTemplate(e.target.value)
              }}
              options={[
                { value: '', label: 'All' },
                ...(templates.data?.results || []).map((t) => ({ value: t.id, label: t.name })),
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
                setTemplate('')
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
          loading={instances.loading}
          columns={[
            {
              key: 'template',
              header: 'Survey',
              render: (i: SurveyInstance) => (
                <div>
                  <Link
                    to={`/app/surveys/instances/${i.id}`}
                    style={{ fontWeight: 650, textDecoration: 'none' }}
                  >
                    {i.template_name}
                  </Link>
                  <div className="hf-subtle" style={{ fontSize: '0.75rem' }}>
                    {i.candidate_name || 'Anonymous'}
                    {i.job_title ? ` · ${i.job_title}` : ''}
                  </div>
                </div>
              ),
            },
            { key: 'status', header: 'Status', render: (i: SurveyInstance) => <Badge status={i.status} /> },
            {
              key: 'responses',
              header: 'Responses',
              render: (i: SurveyInstance) => i.response_count,
            },
            { key: 'sent', header: 'Sent', render: (i: SurveyInstance) => formatDateTime(i.sent_at) },
            {
              key: 'completed',
              header: 'Completed',
              render: (i: SurveyInstance) => formatDateTime(i.completed_at),
            },
          ]}
          rows={instances.data?.results || []}
          rowKey={(i) => i.id}
          emptyTitle="No instances"
          emptyDescription="Create an instance to send a survey."
          onRowClick={(i) => navigate(`/app/surveys/instances/${i.id}`)}
        />
        {instances.data && (
          <Pagination page={page} pageSize={20} total={instances.data.count} onChange={setPage} />
        )}
      </Card>
      <InstanceFormModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        onSaved={() => {
          instances.reload()
          setModalOpen(false)
        }}
      />
    </div>
  )
}

function InstanceFormModal({
  open,
  onClose,
  onSaved,
}: {
  open: boolean
  onClose: () => void
  onSaved: () => void
}) {
  const { toast } = useToast()
  const [template, setTemplate] = useState('')
  const [candidate, setCandidate] = useState('')
  const [job, setJob] = useState('')
  const [anonymous, setAnonymous] = useState(false)
  const [saving, setSaving] = useState(false)
  const templates = useApi(() => surveysApi.templates.list({ page_size: 100 }), [], { enabled: true })

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setSaving(true)
    try {
      await surveysApi.instances.create({
        template,
        candidate: candidate || null,
        job: job || null,
        anonymous,
      })
      toast('Instance created', 'success')
      setTemplate('')
      setCandidate('')
      setJob('')
      setAnonymous(false)
      onSaved()
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Create failed', 'error')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal open={open} onClose={onClose} title="New survey instance">
      <form onSubmit={onSubmit} style={{ display: 'grid', gap: 12 }}>
        <Select
          label="Template"
          required
          value={template}
          onChange={(e) => setTemplate(e.target.value)}
          placeholder="Select template"
          options={(templates.data?.results || []).map((t) => ({ value: t.id, label: t.name }))}
        />
        <Input
          label="Candidate ID (optional)"
          value={candidate}
          onChange={(e) => setCandidate(e.target.value)}
          placeholder="UUID"
        />
        <Input
          label="Job ID (optional)"
          value={job}
          onChange={(e) => setJob(e.target.value)}
          placeholder="UUID"
        />
        <label style={{ display: 'flex', gap: 8, alignItems: 'center', fontSize: '0.88rem' }}>
          <input
            type="checkbox"
            checked={anonymous}
            onChange={(e) => setAnonymous(e.target.checked)}
          />
          Anonymous response
        </label>
        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
          <Button type="button" variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={saving}>
            Create instance
          </Button>
        </div>
      </form>
    </Modal>
  )
}

export function SurveyInstanceDetailPage() {
  const { id = '' } = useParams()
  const navigate = useNavigate()
  const { toast } = useToast()
  const [tab, setTab] = useState('overview')
  const [acting, setActing] = useState(false)
  const [page, setPage] = useState(1)

  const instance = useApi(() => surveysApi.instances.get(id), [id], { enabled: Boolean(id) })
  const responses = useApi(
    () => surveysApi.responses.list({ instance: id, page, page_size: 20 }),
    [id, tab, page],
    { enabled: Boolean(id) && tab === 'responses' },
  )
  const invitations = useApi(
    () => surveysApi.invitations.list({ instance: id, page_size: 50 }),
    [id, tab],
    { enabled: Boolean(id) && tab === 'invitations' },
  )

  async function runAction(action: () => Promise<unknown>, ok: string) {
    setActing(true)
    try {
      await action()
      toast(ok, 'success')
      instance.reload()
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Action failed', 'error')
    } finally {
      setActing(false)
    }
  }

  if (instance.loading) {
    return (
      <div style={{ padding: 64, display: 'grid', placeItems: 'center' }}>
        <Spinner label="Loading instance…" />
      </div>
    )
  }
  if (instance.error || !instance.data) {
    return (
      <EmptyState
        title="Instance not found"
        description={instance.error || 'This instance may have been deleted.'}
        actionLabel="Back to instances"
        onAction={() => navigate('/app/surveys/instances')}
      />
    )
  }

  const i = instance.data

  return (
    <div className="hf-page">
      <PageHeader
        title={i.template_name}
        subtitle={`${i.candidate_name || 'Anonymous'}${i.job_title ? ` · ${i.job_title}` : ''}`}
        breadcrumbs={[{ label: 'Surveys', to: '/app/surveys' }, { label: i.template_name }]}
        actions={
          <>
            <Badge status={i.status} />
            {i.status === 'draft' && (
              <Button
                loading={acting}
                leftIcon={<Send size={14} />}
                onClick={() => runAction(() => surveysApi.instances.send(id), 'Survey sent')}
              >
                Send
              </Button>
            )}
            {['sent', 'partially_completed'].includes(i.status) && (
              <Button
                variant="outline"
                loading={acting}
                leftIcon={<BellRing size={14} />}
                onClick={() =>
                  runAction(() => surveysApi.instances.sendReminder(id), 'Reminder sent')
                }
              >
                Send reminder
              </Button>
            )}
            {['sent', 'partially_completed'].includes(i.status) && (
              <Button
                variant="outline"
                loading={acting}
                leftIcon={<XCircle size={14} />}
                onClick={() => runAction(() => surveysApi.instances.close(id), 'Survey closed')}
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
          { id: 'responses', label: 'Responses', count: responses.data?.count },
          { id: 'invitations', label: 'Invitations', count: invitations.data?.count },
        ]}
      />

      {tab === 'overview' && (
        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 16 }}>
          <Card title="Instance details">
            <dl style={{ display: 'grid', gap: 10, margin: 0, fontSize: '0.88rem' }}>
              <Row label="Status" value={titleCase(i.status)} />
              <Row label="Anonymous" value={i.anonymous ? 'Yes' : 'No'} />
              <Row label="Sent" value={formatDateTime(i.sent_at)} />
              <Row label="Completed" value={formatDateTime(i.completed_at)} />
              <Row label="Token" value={i.token} />
            </dl>
          </Card>
          <div style={{ display: 'grid', gap: 12 }}>
            <StatCard label="Responses" value={i.response_count} icon={<Mail size={16} />} />
            <StatCard label="Invitations" value={i.invitation_count} icon={<BellRing size={16} />} />
          </div>
        </div>
      )}

      {tab === 'responses' && (
        <Card padding={0}>
          <DataTable
            loading={responses.loading}
            columns={[
              {
                key: 'question',
                header: 'Question',
                render: (r) => (
                  <div>
                    <span style={{ fontWeight: 600 }}>{r.question_text}</span>
                    <div className="hf-subtle" style={{ fontSize: '0.75rem' }}>
                      {questionTypeLabel(r.question_type)}
                    </div>
                  </div>
                ),
              },
              {
                key: 'answer',
                header: 'Answer',
                render: (r) => (
                  <span style={{ fontSize: '0.88rem' }}>
                    {typeof r.answer === 'object' && r.answer !== null
                      ? JSON.stringify(r.answer)
                      : String(r.answer ?? '—')}
                  </span>
                ),
              },
              { key: 'answered', header: 'Answered', render: (r) => formatDateTime(r.answered_at) },
            ]}
            rows={responses.data?.results || []}
            rowKey={(r) => r.id}
            emptyTitle="No responses yet"
            emptyDescription="Responses will appear as the survey is completed."
          />
          {responses.data && (
            <Pagination page={page} pageSize={20} total={responses.data.count} onChange={setPage} />
          )}
        </Card>
      )}

      {tab === 'invitations' && (
        <Card padding={0}>
          <DataTable
            loading={invitations.loading}
            columns={[
              { key: 'email', header: 'Email', render: (v) => v.email },
              { key: 'status', header: 'Status', render: (v) => <Badge status={v.status} /> },
              { key: 'sent', header: 'Sent', render: (v) => formatDateTime(v.sent_at) },
              { key: 'completed', header: 'Completed', render: (v) => formatDateTime(v.completed_at) },
            ]}
            rows={invitations.data?.results || []}
            rowKey={(v) => v.id}
            emptyTitle="No invitations"
            emptyDescription="Invitations are created when the survey is sent."
          />
        </Card>
      )}
    </div>
  )
}

export function SurveyAnalyticsPage() {
  const [templateId, setTemplateId] = useState('')
  const templates = useApi(() => surveysApi.templates.list({ page_size: 100 }), [], { enabled: true })
  const analytics = useApi(
    () => surveysApi.analytics(templateId),
    [templateId],
    { enabled: Boolean(templateId) },
  )

  return (
    <div className="hf-page">
      <PageHeader
        title="Survey analytics"
        subtitle="Response rates and per-question breakdowns by template."
        breadcrumbs={[{ label: 'Surveys', to: '/app/surveys' }, { label: 'Analytics' }]}
      />
      <Card>
        <div style={{ maxWidth: 420 }}>
          <Select
            label="Template"
            value={templateId}
            onChange={(e) => setTemplateId(e.target.value)}
            placeholder="Select a template"
            options={(templates.data?.results || []).map((t) => ({ value: t.id, label: t.name }))}
          />
        </div>
      </Card>
      {!templateId && (
        <Card>
          <EmptyState
            title="Pick a template"
            description="Select a survey template above to see its analytics."
          />
        </Card>
      )}
      {templateId && analytics.loading && (
        <Card>
          <Spinner label="Loading analytics…" />
        </Card>
      )}
      {templateId && analytics.error && (
        <Card>
          <p style={{ color: 'var(--hf-danger)' }}>{analytics.error}</p>
        </Card>
      )}
      {templateId && analytics.data && (
        <>
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
              gap: 12,
            }}
          >
            <StatCard
              label="Total instances"
              value={analytics.data.total_instances}
              icon={<Mail size={16} />}
            />
            <StatCard label="Sent" value={analytics.data.sent_instances} icon={<Send size={16} />} />
            <StatCard
              label="Completed"
              value={analytics.data.completed_instances}
              icon={<BarChart3 size={16} />}
            />
            <StatCard
              label="Response rate"
              value={`${Math.round((analytics.data.response_rate || 0) * 100)}%`}
            />
          </div>
          <Card title="Per-question breakdown" subtitle={analytics.data.template_name}>
            <DataTable
              loading={false}
              columns={[
                {
                  key: 'question',
                  header: 'Question',
                  render: (q) => (
                    <div>
                      <span style={{ fontWeight: 600 }}>{q.question_text}</span>
                      <div className="hf-subtle" style={{ fontSize: '0.75rem' }}>
                        {questionTypeLabel(q.question_type)}
                      </div>
                    </div>
                  ),
                },
                { key: 'responses', header: 'Responses', render: (q) => q.response_count },
                {
                  key: 'breakdown',
                  header: 'Breakdown',
                  render: (q) => (
                    <span className="hf-subtle" style={{ fontSize: '0.8rem' }}>
                      {JSON.stringify(q.breakdown)}
                    </span>
                  ),
                },
              ]}
              rows={analytics.data.questions}
              rowKey={(q) => q.question_id}
              emptyTitle="No questions"
              emptyDescription="Add questions to this template to see analytics."
            />
          </Card>
        </>
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
