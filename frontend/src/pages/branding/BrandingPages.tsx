/**
 * BrandingPages.tsx — Employer branding frontend.
 *
 * Exported components & suggested routes (wired by main agent in App.tsx):
 *   BrandingPage        → /app/branding
 *   CulturePostFormPage → /app/branding/culture/new, /app/branding/culture/:id/edit
 */
import { useEffect, useState, type FormEvent } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { Archive, Globe, Palette, Pencil, Plus, Send, Star, Trash2, Users } from 'lucide-react'
import { brandingApi } from '../../api/employer_branding'
import type { BrandProfile, CareerSiteConfig, CulturePost, TeamPage, Testimonial } from '../../api/employer_branding'
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
  Select,
  Spinner,
  Tabs,
  Textarea,
  useToast,
} from '../../components/ui'
import { formatDate, titleCase } from '../../utils/format'
import { ApiError } from '../../api/http'

export function BrandingPage() {
  const [tab, setTab] = useState('profile')

  return (
    <div className="hf-page">
      <PageHeader
        title="Employer branding"
        subtitle="Shape your public careers site: brand identity, team, testimonials, and culture content."
      />
      <Tabs
        value={tab}
        onChange={setTab}
        items={[
          { id: 'profile', label: 'Brand profile', icon: <Palette size={14} /> },
          { id: 'career_site', label: 'Career site', icon: <Globe size={14} /> },
          { id: 'team', label: 'Team', icon: <Users size={14} /> },
          { id: 'testimonials', label: 'Testimonials', icon: <Star size={14} /> },
          { id: 'culture', label: 'Culture posts', icon: <Send size={14} /> },
        ]}
      />
      {tab === 'profile' && <ProfileEditor />}
      {tab === 'career_site' && <CareerSiteEditor />}
      {tab === 'team' && <TeamTab />}
      {tab === 'testimonials' && <TestimonialsTab />}
      {tab === 'culture' && <CulturePostsTab />}
    </div>
  )
}

