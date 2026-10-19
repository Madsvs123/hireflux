/**
 * Documents pages (categories, templates, generated documents, e-sign requests).
 *
 * Exported components & suggested routes:
 *  - DocumentCategoriesPage        → /app/documents/categories
 *  - DocumentsTemplatesPage        → /app/documents
 *  - DocumentsTemplateDetailPage   → /app/documents/templates/:id
 *  - DocumentsTemplateFormPage     → /app/documents/templates/new | /app/documents/templates/:id/edit
 *  - GeneratedDocumentsPage        → /app/documents/generated
 *  - GeneratedDocumentFormPage     → /app/documents/generated/new
 *  - GeneratedDocumentDetailPage   → /app/documents/generated/:id
 *  - SignRequestsPage              → /app/documents/sign-requests
 */
import { useEffect, useState, type FormEvent } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { Download, FileText, FileSignature, Plus, Send } from 'lucide-react'
import {
  documentCategoriesApi,
  documentSignRequestsApi,
  documentTemplatesApi,
  generatedDocumentsApi,
  type DocumentCategory,
  type DocumentTemplate,
  type GeneratedDocument,
} from '../../api/documents'
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
  Tabs,
  Textarea,
  useToast,
} from '../../components/ui'
import { formatDate, formatDateTime, titleCase } from '../../utils/format'
import { ApiError } from '../../api/http'

// ---------------------------------------------------------------------------
// Categories
// ---------------------------------------------------------------------------

