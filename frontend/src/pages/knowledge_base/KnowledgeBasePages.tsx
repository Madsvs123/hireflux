/**
 * Knowledge base pages.
 *
 * Exported components and suggested routes (wire into App.tsx):
 *   - KnowledgeBasePage              -> /app/knowledge
 *   - KnowledgeArticleEditorPage     -> /app/knowledge/new, /app/knowledge/articles/:id/edit
 *   - KnowledgeArticleDetailPage     -> /app/knowledge/articles/:id
 */
import { useEffect, useState, type FormEvent, type ReactNode } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import {
  Archive,
  BookOpen,
  FolderPlus,
  Pencil,
  Plus,
  Send,
  ThumbsDown,
  ThumbsUp,
  Trash2,
} from 'lucide-react'
import {
  knowledgeBaseApi,
  type KnowledgeArticle,
  type KnowledgeArticleVersion,
  type KnowledgeCategory,
  type KnowledgeComment,
} from '../../api/knowledge_base'
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
import { formatDate, formatDateTime } from '../../utils/format'
import { ApiError } from '../../api/http'

// NOTE: the shared <Select> emits option labels as values, so options carry
// display labels and are mapped back to API values on submit.
const ARTICLE_STATUS_OPTIONS = [
  { value: 'Draft', label: 'Draft' },
  { value: 'Published', label: 'Published' },
  { value: 'Archived', label: 'Archived' },
]
const ARTICLE_STATUS_VALUES: Record<string, string> = {
  Draft: 'draft',
  Published: 'published',
  Archived: 'archived',
}