function ProfileEditor() {
  const { toast } = useToast()
  const profile = useApi(() => brandingApi.getProfile(), [], { enabled: true })
  const [form, setForm] = useState({
    primary_color: '#2563EB',
    secondary_color: '#0F172A',
    tagline: '',
    about_html: '',
    culture_values: '',
  })
  const [saving, setSaving] = useState(false)
  const [acting, setActing] = useState(false)

  useEffect(() => {
    if (!profile.data) return
    setForm({
      primary_color: profile.data.primary_color,
      secondary_color: profile.data.secondary_color,
      tagline: profile.data.tagline || '',
      about_html: profile.data.about_html || '',
      culture_values: (profile.data.culture_values || []).join(', '),
    })
  }, [profile.data])

  function set<K extends keyof typeof form>(key: K, value: (typeof form)[K]) {
    setForm((f) => ({ ...f, [key]: value }))
  }

  async function onSave(e: FormEvent) {
    e.preventDefault()
    setSaving(true)
    try {
      await brandingApi.saveProfile({
        primary_color: form.primary_color,
        secondary_color: form.secondary_color,
        tagline: form.tagline,
        about_html: form.about_html,
        culture_values: form.culture_values
          .split(',')
          .map((s) => s.trim())
          .filter(Boolean),
      })
      toast('Brand profile saved', 'success')
      profile.reload()
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Save failed', 'error')
    } finally {
      setSaving(false)
    }
  }

  async function togglePublish() {
    setActing(true)
    try {
      if (profile.data?.is_published) {
        await brandingApi.unpublishProfile()
        toast('Profile unpublished', 'success')
      } else {
        await brandingApi.publishProfile()
        toast('Profile published', 'success')
      }
      profile.reload()
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Action failed', 'error')
    } finally {
      setActing(false)
    }
  }

  if (profile.loading) {
    return (
      <div style={{ padding: 48, display: 'grid', placeItems: 'center' }}>
        <Spinner />
      </div>
    )
  }

  return (
    <form onSubmit={onSave}>
      <Card
        title="Brand profile"
        subtitle="Identity used across the public careers site."
        actions={
          <Badge tone={profile.data?.is_published ? 'success' : 'neutral'}>
            {profile.data?.is_published ? 'Published' : 'Draft'}
          </Badge>
        }
      >
        {profile.error && !profile.data && (
          <p className="hf-muted" style={{ marginBottom: 12, fontSize: '0.85rem' }}>
            No profile yet — fill this in and save to create one.
          </p>
        )}
        <div style={{ display: 'grid', gap: 14 }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <Input label="Primary color" value={form.primary_color} onChange={(e) => set('primary_color', e.target.value)} />
            <Input label="Secondary color" value={form.secondary_color} onChange={(e) => set('secondary_color', e.target.value)} />
          </div>
          <Input label="Tagline" value={form.tagline} onChange={(e) => set('tagline', e.target.value)} />
          <Textarea label="About (HTML)" value={form.about_html} onChange={(e) => set('about_html', e.target.value)} />
          <Input
            label="Culture values (comma-separated)"
            value={form.culture_values}
            onChange={(e) => set('culture_values', e.target.value)}
          />
          <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
            <Button type="button" variant="outline" loading={acting} onClick={() => void togglePublish()}>
              {profile.data?.is_published ? 'Unpublish' : 'Publish'}
            </Button>
            <Button type="submit" loading={saving}>
              Save profile
            </Button>
          </div>
        </div>
      </Card>
    </form>
  )
}

function CareerSiteEditor() {
  const { toast } = useToast()
  const config = useApi(() => brandingApi.getCareerSite(), [], { enabled: true })
  const [form, setForm] = useState({
    site_name: 'Careers',
    slug: '',
    enabled: false,
    hero_title: '',
    hero_subtitle: '',
    footer_text: '',
    custom_css: '',
  })
  const [saving, setSaving] = useState(false)
  const [acting, setActing] = useState(false)

  useEffect(() => {
    if (!config.data) return
    setForm({
      site_name: config.data.site_name,
      slug: config.data.slug,
      enabled: config.data.enabled,
      hero_title: config.data.hero_title || '',
      hero_subtitle: config.data.hero_subtitle || '',
      footer_text: config.data.footer_text || '',
      custom_css: config.data.custom_css || '',
    })
  }, [config.data])

  function set<K extends keyof typeof form>(key: K, value: (typeof form)[K]) {
    setForm((f) => ({ ...f, [key]: value }))
  }

  async function onSave(e: FormEvent) {
    e.preventDefault()
    setSaving(true)
    try {
      await brandingApi.saveCareerSite({
        site_name: form.site_name,
        slug: form.slug,
        enabled: form.enabled,
        hero_title: form.hero_title,
        hero_subtitle: form.hero_subtitle,
        footer_text: form.footer_text,
        custom_css: form.custom_css,
      })
      toast('Career site saved', 'success')
      config.reload()
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Save failed', 'error')
    } finally {
      setSaving(false)
    }
  }

  async function onPublish() {
    setActing(true)
    try {
      await brandingApi.publishCareerSite()
      toast('Career site published', 'success')
      config.reload()
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Action failed', 'error')
    } finally {
      setActing(false)
    }
  }

  if (config.loading) {
    return (
      <div style={{ padding: 48, display: 'grid', placeItems: 'center' }}>
        <Spinner />
      </div>
    )
  }

  return (
    <form onSubmit={onSave}>
      <Card
        title="Career site"
        subtitle="Configuration for your public careers site."
        actions={
          config.data?.slug ? (
            <Link to={`/careers/${config.data.slug}`} style={{ fontSize: '0.85rem' }}>
              /careers/{config.data.slug}
            </Link>
          ) : undefined
        }
      >
        <div style={{ display: 'grid', gap: 14 }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <Input label="Site name" required value={form.site_name} onChange={(e) => set('site_name', e.target.value)} />
            <Input label="Slug" required value={form.slug} onChange={(e) => set('slug', e.target.value)} />
          </div>
          <Input label="Hero title" value={form.hero_title} onChange={(e) => set('hero_title', e.target.value)} />
          <Input label="Hero subtitle" value={form.hero_subtitle} onChange={(e) => set('hero_subtitle', e.target.value)} />
          <Input label="Footer text" value={form.footer_text} onChange={(e) => set('footer_text', e.target.value)} />
          <Textarea label="Custom CSS" value={form.custom_css} onChange={(e) => set('custom_css', e.target.value)} />
          <label style={{ display: 'flex', gap: 8, alignItems: 'center', fontSize: '0.88rem' }}>
            <input type="checkbox" checked={form.enabled} onChange={(e) => set('enabled', e.target.checked)} />
            Site enabled (publicly accessible)
          </label>
          <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
            <Button type="button" variant="outline" loading={acting} onClick={() => void onPublish()}>
              Publish site
            </Button>
            <Button type="submit" loading={saving}>
              Save config
            </Button>
          </div>
        </div>
      </Card>
    </form>
  )
}

function TeamTab() {
  const { toast } = useToast()
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [open, setOpen] = useState(false)
  const [editing, setEditing] = useState<TeamPage | null>(null)
  const [deleting, setDeleting] = useState<TeamPage | null>(null)
  const [saving, setSaving] = useState(false)
  const team = useApi(
    () => brandingApi.listTeam({ page, page_size: 20, search: search || undefined }),
    [page, search, open],
    { enabled: true },
  )
  const [form, setForm] = useState({ name: '', role: '', bio: '', order: 0, is_active: true })

  function openCreate() {
    setEditing(null)
    setForm({ name: '', role: '', bio: '', order: 0, is_active: true })
    setOpen(true)
  }

  function openEdit(m: TeamPage) {
    setEditing(m)
    setForm({ name: m.name, role: m.role, bio: m.bio, order: m.order, is_active: m.is_active })
    setOpen(true)
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setSaving(true)
    try {
      if (editing) {
        await brandingApi.updateTeam(editing.id, form)
        toast('Team member updated', 'success')
      } else {
        await brandingApi.createTeam(form)
        toast('Team member added', 'success')
      }
      setOpen(false)
      team.reload()
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Save failed', 'error')
    } finally {
      setSaving(false)
    }
  }

  async function onDelete() {
    if (!deleting) return
    setSaving(true)
    try {
      await brandingApi.removeTeam(deleting.id)
      toast('Team member removed', 'success')
      setDeleting(null)
      team.reload()
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Delete failed', 'error')
    } finally {
      setSaving(false)
    }
  }

  return (
    <>
      <Card
        padding={0}
        title="Team"
        actions={
          <Button size="sm" leftIcon={<Plus size={14} />} onClick={openCreate}>
            Add member
          </Button>
        }
      >
        <DataTable
          loading={team.loading}
          columns={[
            {
              key: 'name',
              header: 'Member',
              render: (m: TeamPage) => (
                <div>
                  <div style={{ fontWeight: 600 }}>{m.name}</div>
                  <div className="hf-subtle" style={{ fontSize: '0.75rem' }}>{m.role || '—'}</div>
                </div>
              ),
            },
            { key: 'order', header: 'Order', render: (m: TeamPage) => m.order },
            {
              key: 'active',
              header: 'Active',
              render: (m: TeamPage) => <Badge tone={m.is_active ? 'success' : 'neutral'}>{m.is_active ? 'Yes' : 'No'}</Badge>,
            },
            {
              key: 'actions',
              header: '',
              render: (m: TeamPage) => (
                <div style={{ display: 'flex', gap: 6, justifyContent: 'flex-end' }}>
                  <Button size="sm" variant="ghost" onClick={() => openEdit(m)} aria-label="Edit">
                    <Pencil size={14} />
                  </Button>
                  <Button size="sm" variant="ghost" onClick={() => setDeleting(m)} aria-label="Delete">
                    <Trash2 size={14} />
                  </Button>
                </div>
              ),
            },
          ]}
          rows={team.data?.results || []}
          rowKey={(m) => m.id}
          emptyTitle="No team members"
          emptyDescription="Add team profiles to showcase on your careers site."
        />
      </Card>
      <Modal open={open} onClose={() => setOpen(false)} title={editing ? 'Edit team member' : 'Add team member'}>
        <form onSubmit={onSubmit} style={{ display: 'grid', gap: 12 }}>
          <Input label="Name" required value={form.name} onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))} />
          <Input label="Role" value={form.role} onChange={(e) => setForm((f) => ({ ...f, role: e.target.value }))} />
          <Textarea label="Bio" value={form.bio} onChange={(e) => setForm((f) => ({ ...f, bio: e.target.value }))} />
          <Input label="Order" type="number" min={0} value={form.order} onChange={(e) => setForm((f) => ({ ...f, order: Number(e.target.value) || 0 }))} />
          <label style={{ display: 'flex', gap: 8, alignItems: 'center', fontSize: '0.88rem' }}>
            <input type="checkbox" checked={form.is_active} onChange={(e) => setForm((f) => ({ ...f, is_active: e.target.checked }))} />
            Active on careers site
          </label>
          <Button type="submit" loading={saving}>
            {editing ? 'Save changes' : 'Add member'}
          </Button>
        </form>
      </Modal>
      <ConfirmDialog
        open={Boolean(deleting)}
        title="Remove team member"
        message={`Remove ${deleting?.name || 'this member'} from the careers site?`}
        confirmLabel="Remove"
        danger
        loading={saving}
        onConfirm={() => void onDelete()}
        onCancel={() => setDeleting(null)}
      />
    </>
  )
}