export function DocumentCategoriesPage() {
  const { toast } = useToast()
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<DocumentCategory | null>(null)
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [isActive, setIsActive] = useState(true)
  const [saving, setSaving] = useState(false)
  const [removing, setRemoving] = useState<DocumentCategory | null>(null)
  const { data, loading, error, reload } = useApi(
    () => documentCategoriesApi.list({ page, page_size: 20, search: search || undefined }),
    [page, search],
  )

  function openCreate() {
    setEditing(null)
    setName('')
    setDescription('')
    setIsActive(true)
    setModalOpen(true)
  }

  function openEdit(cat: DocumentCategory) {
    setEditing(cat)
    setName(cat.name)
    setDescription(cat.description)
    setIsActive(cat.is_active)
    setModalOpen(true)
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setSaving(true)
    try {
      if (editing) {
        await documentCategoriesApi.update(editing.id, { name, description, is_active: isActive })
        toast('Category updated', 'success')
      } else {
        await documentCategoriesApi.create({ name, description, is_active: isActive })
        toast('Category created', 'success')
      }
      setModalOpen(false)
      reload()
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Save failed', 'error')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="hf-page">
      <PageHeader
        title="Document categories"
        subtitle="Organize document templates into categories."
        actions={<Button leftIcon={<Plus size={16} />} onClick={openCreate}>New category</Button>}
      />

      <Card padding="1rem">
        <Input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search categories…" />
      </Card>

      {error && (
        <Card>
          <p style={{ color: 'var(--hf-danger)' }}>{error}</p>
          <Button variant="outline" size="sm" onClick={reload} style={{ marginTop: 8 }}>Retry</Button>
        </Card>
      )}

      <Card padding={0}>
        <DataTable
          loading={loading}
          columns={[
            { key: 'name', header: 'Name', render: (c) => c.name },
            { key: 'description', header: 'Description', render: (c) => c.description || '—' },
            {
              key: 'active',
              header: 'Active',
              render: (c) => <Badge tone={c.is_active ? 'success' : 'neutral'}>{c.is_active ? 'Active' : 'Inactive'}</Badge>,
            },
            {
              key: 'actions',
              header: '',
              render: (c) => (
                <div style={{ display: 'flex', gap: 6 }}>
                  <Button variant="outline" size="sm" onClick={(e) => { e.stopPropagation(); openEdit(c) }}>Edit</Button>
                  <Button variant="ghost" size="sm" onClick={(e) => { e.stopPropagation(); setRemoving(c) }}>Delete</Button>
                </div>
              ),
            },
          ]}
          rows={data?.results || []}
          rowKey={(c) => c.id}
          emptyTitle="No categories"
          emptyDescription="Create categories to organize document templates."
        />
        {data && <Pagination page={page} pageSize={20} total={data.count} onChange={setPage} />}
      </Card>

      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title={editing ? 'Edit category' : 'New category'}>
        <form onSubmit={onSubmit} style={{ display: 'grid', gap: 12 }}>
          <Input label="Name" required value={name} onChange={(e) => setName(e.target.value)} />
          <Textarea label="Description" value={description} onChange={(e) => setDescription(e.target.value)} />
          <label style={{ display: 'flex', gap: 8, alignItems: 'center', fontSize: '0.88rem' }}>
            <input type="checkbox" checked={isActive} onChange={(e) => setIsActive(e.target.checked)} />
            Active
          </label>
          <Button type="submit" loading={saving}>
            {editing ? 'Save changes' : 'Create category'}
          </Button>
        </form>
      </Modal>

      <ConfirmDialog
        open={Boolean(removing)}
        title="Delete category"
        message={`Delete "${removing?.name}"? Templates in this category keep existing but lose their category.`}
        confirmLabel="Delete"
        danger
        onCancel={() => setRemoving(null)}
        onConfirm={() => {
          if (!removing) return
          documentCategoriesApi
            .remove(removing.id)
            .then(() => { toast('Category deleted', 'success'); setRemoving(null); reload() })
            .catch((err) => toast(err instanceof ApiError ? err.message : 'Delete failed', 'error'))
        }}
      />
    </div>
  )
}

// ---------------------------------------------------------------------------
// Templates
// ---------------------------------------------------------------------------

export function DocumentsTemplatesPage() {
  const navigate = useNavigate()
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [category, setCategory] = useState('')
  const { data, loading, error, reload } = useApi(
    () =>
      documentTemplatesApi.list({
        page,
        page_size: 20,
        search: search || undefined,
        category: category || undefined,
      }),
    [page, search, category],
  )
  const categories = useApi(() => documentCategoriesApi.list({ page_size: 100 }), [])

  return (
    <div className="hf-page">
      <PageHeader
        title="Document templates"
        subtitle="Reusable templates with merge variables for offers, contracts, and more."
        actions={
          <Button leftIcon={<Plus size={16} />} onClick={() => navigate('/app/documents/templates/new')}>
            New template
          </Button>
        }
      />

      <Card padding="1rem">
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, alignItems: 'flex-end' }}>
          <div style={{ flex: '1 1 260px', minWidth: 220 }}>
            <Input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search templates…" />
          </div>
          <div style={{ minWidth: 160 }}>
            <Select
              label="Category"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              options={[{ value: '', label: 'All' }, ...(categories.data?.results || []).map((c) => ({ value: c.id, label: c.name }))]}
            />
          </div>
          <Button variant="ghost" size="sm" onClick={() => { setSearch(''); setCategory(''); setPage(1) }}>
            Clear
          </Button>
        </div>
      </Card>

      {error && (
        <Card>
          <p style={{ color: 'var(--hf-danger)' }}>{error}</p>
          <Button variant="outline" size="sm" onClick={reload} style={{ marginTop: 8 }}>Retry</Button>
        </Card>
      )}

      <Card padding={0}>
        <DataTable
          loading={loading}
          columns={[
            {
              key: 'name',
              header: 'Name',
              render: (t: DocumentTemplate) => (
                <div>
                  <Link to={`/app/documents/templates/${t.id}`} style={{ fontWeight: 650, textDecoration: 'none' }}>
                    {t.name}
                  </Link>
                  <div className="hf-subtle" style={{ fontSize: '0.75rem' }}>{t.category_name || 'Uncategorized'}</div>
                </div>
              ),
            },
            { key: 'description', header: 'Description', render: (t: DocumentTemplate) => t.description || '—' },
            { key: 'variables', header: 'Variables', render: (t: DocumentTemplate) => String(t.variables?.length || 0) },
            {
              key: 'active',
              header: 'Active',
              render: (t: DocumentTemplate) => <Badge tone={t.is_active ? 'success' : 'neutral'}>{t.is_active ? 'Active' : 'Inactive'}</Badge>,
            },
            { key: 'created', header: 'Created', render: (t: DocumentTemplate) => formatDate(t.created_at) },
          ]}
          rows={data?.results || []}
          rowKey={(t) => t.id}
          emptyTitle="No templates"
          emptyDescription="Create a document template to generate documents."
          onRowClick={(t) => navigate(`/app/documents/templates/${t.id}`)}
        />
        {data && <Pagination page={page} pageSize={20} total={data.count} onChange={setPage} />}
      </Card>
    </div>
  )
}

