import { useState, type FormEvent } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { careerApi } from '../../api/portal'
import { useApi } from '../../hooks/useApi'
import { Badge, Button, Card, EmptyState, Input, Spinner, Textarea, useToast } from '../../components/ui'
import { formatCurrency, titleCase } from '../../utils/format'
import { ApiError } from '../../api/http'

export function CareerHomePage() {
  const [params] = useSearchParams()
  const org = params.get('org') || undefined
  const [search, setSearch] = useState('')
  const jobs = useApi(() => careerApi.listJobs({ search: search || undefined, org, page_size: 50 }), [search, org])

  return (
    <div className="hf-atmosphere" style={{ minHeight: '100vh' }}>
      <header
        style={{
          maxWidth: 960,
          margin: '0 auto',
          padding: '1.5rem 1.25rem',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          position: 'relative',
          zIndex: 1,
        }}
      >
        <Link to="/careers" style={{ textDecoration: 'none', color: 'inherit', fontFamily: 'var(--hf-font-display)', fontSize: '1.4rem', fontWeight: 700 }}>
          HireFlux Careers
        </Link>
        <Link to="/login" style={{ fontSize: '0.9rem' }}>
          Recruiter login
        </Link>
      </header>
      <section style={{ maxWidth: 960, margin: '0 auto', padding: '2rem 1.25rem 3rem', position: 'relative', zIndex: 1 }}>
        <h1 style={{ fontSize: 'clamp(2rem, 4vw, 3rem)', marginBottom: 10 }}>Find your next role</h1>
        <p className="hf-muted" style={{ maxWidth: 520, lineHeight: 1.5, marginBottom: 24 }}>
          Explore open positions and apply in minutes. Built for candidates who want a clear, respectful hiring experience.
        </p>
        <Input
          placeholder="Search roles…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={{ maxWidth: 420, marginBottom: 28 }}
        />
        {jobs.error ? (
          <Spinner label="Loading roles…" />
        ) : jobs.loading ? (
          <Card>
            <EmptyState title="Careers unavailable" description={jobs.error} />
          </Card>
        ) : (
          <div style={{ display: 'grid', gap: 12 }}>
            {(jobs.data?.results || []).map((job) => (
              <Link
                key={job.id}
                to={`/careers/jobs/${job.slug || job.id}`}
                style={{ textDecoration: 'none', color: 'inherit' }}
              >
                <Card>
                  <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
                    <div>
                      <h3 style={{ marginBottom: 6 }}>{job.title}</h3>
                      <p className="hf-muted" style={{ fontSize: '0.88rem' }}>
                        {job.department_name || 'Team'} · {titleCase(job.remote_policy)} · {titleCase(job.employment_type)}
                      </p>
                    </div>
                    <Badge tone="teal">{titleCase(job.experience_level)}</Badge>
                  </div>
                </Card>
              </Link>
            ))}
            {!jobs.data?.results?.length && <EmptyState title="No open roles right now" />}
          </div>
        )}
      </section>
    </div>
  )
}

export function JobPublicDetailPage() {
  const { slug = '' } = useParams()
  const [params] = useSearchParams()
  const org = params.get('org') || undefined
  const job = useApi(() => careerApi.getJob(slug, { org }), [slug, org])
  const navigate = useNavigate()

  if (job.loading) {
    return (
      <div style={{ padding: 64, display: 'grid', placeItems: 'center' }}>
        <Spinner />
      </div>
    )
  }
  if (job.error || !job.data) {
    return <EmptyState title="Role not found" description={job.error || undefined} actionLabel="Back" onAction={() => navigate('/careers')} />
  }
  const j = job.data
  return (
    <div className="hf-atmosphere" style={{ minHeight: '100vh' }}>
      <div style={{ maxWidth: 800, margin: '0 auto', padding: '2rem 1.25rem', position: 'relative', zIndex: 1 }}>
        <Link to="/careers" className="hf-muted" style={{ fontSize: '0.85rem' }}>
          ← All roles
        </Link>
        <h1 style={{ marginTop: 16, marginBottom: 8 }}>{j.title}</h1>
        <p className="hf-muted" style={{ marginBottom: 20 }}>
          {titleCase(j.employment_type)} · {titleCase(j.remote_policy)}
          {j.salary_visible ? ` · ${formatCurrency(j.salary_min, j.currency)} – ${formatCurrency(j.salary_max, j.currency)}` : ''}
        </p>
        <Card title="About the role">
          <div style={{ whiteSpace: 'pre-wrap', lineHeight: 1.6 }} className="hf-muted">
            {j.description || 'Details coming soon.'}
          </div>
        </Card>
        <div style={{ marginTop: 16 }}>
          <Button onClick={() => navigate(`/careers/jobs/${slug}/apply`)}>Apply now</Button>
        </div>
      </div>
    </div>
  )
}

export function ApplyFormPage() {
  const { slug = '' } = useParams()
  const navigate = useNavigate()
  const { toast } = useToast()
  const job = useApi(() => careerApi.getJob(slug), [slug], { enabled: false })
  const [form, setForm] = useState({
    first_name: '',
    last_name: '',
    email: '',
    phone: '',
    cover_letter: '',
  })
  const [resume, setResume] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    if (!job.data) return
    setLoading(true)
    try {
      await careerApi.apply({
        job_id: job.data.id,
        ...form,
        resume: resume || undefined,
      })
      toast('Application submitted', 'success')
      navigate('/careers')
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Application failed', 'error')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="hf-atmosphere" style={{ minHeight: '100vh' }}>
      <div style={{ maxWidth: 560, margin: '0 auto', padding: '2rem 1.25rem', position: 'relative', zIndex: 1 }}>
        <h1 style={{ marginBottom: 8 }}>Apply{job.data ? ` · ${job.data.title}` : ''}</h1>
        <Card>
          <form onSubmit={onSubmit} style={{ display: 'grid', gap: 12 }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
              <Input label="First name" required value={form.first_name} onChange={(e) => setForm({ ...form, first_name: e.target.value })} />
              <Input label="Last name" required value={form.last_name} onChange={(e) => setForm({ ...form, last_name: e.target.value })} />
            </div>
            <Input label="Email" type="email" required value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
            <Input label="Phone" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
            <Textarea label="Cover letter" value={form.cover_letter} onChange={(e) => setForm({ ...form, cover_letter: e.target.value })} />
            <label style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--hf-text-muted)' }}>
              Resume
              <input type="file" accept=".pdf,.doc,.docx" onChange={(e) => setResume(e.target.files?.[0] || null)} style={{ display: 'block', marginTop: 6 }} />
            </label>
            <Button type="submit" loading={loading} disabled={!job.data}>
              Submit application
            </Button>
          </form>
        </Card>
      </div>
    </div>
  )
}