function TestimonialsTab() {
  const { toast } = useToast()
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [open, setOpen] = useState(false)
  const [editing, setEditing] = useState<Testimonial | null>(null)
  const [deleting, setDeleting] = useState<Testimonial | null>(null)
  const [saving, setSaving] = useState(false)
  const testimonials = useApi(
    () => brandingApi.listTestimonials({ page, page_size: 20, search: search || undefined }),
    [page, search, open],
    { enabled: true },
  )
  const [form, setForm] = useState({ author_name: '', author_role: '', content: '', rating: 5, is_active: true })

  function openCreate() {
    setEditing(null)
    setForm({ author_name: '', author_role: '', content: '', rating: 5, is_active: true })
    setOpen(true)
  }

  function openEdit(t: Testimonial) {
    setEditing(t)
    setForm({ author_name: t.author_name, author_role: t.author_role, content: t.content, rating: t.rating, is_active: t.is_active })
    setOpen(true)
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setSaving(true)
    try {
      if (editing) {
        await brandingApi.updateTestimonial(editing.id, form)
        toast('Testimonial updated', 'success')
      } else {
        await brandingApi.createTestimonial(form)
        toast('Testimonial added', 'success')
      }
      setOpen(false)
      testimonials.reload()
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Save failed', 'error')
    } finally {
      setSaving(false)
    }
  }

  async function onDelete() {
    if (!deleting) return
    setSaving(true)
    try {
      await brandingApi.removeTestimonial(deleting.id)
      toast('Testimonial removed', 'success')
      setDeleting(null)
      testimonials.reload()
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Delete failed', 'error')
    } finally {
      setSaving(false)
    }
  }

  return (
    <>
      <Card
        padding={0}
        title="Testimonials"
        actions={
          <Button size="sm" leftIcon={<Plus size={14} />} onClick={openCreate}>
            Add testimonial
          </Button>
        }
      >
        <DataTable
          loading={testimonials.loading}
          columns={[
            {
              key: 'author',
              header: 'Author',
              render: (t: Testimonial) => (
                <div>
                  <div style={{ fontWeight: 600 }}>{t.author_name}</div>
                  <div className="hf-subtle" style={{ fontSize: '0.75rem' }}>{t.author_role || '—'}</div>
                </div>
              ),
            },
            { key: 'rating', header: 'Rating', render: (t: Testimonial) => `${t.rating} / 5` },
            {
              key: 'active',
              header: 'Active',
              render: (t: Testimonial) => <Badge tone={t.is_active ? 'success' : 'neutral'}>{t.is_active ? 'Yes' : 'No'}</Badge>,
            },
            {
              key: 'actions',
              header: '',
              render: (t: Testimonial) => (
                <div style={{ display: 'flex', gap: 6, justifyContent: 'flex-end' }}>
                  <Button size="sm" variant="ghost" onClick={() => openEdit(t)} aria-label="Edit">
                    <Pencil size={14} />
                  </Button>
                  <Button size="sm" variant="ghost" onClick={() => setDeleting(t)} aria-label="Delete">
                    <Trash2 size={14} />
                  </Button>
                </div>
              ),
            },
          ]}
          rows={testimonials.data?.results || []}
          rowKey={(t) => t.id}
          emptyTitle="No testimonials"
          emptyDescription="Add quotes from candidates and employees."
        />
      </Card>
      <Modal open={open} onClose={() => setOpen(false)} title={editing ? 'Edit testimonial' : 'Add testimonial'}>
        <form onSubmit={onSubmit} style={{ display: 'grid', gap: 12 }}>
          <Input label="Author name" required value={form.author_name} onChange={(e) => setForm((f) => ({ ...f, author_name: e.target.value }))} />
          <Input label="Author role" value={form.author_role} onChange={(e) => setForm((f) => ({ ...f, author_role: e.target.value }))} />
          <Textarea label="Content" required value={form.content} onChange={(e) => setForm((f) => ({ ...f, content: e.target.value }))} />
          <Input label="Rating (1–5)" type="number" min={1} max={5} value={form.rating} onChange={(e) => setForm((f) => ({ ...f, rating: Math.min(5, Math.max(1, Number(e.target.value) || 5)) }))} />
          <label style={{ display: 'flex', gap: 8, alignItems: 'center', fontSize: '0.88rem' }}>
            <input type="checkbox" checked={form.is_active} onChange={(e) => setForm((f) => ({ ...f, is_active: e.target.checked }))} />
            Active on careers site
          </label>
          <Button type="submit" loading={saving}>
            {editing ? 'Save changes' : 'Add testimonial'}
          </Button>
        </form>
      </Modal>
      <ConfirmDialog
        open={Boolean(deleting)}
        title="Remove testimonial"
        message={`Remove the testimonial from ${deleting?.author_name || 'this author'}?`}
        confirmLabel="Remove"
        danger
        loading={saving}
        onConfirm={() => void onDelete()}
        onCancel={() => setDeleting(null)}
      />
    </>
  )
}