export function DocumentsTemplateDetailPage() {
  const { id = '' } = useParams()
  const navigate = useNavigate()
  const { toast } = useToast()
  const [renderOpen, setRenderOpen] = useState(false)
  const [renderResult, setRenderResult] = useState<{ content_html: string; content_text: string } | null>(null)
  const [vars, setVars] = useState('')
  const [rendering, setRendering] = useState(false)
  const [acting, setActing] = useState(false)
  const [removeOpen, setRemoveOpen] = useState(false)
  const template = useApi(() => documentTemplatesApi.get(id), [id], { enabled: Boolean(id) })

  async function runRender(e: FormEvent) {
    e.preventDefault()
    setRendering(true)
    try {
      const variables: Record<string, string> = {}
      for (const line of vars.split('\n')) {
        const idx = line.indexOf('=')
        if (idx > 0) variables[line.slice(0, idx).trim()] = line.slice(idx + 1).trim()
      }
      const result = await documentTemplatesApi.render(id, { variables })
      setRenderResult(result)
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Render failed', 'error')
    } finally {
      setRendering(false)
    }
  }

  async function runDuplicate() {
    setActing(true)
    try {
      await documentTemplatesApi.duplicate(id)
      toast('Template duplicated', 'success')
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Duplicate failed', 'error')
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
        onAction={() => navigate('/app/documents')}
      />
    )
  }

  const t = template.data

  return (
    <div className="hf-page">
      <PageHeader
        title={t.name}
        subtitle={`${t.category_name || 'Uncategorized'} · ${t.variables?.length || 0} variables`}
        actions={
          <>
            <Badge tone={t.is_active ? 'success' : 'neutral'}>{t.is_active ? 'Active' : 'Inactive'}</Badge>
            <Button variant="outline" onClick={() => navigate(`/app/documents/templates/${id}/edit`)}>Edit</Button>
            <Button variant="outline" loading={acting} onClick={() => void runDuplicate()}>Duplicate</Button>
            <Button variant="outline" leftIcon={<FileText size={15} />} onClick={() => { setVars(''); setRenderResult(null); setRenderOpen(true) }}>
              Render preview
            </Button>
            <Button variant="danger" onClick={() => setRemoveOpen(true)}>Delete</Button>
          </>
        }
      />

      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 16 }}>
        <Card title="Body (HTML)">
          <div className="hf-muted" style={{ whiteSpace: 'pre-wrap', lineHeight: 1.6, fontSize: '0.88rem', maxHeight: 420, overflow: 'auto' }}>
            {t.body_html || 'No HTML body.'}
          </div>
        </Card>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <Card title="Body (text)">
            <div className="hf-muted" style={{ whiteSpace: 'pre-wrap', lineHeight: 1.6, fontSize: '0.88rem', maxHeight: 200, overflow: 'auto' }}>
              {t.body_text || 'No text body.'}
            </div>
          </Card>
          <Card title="Variables">
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
              {(t.variables || []).map((v) => (
                <Badge key={v} tone="teal">{v}</Badge>
              ))}
              {!t.variables?.length && <span className="hf-muted">No variables defined</span>}
            </div>
          </Card>
          <Card title="Details">
            <dl style={{ display: 'grid', gap: 10, margin: 0, fontSize: '0.88rem' }}>
              <Row label="Currency" value={t.default_currency || 'USD'} />
              <Row label="Created" value={formatDate(t.created_at)} />
            </dl>
          </Card>
        </div>
      </div>

      <Modal open={renderOpen} onClose={() => setRenderOpen(false)} title="Render preview" width={680}>
        <form onSubmit={runRender} style={{ display: 'grid', gap: 12 }}>
          <Textarea
            label="Variables (one per line: name=value)"
            value={vars}
            onChange={(e) => setVars(e.target.value)}
            placeholder={'candidate_name=Jane Doe\noffer_salary=120000'}
          />
          <Button type="submit" loading={rendering}>
            Render
          </Button>
        </form>
        {renderResult && (
          <Card title="Preview" style={{ marginTop: 12 }}>
            <div className="hf-muted" style={{ whiteSpace: 'pre-wrap', lineHeight: 1.6, fontSize: '0.88rem', maxHeight: 320, overflow: 'auto' }}>
              {renderResult.content_html || renderResult.content_text}
            </div>
          </Card>
        )}
      </Modal>

      <ConfirmDialog
        open={removeOpen}
        title="Delete template"
        message={`Delete "${t.name}"? Generated documents keep their content.`}
        confirmLabel="Delete"
        danger
        onCancel={() => setRemoveOpen(false)}
        onConfirm={() => {
          documentTemplatesApi
            .remove(id)
            .then(() => { toast('Template deleted', 'success'); navigate('/app/documents') })
            .catch((err) => toast(err instanceof ApiError ? err.message : 'Delete failed', 'error'))
        }}
      />
    </div>
  )
}