export function KnowledgeBasePage() {
  const navigate = useNavigate()
  const { toast } = useToast()
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('')
  const [categoryId, setCategoryId] = useState('')
  const [categoryOpen, setCategoryOpen] = useState(false)
  const [editingCategory, setEditingCategory] = useState<KnowledgeCategory | null>(null)
  const [deletingCategory, setDeletingCategory] = useState<KnowledgeCategory | null>(null)

  const categories = useApi(() => knowledgeBaseApi.categories.list({ page_size: 100 }), [], {
    enabled: true,
  })
  const articles = useApi(
    () =>
      knowledgeBaseApi.articles.list({
        page,
        page_size: 20,
        search: search || undefined,
        status: status ? ARTICLE_STATUS_VALUES[status] : undefined,
        category: categoryId || undefined,
      }),
    [page, search, status, categoryId],
    { enabled: true },
  )

  return (
    <div className="hf-page">
      <PageHeader
        title="Knowledge base"
        subtitle="Internal wiki for your hiring team — processes, playbooks, and reference material."
        actions={
          <Button leftIcon={<Plus size={16} />} onClick={() => navigate('/app/knowledge/new')}>
            New article
          </Button>
        }
      />
      <div style={{ display: 'grid', gridTemplateColumns: '260px 1fr', gap: 16, alignItems: 'start' }}>
        <Card title="Categories" actions={
          <Button
            variant="ghost"
            size="sm"
            leftIcon={<FolderPlus size={14} />}
            onClick={() => {
              setEditingCategory(null)
              setCategoryOpen(true)
            }}
          >
            Add
          </Button>
        }>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <button
              onClick={() => {
                setCategoryId('')
                setPage(1)
              }}
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                gap: 8,
                padding: '0.5rem 0.6rem',
                borderRadius: 8,
                border: 'none',
                background: categoryId === '' ? 'var(--hf-primary-soft)' : 'transparent',
                color: categoryId === '' ? 'var(--hf-teal-700)' : 'var(--hf-text)',
                fontWeight: categoryId === '' ? 650 : 500,
                cursor: 'pointer',
                textAlign: 'left',
                width: '100%',
                fontSize: '0.88rem',
              }}
            >
              <span>All articles</span>
              <span className="hf-subtle" style={{ fontSize: '0.75rem' }}>
                {articles.data?.count ?? '…'}
              </span>
            </button>
            {(categories.data?.results || []).map((c) => {
              const active = categoryId === c.id
              return (
                <div
                  key={c.id}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    borderRadius: 8,
                    background: active ? 'var(--hf-primary-soft)' : 'transparent',
                  }}
                >
                  <button
                    onClick={() => {
                      setCategoryId(active ? '' : c.id)
                      setPage(1)
                    }}
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      gap: 8,
                      padding: '0.5rem 0.6rem',
                      border: 'none',
                      background: 'transparent',
                      color: active ? 'var(--hf-teal-700)' : 'var(--hf-text)',
                      fontWeight: active ? 650 : 500,
                      cursor: 'pointer',
                      textAlign: 'left',
                      flex: 1,
                      fontSize: '0.88rem',
                    }}
                  >
                    <span>
                      {c.icon ? `${c.icon} ` : ''}
                      {c.name}
                    </span>
                    <span className="hf-subtle" style={{ fontSize: '0.75rem' }}>
                      {c.article_count}
                    </span>
                  </button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      setEditingCategory(c)
                      setCategoryOpen(true)
                    }}
                  >
                    <Pencil size={12} />
                  </Button>
                  <Button variant="ghost" size="sm" onClick={() => setDeletingCategory(c)}>
                    <Trash2 size={12} />
                  </Button>
                </div>
              )
            })}
            {!categories.data?.results?.length && (
              <p className="hf-muted" style={{ fontSize: '0.85rem', padding: '0.5rem 0' }}>
                No categories yet.
              </p>
            )}
          </div>
        </Card>

        <div style={{ display: 'grid', gap: 16 }}>
          <Card padding="1rem">
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, alignItems: 'flex-end' }}>
              <div style={{ flex: '1 1 220px', minWidth: 200 }}>
                <Input
                  value={search}
                  onChange={(e) => {
                    setPage(1)
                    setSearch(e.target.value)
                  }}
                  placeholder="Search articles…"
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
                  options={[{ value: '', label: 'All' }, ...ARTICLE_STATUS_OPTIONS]}
                />
              </div>
              <div style={{ display: 'flex', gap: 8, marginLeft: 'auto' }}>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    setSearch('')
                    setStatus('')
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
              loading={articles.loading}
              columns={[
                {
                  key: 'title',
                  header: 'Article',
                  render: (a: KnowledgeArticle) => (
                    <div>
                      <Link
                        to={`/app/knowledge/articles/${a.id}`}
                        style={{ fontWeight: 650, textDecoration: 'none' }}
                      >
                        {a.title}
                      </Link>
                      <div className="hf-subtle" style={{ fontSize: '0.75rem' }}>
                        {a.category_name || 'Uncategorized'}
                        {a.summary ? ` · ${a.summary.slice(0, 80)}` : ''}
                      </div>
                    </div>
                  ),
                },
                {
                  key: 'status',
                  header: 'Status',
                  render: (a: KnowledgeArticle) => <Badge status={a.status} />,
                },
                { key: 'views', header: 'Views', render: (a: KnowledgeArticle) => a.view_count },
                {
                  key: 'votes',
                  header: 'Votes',
                  render: (a: KnowledgeArticle) => a.vote_count,
                },
                {
                  key: 'published',
                  header: 'Published',
                  render: (a: KnowledgeArticle) => formatDate(a.published_at),
                },
              ]}
              rows={articles.data?.results || []}
              rowKey={(a) => a.id}
              emptyTitle="No articles"
              emptyDescription="Write the first article for your hiring team."
              onRowClick={(a) => navigate(`/app/knowledge/articles/${a.id}`)}
            />
            {articles.data && (
              <Pagination page={page} pageSize={20} total={articles.data.count} onChange={setPage} />
            )}
          </Card>
        </div>
      </div>

      <CategoryFormModal
        open={categoryOpen}
        editing={editingCategory}
        onClose={() => setCategoryOpen(false)}
        onSaved={() => {
          categories.reload()
          setCategoryOpen(false)
        }}
      />
      <ConfirmDialog
        open={Boolean(deletingCategory)}
        title="Delete category"
        message={`Delete "${deletingCategory?.name}"? Articles in it will not be deleted.`}
        confirmLabel="Delete"
        danger
        onCancel={() => setDeletingCategory(null)}
        onConfirm={() => {
          if (!deletingCategory) return
          knowledgeBaseApi.categories
            .remove(deletingCategory.id)
            .then(() => {
              toast('Category deleted', 'success')
              categories.reload()
            })
            .catch((err: unknown) =>
              toast(err instanceof ApiError ? err.message : 'Delete failed', 'error'),
            )
            .finally(() => setDeletingCategory(null))
        }}
      />
    </div>
  )
}