function CulturePostsTab() {
  const navigate = useNavigate()
  const { toast } = useToast()
  const [page, setPage] = useState(1)
  const [status, setStatus] = useState('')
  const [deleting, setDeleting] = useState<CulturePost | null>(null)
  const [acting, setActing] = useState<string | null>(null)
  const [removing, setRemoving] = useState(false)
  const posts = useApi(
    () => brandingApi.listCulturePosts({ page, page_size: 20, status: status || undefined }),
    [page, status, deleting],
    { enabled: true },
  )

  async function runAction(postId: string, action: () => Promise<unknown>, ok: string) {
    setActing(postId)
    try {
      await action()
      toast(ok, 'success')
      posts.reload()
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Action failed', 'error')
    } finally {
      setActing(null)
    }
  }

  async function onDelete() {
    if (!deleting) return
    setRemoving(true)
    try {
      await brandingApi.removeCulturePost(deleting.id)
      toast('Post deleted', 'success')
      setDeleting(null)
      posts.reload()
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Delete failed', 'error')
    } finally {
      setRemoving(false)
    }
  }

  return (
    <>
      <Card
        padding={0}
        title="Culture posts"
        actions={
          <Button size="sm" leftIcon={<Plus size={14} />} onClick={() => navigate('/app/branding/culture/new')}>
            New post
          </Button>
        }
      >
        <div style={{ padding: '0.75rem 1.25rem', borderBottom: '1px solid var(--hf-border)' }}>
          <Select
            label="Status"
            value={status}
            onChange={(e) => {
              setPage(1)
              setStatus(e.target.value)
            }}
            options={[
              { value: '', label: 'All' },
              { value: 'draft', label: 'Draft' },
              { value: 'published', label: 'Published' },
              { value: 'archived', label: 'Archived' },
            ]}
          />
        </div>
        <DataTable
          loading={posts.loading}
          columns={[
            {
              key: 'title',
              header: 'Title',
              render: (p: CulturePost) => (
                <Link to={`/app/branding/culture/${p.id}/edit`} style={{ fontWeight: 650, textDecoration: 'none' }}>
                  {p.title}
                </Link>
              ),
            },
            {
              key: 'status',
              header: 'Status',
              render: (p: CulturePost) => (
                <Badge tone={p.status === 'published' ? 'success' : p.status === 'archived' ? 'neutral' : 'warning'}>
                  {titleCase(p.status)}
                </Badge>
              ),
            },
            { key: 'tags', header: 'Tags', render: (p: CulturePost) => (p.tags || []).join(', ') || '—' },
            { key: 'published', header: 'Published', render: (p: CulturePost) => formatDate(p.published_at) },
            {
              key: 'actions',
              header: '',
              render: (p: CulturePost) => (
                <div style={{ display: 'flex', gap: 6, justifyContent: 'flex-end' }}>
                  {p.status === 'draft' && (
                    <Button
                      size="sm"
                      variant="outline"
                      loading={acting === p.id}
                      onClick={() => void runAction(p.id, () => brandingApi.publishCulturePost(p.id), 'Post published')}
                    >
                      <Send size={13} /> Publish
                    </Button>
                  )}
                  {p.status === 'published' && (
                    <Button
                      size="sm"
                      variant="ghost"
                      loading={acting === p.id}
                      onClick={() => void runAction(p.id, () => brandingApi.archiveCulturePost(p.id), 'Post archived')}
                    >
                      <Archive size={13} /> Archive
                    </Button>
                  )}
                  <Button size="sm" variant="ghost" onClick={() => setDeleting(p)} aria-label="Delete">
                    <Trash2 size={14} />
                  </Button>
                </div>
              ),
            },
          ]}
          rows={posts.data?.results || []}
          rowKey={(p) => p.id}
          emptyTitle="No culture posts"
          emptyDescription="Share stories about life at your company."
        />
      </Card>
      <ConfirmDialog
        open={Boolean(deleting)}
        title="Delete culture post"
        message={`Delete "${deleting?.title || 'this post'}"? This cannot be undone.`}
        confirmLabel="Delete"
        danger
        loading={removing}
        onConfirm={() => void onDelete()}
        onCancel={() => setDeleting(null)}
      />
    </>
  )
}