export function DocumentsTemplateFormPage() {
  const { id } = useParams()
  const isEdit = Boolean(id)
  const navigate = useNavigate()
  const { toast } = useToast()
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [category, setCategory] = useState('')
  const [bodyHtml, setBodyHtml] = useState('')
  const [bodyText, setBodyText] = useState('')
  const [variables, setVariables] = useState('')
  const [defaultCurrency, setDefaultCurrency] = useState('USD')
  const [isActive, setIsActive] = useState(true)
  const [loading, setLoading] = useState(isEdit)
  const [saving, setSaving] = useState(false)
  const categories = useApi(() => documentCategoriesApi.list({ page_size: 100 }), [])

  useEffect(() => {
    if (!id) return
    setLoading(true)
    documentTemplatesApi
      .get(id)
      .then((t) => {
        setName(t.name)
        setDescription(t.description)
        setCategory(t.category || '')
        setBodyHtml(t.body_html || '')
        setBodyText(t.body_text || '')
        setVariables((t.variables || []).join('\n'))
        setDefaultCurrency(t.default_currency || 'USD')
        setIsActive(t.is_active)
      })
      .catch((err) => toast(err instanceof ApiError ? err.message : 'Failed to load', 'error'))
      .finally(() => setLoading(false))
  }, [id, toast])

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setSaving(true)
    const payload = {
      name,
      description,
      category: category || null,
      body_html: bodyHtml,
      body_text: bodyText,
      variables: variables.split('\n').map((v) => v.trim()).filter(Boolean),
      default_currency: defaultCurrency || 'USD',
      is_active: isActive,
    }
    try {
      if (isEdit) {
        await documentTemplatesApi.update(id!, payload)
        toast('Template updated', 'success')
      } else {
        await documentTemplatesApi.create(payload)
        toast('Template created', 'success')
      }
      navigate('/app/documents')
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
      <PageHeader title={isEdit ? 'Edit template' : 'New document template'} subtitle="Define the template body and merge variables." />
      <form onSubmit={onSubmit}>
        <Card>
          <div style={{ display: 'grid', gap: 14 }}>
            <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 12 }}>
              <Input label="Name" required value={name} onChange={(e) => setName(e.target.value)} />
              <Select
                label="Category"
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                placeholder="No category"
                options={(categories.data?.results || []).map((c) => ({ value: c.id, label: c.name }))}
              />
            </div>
            <Textarea label="Description" value={description} onChange={(e) => setDescription(e.target.value)} />
            <Textarea
              label="Body (HTML)"
              value={bodyHtml}
              onChange={(e) => setBodyHtml(e.target.value)}
              style={{ minHeight: 180, fontFamily: 'monospace', fontSize: '0.85rem' }}
            />
            <Textarea
              label="Body (plain text)"
              value={bodyText}
              onChange={(e) => setBodyText(e.target.value)}
              style={{ minHeight: 140 }}
            />
            <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 12 }}>
              <Input
                label="Variables (one per line)"
                value={variables}
                onChange={(e) => setVariables(e.target.value)}
                placeholder={'candidate_name\noffer_salary'}
              />
              <Input label="Default currency" value={defaultCurrency} onChange={(e) => setDefaultCurrency(e.target.value)} />
            </div>
            <label style={{ display: 'flex', gap: 8, alignItems: 'center', fontSize: '0.88rem' }}>
              <input type="checkbox" checked={isActive} onChange={(e) => setIsActive(e.target.checked)} />
              Active
            </label>
            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
              <Button type="button" variant="outline" onClick={() => navigate(-1)}>Cancel</Button>
              <Button type="submit" loading={saving}>{isEdit ? 'Save changes' : 'Create template'}</Button>
            </div>
          </div>
        </Card>
      </form>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Generated documents