function CategoryFormModal({
  open,
  editing,
  onClose,
  onSaved,
}: {
  open: boolean
  editing: KnowledgeCategory | null
  onClose: () => void
  onSaved: () => void
}) {
  const { toast } = useToast()
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [icon, setIcon] = useState('')
  const [order, setOrder] = useState(0)
  const [isActive, setIsActive] = useState(true)
  const [saving, setSaving] = useState(false)
  const [seed, setSeed] = useState('')

  if (open && seed !== (editing?.id || 'new')) {
    setSeed(editing?.id || 'new')
    setName(editing?.name || '')
    setDescription(editing?.description || '')
    setIcon(editing?.icon || '')
    setOrder(editing?.order ?? 0)
    setIsActive(editing?.is_active ?? true)
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setSaving(true)
    const payload = {
      name,
      description,
      icon: icon || null,
      order: Number(order) || 0,
      is_active: isActive,
    }
    try {
      if (editing) {
        await knowledgeBaseApi.categories.update(editing.id, payload)
        toast('Category updated', 'success')
      } else {
        await knowledgeBaseApi.categories.create(payload)
        toast('Category created', 'success')
      }
      onSaved()
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Save failed', 'error')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal open={open} onClose={onClose} title={editing ? 'Edit category' : 'New category'}>
      <form onSubmit={onSubmit} style={{ display: 'grid', gap: 12 }}>
        <Input label="Name" required value={name} onChange={(e) => setName(e.target.value)} />
        <Textarea
          label="Description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          <Input
            label="Icon (emoji or key)"
            value={icon}
            onChange={(e) => setIcon(e.target.value)}
            placeholder="📚"
          />
          <Input
            label="Order"
            type="number"
            value={order}
            onChange={(e) => setOrder(Number(e.target.value))}
          />
        </div>
        <label style={{ display: 'flex', gap: 8, alignItems: 'center', fontSize: '0.88rem' }}>
          <input
            type="checkbox"
            checked={isActive}
            onChange={(e) => setIsActive(e.target.checked)}
          />
          Active category
        </label>
        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
          <Button type="button" variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={saving}>
            {editing ? 'Save changes' : 'Create category'}
          </Button>
        </div>
      </form>
    </Modal>
  )
}

export function KnowledgeArticleEditorPage() {
  const { id } = useParams()
  const isEdit = Boolean(id)
  const navigate = useNavigate()
  const { toast } = useToast()
  const [saving, setSaving] = useState(false)
  const [loading, setLoading] = useState(isEdit)
  const categories = useApi(() => knowledgeBaseApi.categories.list({ page_size: 100 }), [], {
    enabled: true,
  })
  const [form, setForm] = useState({
    category: '',
    title: '',
    summary: '',
    body_html: '',
    status: 'Draft',
  })

  function set<K extends keyof typeof form>(key: K, value: (typeof form)[K]) {
    setForm((f) => ({ ...f, [key]: value }))
  }

  useEffect(() => {
    if (!id) return
    setLoading(true)
    knowledgeBaseApi.articles
      .get(id)
      .then((a) => {
        setForm({
          category: a.category,
          title: a.title,
          summary: a.summary || '',
          body_html: a.body_html || '',
          status: a.status === 'published' ? 'Published' : a.status === 'archived' ? 'Archived' : 'Draft',
        })
      })
      .catch((err: unknown) =>
        toast(err instanceof ApiError ? err.message : 'Failed to load article', 'error'),
      )
      .finally(() => setLoading(false))
  }, [id, toast])

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setSaving(true)
    const payload = {
      category: form.category || null,
      title: form.title,
      summary: form.summary,
      body_html: form.body_html,
      status: ARTICLE_STATUS_VALUES[form.status] || form.status,
    }
    try {
      const saved = isEdit
        ? await knowledgeBaseApi.articles.update(id!, payload)
        : await knowledgeBaseApi.articles.create(payload)
      toast(isEdit ? 'Article updated' : 'Article created', 'success')
      navigate(`/app/knowledge/articles/${saved.id}`)
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
        title={isEdit ? 'Edit article' : 'New article'}
        subtitle="Write internal documentation for your hiring team."
      />
      <form onSubmit={onSubmit}>
        <Card>
          <div style={{ display: 'grid', gap: 14 }}>
            <Input label="Title" required value={form.title} onChange={(e) => set('title', e.target.value)} />
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              <Select
                label="Category"
                value={form.category}
                onChange={(e) => set('category', e.target.value)}
                placeholder="Select category"
                options={(categories.data?.results || []).map((c) => ({ value: c.id, label: c.name }))}
              />
              <Select
                label="Status"
                value={form.status}
                onChange={(e) => set('status', e.target.value)}
                options={ARTICLE_STATUS_OPTIONS}
              />
            </div>
            <Input
              label="Summary"
              value={form.summary}
              onChange={(e) => set('summary', e.target.value)}
              placeholder="Short description shown in lists"
            />
            <Textarea
              label="Body (HTML)"
              value={form.body_html}
              onChange={(e) => set('body_html', e.target.value)}
              style={{ minHeight: 320, fontFamily: 'monospace', fontSize: '0.85rem' }}
              placeholder="<h2>Process</h2><p>Write the article content in HTML…</p>"
            />
            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
              <Button type="button" variant="outline" onClick={() => navigate(-1)}>
                Cancel
              </Button>
              <Button type="submit" loading={saving}>
                {isEdit ? 'Save changes' : 'Create article'}
              </Button>
            </div>
          </div>
        </Card>
      </form>
    </div>
  )
}

export function KnowledgeArticleDetailPage() {
  const { id = '' } = useParams()
  const navigate = useNavigate()
  const { toast } = useToast()
  const [tab, setTab] = useState('content')
  const [acting, setActing] = useState(false)
  const [voting, setVoting] = useState(false)
  const [comment, setComment] = useState('')
  const [commentSaving, setCommentSaving] = useState(false)
  const [restoreOpen, setRestoreOpen] = useState(false)
  const [restoreVersionId, setRestoreVersionId] = useState('')
  const [diffOpen, setDiffOpen] = useState(false)
  const [diffA, setDiffA] = useState('')
  const [diffB, setDiffB] = useState('')
  const [diffResult, setDiffResult] = useState<{
    from_version: number
    to_version: number
    title_diff: string[]
    body_diff: string[]
  } | null>(null)
  const [attachmentOpen, setAttachmentOpen] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)

  const article = useApi(() => knowledgeBaseApi.articles.get(id), [id], { enabled: Boolean(id) })
  const comments = useApi(
    () => knowledgeBaseApi.comments.list({ article: id, page_size: 100 }),
    [id, tab],
    { enabled: Boolean(id) && tab === 'comments' },
  )
  const versions = useApi(
    () => knowledgeBaseApi.articles.versions(id),
    [id, tab],
    { enabled: Boolean(id) && tab === 'versions' },
  )
  const attachments = useApi(
    () => knowledgeBaseApi.attachments.list({ article: id, page_size: 100 }),
    [id, tab],
    { enabled: Boolean(id) && tab === 'attachments' },
  )

  // Bump the view counter once per page visit (fire-and-forget).
  useEffect(() => {
    if (!id) return
    knowledgeBaseApi.articles.incrementView(id).catch(() => undefined)
  }, [id])

  async function runAction(action: () => Promise<unknown>, ok: string) {
    setActing(true)
    try {
      await action()
      toast(ok, 'success')
      article.reload()
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Action failed', 'error')
    } finally {
      setActing(false)
    }
  }

  async function vote(helpful: boolean) {
    setVoting(true)
    try {
      await knowledgeBaseApi.votes.toggle({ article_id: id, helpful })
      toast(helpful ? 'Marked helpful' : 'Marked not helpful', 'success')
      article.reload()
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Vote failed', 'error')
    } finally {
      setVoting(false)
    }
  }

  async function addComment(e: FormEvent) {
    e.preventDefault()
    if (!comment.trim()) return
    setCommentSaving(true)
    try {
      await knowledgeBaseApi.comments.create({ article: id, body: comment })
      setComment('')
      toast('Comment added', 'success')
      comments.reload()
      article.reload()
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Comment failed', 'error')
    } finally {
      setCommentSaving(false)
    }
  }

  async function restoreVersion() {
    if (!restoreVersionId) return
    try {
      await knowledgeBaseApi.articles.restoreVersion(id, { version_id: restoreVersionId })
      toast('Version restored', 'success')
      article.reload()
      versions.reload()
      setRestoreOpen(false)
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Restore failed', 'error')
    }
  }

  async function runDiff() {
    if (!diffA || !diffB) return
    try {
      const res = await knowledgeBaseApi.articles.diff(id, { version_a: diffA, version_b: diffB })
      setDiffResult(res)
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Diff failed', 'error')
    }
  }

  if (article.loading) {
    return (
      <div style={{ padding: 64, display: 'grid', placeItems: 'center' }}>
        <Spinner label="Loading article…" />
      </div>
    )
  }
  if (article.error || !article.data) {
    return (
      <EmptyState
        title="Article not found"
        description={article.error || 'This article may have been deleted.'}
        actionLabel="Back to knowledge base"
        onAction={() => navigate('/app/knowledge')}
      />
    )
  }

  const a = article.data

  return (
    <div className="hf-page">
      <PageHeader
        title={a.title}
        subtitle={a.category_name || 'Uncategorized'}
        breadcrumbs={[{ label: 'Knowledge base', to: '/app/knowledge' }, { label: a.title }]}
        actions={
          <>
            <Badge status={a.status} />
            <Button variant="outline" onClick={() => navigate(`/app/knowledge/articles/${id}/edit`)}>
              Edit
            </Button>
            {a.status === 'draft' && (
              <Button
                loading={acting}
                leftIcon={<Send size={14} />}
                onClick={() => runAction(() => knowledgeBaseApi.articles.publish(id), 'Article published')}
              >
                Publish
              </Button>
            )}
            {a.status !== 'archived' && (
              <Button
                variant="outline"
                loading={acting}
                leftIcon={<Archive size={14} />}
                onClick={() => runAction(() => knowledgeBaseApi.articles.archive(id), 'Article archived')}
              >
                Archive
              </Button>
            )}
            <Button variant="danger" onClick={() => setConfirmDelete(true)}>
              Delete
            </Button>
          </>
        }
      />

      <Tabs
        value={tab}
        onChange={setTab}
        items={[
          { id: 'content', label: 'Content' },
          { id: 'comments', label: 'Comments', count: a.comment_count },
          { id: 'versions', label: 'Versions', count: versions.data?.length },
          { id: 'attachments', label: 'Attachments', count: attachments.data?.count },
        ]}
      />

      {tab === 'content' && (
        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 16 }}>
          <Card title="Article">
            {a.summary && (
              <p className="hf-muted" style={{ fontStyle: 'italic', marginTop: 0 }}>
                {a.summary}
              </p>
            )}
            <div
              className="hf-prose"
              style={{ lineHeight: 1.65 }}
              dangerouslySetInnerHTML={{ __html: a.body_html || '<p>No content yet.</p>' }}
            />
          </Card>
          <div style={{ display: 'grid', gap: 12, alignContent: 'start' }}>
            <Card title="Stats">
              <dl style={{ display: 'grid', gap: 10, margin: 0, fontSize: '0.88rem' }}>
                <Row label="Views" value={String(a.view_count)} />
                <Row label="Votes" value={String(a.vote_count)} />
                <Row label="Published by" value={a.published_by_name || '—'} />
                <Row label="Published" value={formatDateTime(a.published_at)} />
              </dl>
            </Card>
            <Card title="Was this helpful?">
              <div style={{ display: 'flex', gap: 8 }}>
                <Button
                  variant="outline"
                  size="sm"
                  loading={voting}
                  leftIcon={<ThumbsUp size={14} />}
                  onClick={() => void vote(true)}
                >
                  Helpful
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  loading={voting}
                  leftIcon={<ThumbsDown size={14} />}
                  onClick={() => void vote(false)}
                >
                  Not helpful
                </Button>
              </div>
            </Card>
          </div>
        </div>
      )}

      {tab === 'comments' && (
        <Card title="Comments">
          <form onSubmit={addComment} style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
            <Input
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              placeholder="Add a comment…"
            />
            <Button type="submit" loading={commentSaving} leftIcon={<Send size={14} />}>
              Comment
            </Button>
          </form>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {(comments.data?.results || []).map((c: KnowledgeComment) => (
              <div
                key={c.id}
                style={{
                  padding: 12,
                  borderRadius: 10,
                  border: '1px solid var(--hf-border)',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
                  <span style={{ fontWeight: 600, fontSize: '0.88rem' }}>
                    {c.author_name || '—'}
                  </span>
                  <span className="hf-subtle" style={{ fontSize: '0.75rem' }}>
                    {formatDateTime(c.created_at)}
                  </span>
                </div>
                <p className="hf-muted" style={{ marginTop: 6, marginBottom: 0, fontSize: '0.9rem' }}>
                  {c.body}
                </p>
              </div>
            ))}
            {!comments.data?.results?.length && (
              <EmptyState title="No comments yet" description="Start the discussion." />
            )}
          </div>
        </Card>
      )}

      {tab === 'versions' && (
        <Card padding={0}>
          <CardHeader
            title="Version history"
            actions={
              <>
                <Button
                  variant="outline"
                  size="sm"
                  leftIcon={<BookOpen size={14} />}
                  onClick={() => {
                    setDiffResult(null)
                    setDiffOpen(true)
                  }}
                >
                  Diff versions
                </Button>
                <Button
                  size="sm"
                  onClick={() => {
                    setRestoreVersionId('')
                    setRestoreOpen(true)
                  }}
                >
                  Restore version
                </Button>
              </>
            }
          />
          <DataTable
            loading={versions.loading}
            columns={[
              {
                key: 'version',
                header: 'Version',
                render: (v: KnowledgeArticleVersion) => `v${v.version_number}`,
              },
              { key: 'title', header: 'Title', render: (v: KnowledgeArticleVersion) => v.title },
              {
                key: 'note',
                header: 'Change note',
                render: (v: KnowledgeArticleVersion) => v.change_note || '—',
              },
              {
                key: 'by',
                header: 'By',
                render: (v: KnowledgeArticleVersion) => v.created_by_name || '—',
              },
              {
                key: 'at',
                header: 'Saved',
                render: (v: KnowledgeArticleVersion) => formatDateTime(v.created_at),
              },
            ]}
            rows={versions.data || []}
            rowKey={(v) => v.id}
            emptyTitle="No versions"
            emptyDescription="Versions are snapshotted automatically when an article is created or updated."
          />
        </Card>
      )}

      {tab === 'attachments' && (
        <Card padding={0}>
          <CardHeader
            title="Attachments"
            actions={
              <Button size="sm" leftIcon={<Plus size={14} />} onClick={() => setAttachmentOpen(true)}>
                Upload
              </Button>
            }
          />
          <DataTable
            loading={attachments.loading}
            columns={[
              { key: 'name', header: 'Name', render: (x) => x.name },
              {
                key: 'size',
                header: 'Size',
                render: (x) => (x.size != null ? `${Math.round(x.size / 1024)} KB` : '—'),
              },
              { key: 'by', header: 'Uploaded by', render: (x) => x.uploaded_by_name || '—' },
              { key: 'at', header: 'Uploaded', render: (x) => formatDateTime(x.created_at) },
              {
                key: 'actions',
                header: '',
                render: (x) => (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={(e) => {
                      e.stopPropagation()
                      knowledgeBaseApi.attachments
                        .remove(x.id)
                        .then(() => {
                          toast('Attachment removed', 'success')
                          attachments.reload()
                        })
                        .catch((err: unknown) =>
                          toast(err instanceof ApiError ? err.message : 'Delete failed', 'error'),
                        )
                    }}
                  >
                    <Trash2 size={14} />
                  </Button>
                ),
              },
            ]}
            rows={attachments.data?.results || []}
            rowKey={(x) => x.id}
            emptyTitle="No attachments"
          />
        </Card>
      )}

      <Modal open={restoreOpen} onClose={() => setRestoreOpen(false)} title="Restore version">
        <div style={{ display: 'grid', gap: 12 }}>
          <Select
            label="Version"
            value={restoreVersionId}
            onChange={(e) => setRestoreVersionId(e.target.value)}
            placeholder="Select version"
            options={(versions.data || []).map((v) => ({
              value: v.id,
              label: `v${v.version_number} — ${v.change_note || v.title}`,
            }))}
          />
          <p className="hf-muted" style={{ fontSize: '0.85rem' }}>
            Restoring will replace the current title and body with this version. A new version
            snapshot is created automatically.
          </p>
          <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
            <Button variant="outline" onClick={() => setRestoreOpen(false)}>
              Cancel
            </Button>
            <Button onClick={() => void restoreVersion()}>Restore</Button>
          </div>
        </div>
      </Modal>

      <Modal open={diffOpen} onClose={() => setDiffOpen(false)} title="Diff versions" width={720}>
        <div style={{ display: 'grid', gap: 12 }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <Select
              label="Version A"
              value={diffA}
              onChange={(e) => {
                setDiffA(e.target.value)
                setDiffResult(null)
              }}
              placeholder="Select version"
              options={(versions.data || []).map((v) => ({
                value: v.id,
                label: `v${v.version_number}`,
              }))}
            />
            <Select
              label="Version B"
              value={diffB}
              onChange={(e) => {
                setDiffB(e.target.value)
                setDiffResult(null)
              }}
              placeholder="Select version"
              options={(versions.data || []).map((v) => ({
                value: v.id,
                label: `v${v.version_number}`,
              }))}
            />
          </div>
          <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
            <Button onClick={() => void runDiff()}>Show diff</Button>
          </div>
          {diffResult && (
            <div style={{ display: 'grid', gap: 8 }}>
              <div>
                <strong style={{ fontSize: '0.85rem' }}>Title diff</strong>
                <pre className="hf-muted" style={{ fontSize: '0.75rem', whiteSpace: 'pre-wrap' }}>
                  {diffResult.title_diff.join('\n') || 'No title changes'}
                </pre>
              </div>
              <div>
                <strong style={{ fontSize: '0.85rem' }}>Body diff</strong>
                <pre
                  className="hf-muted"
                  style={{
                    fontSize: '0.75rem',
                    whiteSpace: 'pre-wrap',
                    maxHeight: 320,
                    overflow: 'auto',
                  }}
                >
                  {diffResult.body_diff.join('\n') || 'No body changes'}
                </pre>
              </div>
            </div>
          )}
        </div>
      </Modal>

      <AttachmentUploadModal
        open={attachmentOpen}
        articleId={id}
        onClose={() => setAttachmentOpen(false)}
        onSaved={() => {
          attachments.reload()
          setAttachmentOpen(false)
        }}
      />

      <ConfirmDialog
        open={confirmDelete}
        title="Delete article"
        message={`Delete "${a.title}"? This removes the article and its versions.`}
        confirmLabel="Delete"
        danger
        onCancel={() => setConfirmDelete(false)}
        onConfirm={() => {
          knowledgeBaseApi.articles
            .remove(id)
            .then(() => {
              toast('Article deleted', 'success')
              navigate('/app/knowledge')
            })
            .catch((err: unknown) =>
              toast(err instanceof ApiError ? err.message : 'Delete failed', 'error'),
            )
            .finally(() => setConfirmDelete(false))
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

function AttachmentUploadModal({
  open,
  articleId,
  onClose,
  onSaved,
}: {
  open: boolean
  articleId: string
  onClose: () => void
  onSaved: () => void
}) {
  const { toast } = useToast()
  const [name, setName] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [saving, setSaving] = useState(false)

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    if (!file) {
      toast('Choose a file to upload', 'error')
      return
    }
    setSaving(true)
    const form = new FormData()
    form.append('article', articleId)
    form.append('name', name || file.name)
    form.append('file', file)
    try {
      await knowledgeBaseApi.attachments.upload(form)
      toast('Attachment uploaded', 'success')
      setName('')
      setFile(null)
      onSaved()
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Upload failed', 'error')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal open={open} onClose={onClose} title="Upload attachment">
      <form onSubmit={onSubmit} style={{ display: 'grid', gap: 12 }}>
        <Input
          label="Name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Defaults to file name"
        />
        <label style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--hf-text-muted)' }}>
            File
          </span>
          <input
            type="file"
            required
            onChange={(e) => setFile(e.target.files?.[0] || null)}
            style={{ fontSize: '0.85rem' }}
          />
        </label>
        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
          <Button type="button" variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={saving}>
            Upload
          </Button>
        </div>
      </form>
    </Modal>
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