const emptyCulturePost = {
  title: '',
  body_html: '',
  tags: '',
}

export function CulturePostFormPage() {
  const { id } = useParams()
  const isEdit = Boolean(id)
  const navigate = useNavigate()
  const { toast } = useToast()
  const [form, setForm] = useState(emptyCulturePost)
  const [loading, setLoading] = useState(isEdit)
  const [saving, setSaving] = useState(false)
  const post = useApi(() => brandingApi.getCulturePost(id!), [id], { enabled: isEdit })

  useEffect(() => {
    if (!post.data) return
    setForm({
      title: post.data.title,
      body_html: post.data.body_html || '',
      tags: (post.data.tags || []).join(', '),
    })
    setLoading(false)
  }, [post.data])

  function set<K extends keyof typeof emptyCulturePost>(key: K, value: string) {
    setForm((f) => ({ ...f, [key]: value }))
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    if (!form.title.trim()) {
      toast('Title is required', 'error')
      return
    }
    setSaving(true)
    const payload = {
      title: form.title,
      body_html: form.body_html,
      tags: form.tags
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean),
    }
    try {
      const saved = isEdit ? await brandingApi.updateCulturePost(id!, payload) : await brandingApi.createCulturePost(payload)
      toast(isEdit ? 'Post updated' : 'Post created', 'success')
      navigate('/app/branding')
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Save failed', 'error')
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div style={{ padding: 64, display: 'grid', placeItems: 'center' }}>
        <Spinner label="Loading post…" />
      </div>
    )
  }

  if (isEdit && !post.loading && post.error) {
    return (
      <EmptyState title="Post not found" description={post.error} actionLabel="Back" onAction={() => navigate('/app/branding')} />
    )
  }

  return (
    <div className="hf-page">
      <PageHeader
        title={isEdit ? 'Edit culture post' : 'New culture post'}
        subtitle="Write a life-at-company story for your careers site."
        actions={isEdit && post.data ? <Badge status={post.data.status} /> : undefined}
      />
      <form onSubmit={onSubmit}>
        <Card>
          <div style={{ display: 'grid', gap: 14 }}>
            <Input label="Title" required value={form.title} onChange={(e) => set('title', e.target.value)} />
            <Textarea label="Body (HTML)" value={form.body_html} onChange={(e) => set('body_html', e.target.value)} />
            <Input label="Tags (comma-separated)" value={form.tags} onChange={(e) => set('tags', e.target.value)} />
            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
              <Button type="button" variant="outline" onClick={() => navigate(-1)}>
                Cancel
              </Button>
              <Button type="submit" loading={saving}>
                {isEdit ? 'Save changes' : 'Create post'}
              </Button>
            </div>
          </div>
        </Card>
      </form>
    </div>
  )
}