// ---------------------------------------------------------------------------

export function GeneratedDocumentsPage() {
  const navigate = useNavigate()
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('')
  const { data, loading, error, reload } = useApi(
    () =>
      generatedDocumentsApi.list({
        page,
        page_size: 20,
        search: search || undefined,
        status: status || undefined,
      }),
    [page, search, status],
  )

  return (
    <div className="hf-page">
      <PageHeader
        title="Generated documents"
        subtitle="Documents created from templates, with finalize / void lifecycle."
        actions={
          <Button leftIcon={<Plus size={16} />} onClick={() => navigate('/app/documents/generated/new')}>
            New document
          </Button>
        }
      />

      <Card padding="1rem">
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, alignItems: 'flex-end' }}>
          <div style={{ flex: '1 1 260px', minWidth: 220 }}>
            <Input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search documents…" />
          </div>
          <div style={{ minWidth: 150 }}>
            <Select
              label="Status"
              value={status}
              onChange={(e) => setStatus(e.target.value)}
              options={[
                { value: '', label: 'All' },
                { value: 'draft', label: 'Draft' },
                { value: 'finalized', label: 'Finalized' },
                { value: 'void', label: 'Void' },
              ]}
            />
          </div>
          <Button variant="ghost" size="sm" onClick={() => { setSearch(''); setStatus(''); setPage(1) }}>
            Clear
          </Button>
        </div>
      </Card>

      {error && (
        <Card>
          <p style={{ color: 'var(--hf-danger)' }}>{error}</p>
          <Button variant="outline" size="sm" onClick={reload} style={{ marginTop: 8 }}>Retry</Button>
        </Card>
      )}

      <Card padding={0}>
        <DataTable
          loading={loading}
          columns={[
            {
              key: 'title',
              header: 'Title',
              render: (d: GeneratedDocument) => (
                <div>
                  <Link to={`/app/documents/generated/${d.id}`} style={{ fontWeight: 650, textDecoration: 'none' }}>
                    {d.title}
                  </Link>
                  <div className="hf-subtle" style={{ fontSize: '0.75rem' }}>{d.template_name || 'Ad-hoc'}</div>
                </div>
              ),
            },
            { key: 'candidate', header: 'Candidate', render: (d: GeneratedDocument) => d.related_candidate_name || '—' },
            { key: 'job', header: 'Job', render: (d: GeneratedDocument) => d.related_job_title || '—' },
            { key: 'status', header: 'Status', render: (d: GeneratedDocument) => <Badge status={d.status} /> },
            { key: 'finalized', header: 'Finalized', render: (d: GeneratedDocument) => formatDate(d.finalized_at) },
            { key: 'created', header: 'Created', render: (d: GeneratedDocument) => formatDate(d.created_at) },
          ]}
          rows={data?.results || []}
          rowKey={(d) => d.id}
          emptyTitle="No documents"
          emptyDescription="Generate a document from a template."
          onRowClick={(d) => navigate(`/app/documents/generated/${d.id}`)}
        />
        {data && <Pagination page={page} pageSize={20} total={data.count} onChange={setPage} />}
      </Card>
    </div>
  )
}

export function GeneratedDocumentFormPage() {
  const navigate = useNavigate()
  const { toast } = useToast()
  const [templateId, setTemplateId] = useState('')
  const [title, setTitle] = useState('')
  const [contentText, setContentText] = useState('')
  const [saving, setSaving] = useState(false)
  const templates = useApi(() => documentTemplatesApi.list({ page_size: 100, is_active: true }), [])

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setSaving(true)
    try {
      const doc = await generatedDocumentsApi.create({
        template_id: templateId || null,
        title,
        content_text: contentText,
      })
      toast('Document created', 'success')
      navigate(`/app/documents/generated/${doc.id}`)
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Save failed', 'error')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="hf-page">
      <PageHeader title="New generated document" subtitle="Create a document from a template (or ad-hoc)." />
      <form onSubmit={onSubmit}>
        <Card>
          <div style={{ display: 'grid', gap: 14 }}>
            <Select
              label="Template (optional)"
              value={templateId}
              onChange={(e) => setTemplateId(e.target.value)}
              placeholder="Ad-hoc document"
              options={(templates.data?.results || []).map((t) => ({ value: t.id, label: t.name }))}
            />
            <Input label="Title" required value={title} onChange={(e) => setTitle(e.target.value)} />
            <Textarea
              label="Content (plain text)"
              value={contentText}
              onChange={(e) => setContentText(e.target.value)}
              style={{ minHeight: 160 }}
            />
            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
              <Button type="button" variant="outline" onClick={() => navigate('/app/documents/generated')}>Cancel</Button>
              <Button type="submit" loading={saving}>Create document</Button>
            </div>
          </div>
        </Card>
      </form>
    </div>
  )
}

export function GeneratedDocumentDetailPage() {
  const { id = '' } = useParams()
  const navigate = useNavigate()
  const { toast } = useToast()
  const [tab, setTab] = useState('content')
  const [acting, setActing] = useState(false)
  const [voidOpen, setVoidOpen] = useState(false)
  const [signModal, setSignModal] = useState(false)
  const doc = useApi(() => generatedDocumentsApi.get(id), [id], { enabled: Boolean(id) })
  const signRequests = useApi(
    () => documentSignRequestsApi.list({ document: id, page_size: 50 }),
    [id, tab],
    { enabled: Boolean(id) && tab === 'signatures' },
  )

  async function runAction(action: () => Promise<unknown>, ok: string) {
    setActing(true)
    try {
      await action()
      toast(ok, 'success')
      doc.reload()
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Action failed', 'error')
    } finally {
      setActing(false)
    }
  }

  if (doc.loading) {
    return (
      <div style={{ padding: 64, display: 'grid', placeItems: 'center' }}>
        <Spinner label="Loading document…" />
      </div>
    )
  }

  if (doc.error || !doc.data) {
    return (
      <EmptyState
        title="Document not found"
        description={doc.error || 'This document may have been deleted.'}
        actionLabel="Back to documents"
        onAction={() => navigate('/app/documents/generated')}
      />
    )
  }

  const d = doc.data

  return (
    <div className="hf-page">
      <PageHeader
        title={d.title}
        subtitle={`${d.template_name || 'Ad-hoc'}${d.related_candidate_name ? ` · ${d.related_candidate_name}` : ''}`}
        actions={
          <>
            <Badge status={d.status} />
            {d.status === 'draft' && (
              <Button loading={acting} onClick={() => runAction(() => generatedDocumentsApi.finalize(id), 'Document finalized')}>
                Finalize
              </Button>
            )}
            {d.status !== 'void' && (
              <Button variant="danger" loading={acting} onClick={() => setVoidOpen(true)}>
                Void
              </Button>
            )}
            <Button
              variant="outline"
              leftIcon={<Download size={15} />}
              onClick={() => runAction(() => generatedDocumentsApi.download(id), 'Download started')}
            >
              Download
            </Button>
          </>
        }
      />

      <Tabs
        value={tab}
        onChange={setTab}
        items={[
          { id: 'content', label: 'Content' },
          { id: 'signatures', label: 'Sign requests', count: signRequests.data?.count },
        ]}
      />

      {tab === 'content' && (
        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 16 }}>
          <Card title="Content">
            <div className="hf-muted" style={{ whiteSpace: 'pre-wrap', lineHeight: 1.6, fontSize: '0.88rem' }}>
              {d.content_text || d.content_html || 'No content yet.'}
            </div>
          </Card>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <Card title="Details">
              <dl style={{ display: 'grid', gap: 10, margin: 0, fontSize: '0.88rem' }}>
                <Row label="Status" value={titleCase(d.status)} />
                <Row label="Candidate" value={d.related_candidate_name || '—'} />
                <Row label="Job" value={d.related_job_title || '—'} />
                <Row label="Offer" value={d.related_offer_title || '—'} />
                <Row label="Finalized" value={d.finalized_by_name ? `${d.finalized_by_name} · ${formatDate(d.finalized_at)}` : '—'} />
                <Row label="Created" value={formatDate(d.created_at)} />
              </dl>
            </Card>
            <Button variant="outline" leftIcon={<FileSignature size={15} />} onClick={() => setSignModal(true)} disabled={d.status !== 'finalized'}>
              Create sign request
            </Button>
          </div>
        </div>
      )}

      {tab === 'signatures' && (
        <Card padding={0} title="Sign requests">
          <DataTable
            loading={signRequests.loading}
            columns={[
              { key: 'signer', header: 'Signer', render: (s) => `${s.signer_name} <${s.signer_email}>` },
              { key: 'status', header: 'Status', render: (s) => <Badge status={s.status} /> },
              { key: 'sent', header: 'Sent', render: (s) => formatDate(s.sent_at) },
              { key: 'signed', header: 'Signed', render: (s) => formatDate(s.signed_at) },
              { key: 'signatures', header: 'Signatures', render: (s) => String(s.signature_count || 0) },
            ]}
            rows={signRequests.data?.results || []}
            rowKey={(s) => s.id}
            emptyTitle="No sign requests"
            emptyDescription="Create a sign request to collect an e-signature."
          />
        </Card>
      )}

      <ConfirmDialog
        open={voidOpen}
        title="Void document"
        message={`Void "${d.title}"? It will no longer be usable for signing.`}
        confirmLabel="Void document"
        danger
        loading={acting}
        onCancel={() => setVoidOpen(false)}
        onConfirm={() => {
          setVoidOpen(false)
          void runAction(() => generatedDocumentsApi.void(id), 'Document voided')
        }}
      />
      <SignRequestModal open={signModal} documentId={id} onClose={() => setSignModal(false)} onDone={() => signRequests.reload()} />
    </div>
  )
}

function SignRequestModal({
  open,
  documentId,
  onClose,
  onDone,
}: {
  open: boolean
  documentId: string
  onClose: () => void
  onDone: () => void
}) {
  const { toast } = useToast()
  const [signerName, setSignerName] = useState('')
  const [signerEmail, setSignerEmail] = useState('')
  const [message, setMessage] = useState('')
  const [saving, setSaving] = useState(false)

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setSaving(true)
    try {
      await documentSignRequestsApi.create({ document_id: documentId, signer_name: signerName, signer_email: signerEmail, message })
      toast('Sign request created', 'success')
      onDone()
      onClose()
      setSignerName('')
      setSignerEmail('')
      setMessage('')
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Failed', 'error')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal open={open} onClose={onClose} title="Create sign request">
      <form onSubmit={onSubmit} style={{ display: 'grid', gap: 12 }}>
        <Input label="Signer name" required value={signerName} onChange={(e) => setSignerName(e.target.value)} />
        <Input label="Signer email" required type="email" value={signerEmail} onChange={(e) => setSignerEmail(e.target.value)} />
        <Textarea label="Message (optional)" value={message} onChange={(e) => setMessage(e.target.value)} />
        <Button type="submit" loading={saving}>Create request</Button>
      </form>
    </Modal>
  )
}

// ---------------------------------------------------------------------------
// Sign requests
// ---------------------------------------------------------------------------

export function SignRequestsPage() {
  const { toast } = useToast()
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('')
  const [acting, setActing] = useState<string | null>(null)
  const { data, loading, error, reload } = useApi(
    () =>
      documentSignRequestsApi.list({
        page,
        page_size: 20,
        search: search || undefined,
        status: status || undefined,
      }),
    [page, search, status],
  )

  async function runAction(action: () => Promise<unknown>, id: string, ok: string) {
    setActing(id)
    try {
      await action()
      toast(ok, 'success')
      reload()
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Action failed', 'error')
    } finally {
      setActing(null)
    }
  }

  return (
    <div className="hf-page">
      <PageHeader
        title="Sign requests"
        subtitle="Track e-signature requests sent to candidates and other signers."
      />

      <Card padding="1rem">
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, alignItems: 'flex-end' }}>
          <div style={{ flex: '1 1 260px', minWidth: 220 }}>
            <Input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search by signer…" />
          </div>
          <div style={{ minWidth: 150 }}>
            <Select
              label="Status"
              value={status}
              onChange={(e) => setStatus(e.target.value)}
              options={[
                { value: '', label: 'All' },
                { value: 'pending', label: 'Pending' },
                { value: 'signed', label: 'Signed' },
                { value: 'declined', label: 'Declined' },
                { value: 'voided', label: 'Voided' },
              ]}
            />
          </div>
          <Button variant="ghost" size="sm" onClick={() => { setSearch(''); setStatus(''); setPage(1) }}>
            Clear
          </Button>
        </div>
      </Card>

      {error && (
        <Card>
          <p style={{ color: 'var(--hf-danger)' }}>{error}</p>
          <Button variant="outline" size="sm" onClick={reload} style={{ marginTop: 8 }}>Retry</Button>
        </Card>
      )}

      <Card padding={0}>
        <DataTable
          loading={loading}
          columns={[
            {
              key: 'signer',
              header: 'Signer',
              render: (s) => (
                <div>
                  <div style={{ fontWeight: 650 }}>{s.signer_name}</div>
                  <div className="hf-subtle" style={{ fontSize: '0.75rem' }}>{s.signer_email}</div>
                </div>
              ),
            },
            { key: 'document', header: 'Document', render: (s) => s.document_title },
            { key: 'status', header: 'Status', render: (s) => <Badge status={s.status} /> },
            { key: 'sent', header: 'Sent', render: (s) => formatDateTime(s.sent_at) },
            { key: 'expires', header: 'Expires', render: (s) => formatDate(s.expires_at) },
            {
              key: 'actions',
              header: '',
              render: (s) => (
                <div style={{ display: 'flex', gap: 6 }}>
                  {s.status === 'pending' && (
                    <Button size="sm" leftIcon={<Send size={13} />} loading={acting === s.id} onClick={(e) => { e.stopPropagation(); void runAction(() => documentSignRequestsApi.send(s.id), s.id, 'Sign request sent') }}>
                      Send
                    </Button>
                  )}
                  {s.status === 'pending' && (
                    <Button size="sm" variant="outline" loading={acting === s.id} onClick={(e) => { e.stopPropagation(); void runAction(() => documentSignRequestsApi.resend(s.id), s.id, 'Sign request resent') }}>
                      Resend
                    </Button>
                  )}
                  {s.status !== 'voided' && (
                    <Button size="sm" variant="ghost" loading={acting === s.id} onClick={(e) => { e.stopPropagation(); void runAction(() => documentSignRequestsApi.void(s.id), s.id, 'Sign request voided') }}>
                      Void
                    </Button>
                  )}
                </div>
              ),
            },
          ]}
          rows={data?.results || []}
          rowKey={(s) => s.id}
          emptyTitle="No sign requests"
          emptyDescription="Create a sign request from a finalized document."
        />
        {data && <Pagination page={page} pageSize={20} total={data.count} onChange={setPage} />}
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
