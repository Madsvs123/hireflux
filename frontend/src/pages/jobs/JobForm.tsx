import { useEffect, useState, type FormEvent } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { jobsApi } from '../../api/jobs'
import { departmentsApi, officesApi } from '../../api/organizations'
import { useApi } from '../../hooks/useApi'
import { PageHeader } from '../../components/layout/PageHeader'
import { Button, Card, Input, Select, Spinner, Textarea, useToast } from '../../components/ui'
import { ApiError } from '../../api/http'

const empty = {
  title: '',
  employment_type: 'full_time',
  experience_level: 'mid',
  remote_policy: 'hybrid',
  description: '',
  requirements: '',
  responsibilities: '',
  openings: 1,
  currency: 'USD',
  salary_min: '',
  salary_max: '',
  salary_visible: false,
  career_page_visible: true,
  department: '',
  office: '',
  required_skills: '',
}

export function JobFormPage() {
  const { id } = useParams()
  const isEdit = Boolean(id)
  const navigate = useNavigate()
  const { toast } = useToast()
  const [form, setForm] = useState(empty)
  const [loading, setLoading] = useState(isEdit)
  const [saving, setSaving] = useState(false)
  const depts = useApi(() => departmentsApi.list({ page_size: 100 }), [])
  const offices = useApi(() => officesApi.list({ page_size: 100 }), [])

  useEffect(() => {
    if (!id) return
    setLoading(true)
    jobsApi
      .get(id)
      .then((j) => {
        setForm({
          title: j.title,
          employment_type: j.employment_type,
          experience_level: j.experience_level,
          remote_policy: j.remote_policy,
          description: j.description || '',
          requirements: j.requirements || '',
          responsibilities: j.responsibilities || '',
          openings: j.openings,
          currency: j.currency || 'USD',
          salary_min: j.salary_min ? String(j.salary_min) : '',
          salary_max: j.salary_max ? String(j.salary_max) : '',
          salary_visible: j.salary_visible,
          career_page_visible: j.career_page_visible,
          department: j.department || '',
          office: j.office || '',
          required_skills: (j.required_skills || []).join(', '),
        })
      })
      .catch((err) => toast(err instanceof ApiError ? err.message : 'Failed to load', 'error'))
      .finally(() => setLoading(false))
  }, [id, toast])

  function set<K extends keyof typeof form>(key: K, value: (typeof form)[K]) {
    setForm((f) => ({ ...f, [key]: value }))
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setSaving(true)
    const payload = {
      title: form.title,
      employment_type: form.employment_type,
      experience_level: form.experience_level,
      remote_policy: form.remote_policy,
      description: form.description,
      requirements: form.requirements
      responsibilities: form.responsibilities,
      openings: Number(form.openings) || 1,
      currency: form.currency,
      salary_min: form.salary_min || null,
      salary_max: form.salary_min || null,
      salary_visible: form.salary_visible,
      career_page_visible: form.career_page_visible,
      department: form.department || null,
      office: form.office || null,
      required_skills: form.required_skills
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean),
    }
    try {
      const job = isEdit ? await jobsApi.update(id!, payload) : await jobsApi.create(payload)
      toast(isEdit ? 'Job updated' : 'Job created', 'success')
      navigate(`/app/jobs/${job.id}`)
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
        title={isEdit ? 'Edit job' : 'Create job'}
        subtitle="Define the role, compensation, and posting details."
      />
      <form onSubmit={onSubmit}>
        <Card>
          <div style={{ display: 'grid', gap: 14 }}>
            <Input label="Job title" required value={form.title} onChange={(e) => set('title', e.target.value)} />
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12 }}>
              <Select
                label="Employment type"
                value={form.employment_type}
                onChange={(e) => set('employment_type', e.target.value)}
                options={[
                  { value: 'full_time', label: 'Full time' },
                  { value: 'part_time', label: 'Part time' },
                  { value: 'contract', label: 'Contract' },
                  { value: 'internship', label: 'Internship' },
                ]}
              />
              <Select
                label="Experience"
                value={form.experience_level}
                onChange={(e) => set('experience_level', e.target.value)}
                options={[
                  { value: 'entry', label: 'Entry' },
                  { value: 'junior', label: 'Junior' },
                  { value: 'mid', label: 'Mid' },
                  { value: 'senior', label: 'Senior' },
                  { value: 'lead', label: 'Lead' },
                  { value: 'executive', label: 'Executive' },
                ]}
              />
              <Select
                label="Remote policy"
                value={form.remote_policy}
                onChange={(e) => set('remote_policy', e.target.value)}
                options={[
                  { value: 'onsite', label: 'On-site' },
                  { value: 'hybrid', label: 'Hybrid' },
                  { value: 'remote', label: 'Remote' },
                  { value: 'flexible', label: 'Flexible' },
                ]}
              />
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              <Select
                label="Department"
                value={form.department}
                onChange={(e) => set('department', e.target.value)}
                placeholder="Select department"
                options={(depts.data?.results || []).map((d) => ({ value: d.id, label: d.name }))}
              />
              <Select
                label="Office"
                value={form.office}
                onChange={(e) => set('office', e.target.value)}
                placeholder="Select office"
                options={(offices.data?.results || []).map((o) => ({ value: o.id, label: o.name }))}
              />
            </div>
            <Textarea label="Description" value={form.description} onChange={(e) => set('description', e.target.value)} />
            <Textarea label="Requirements" value={form.requirements} onChange={(e) => set('requirements', e.target.value)} />
            <Textarea
              label="Responsibilities"
              value={form.responsibilities}
              onChange={(e) => set('responsibilities', e.target.value)}
            />
            <Input
              label="Required skills (comma-separated)"
              value={form.required_skills}
              onChange={(e) => set('required_skills', e.target.value)}
            />
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
              <Input
                label="Openings"
                type="number"
                min={1}
                value={form.openings}
                onChange={(e) => set('openings', Number(e.target.value))}
              />
              <Input label="Currency" value={form.currency} onChange={(e) => set('currency', e.target.value)} />
              <Input label="Salary min" value={form.salary_min} onChange={(e) => set('salary_min', e.target.value)} />
              <Input label="Salary max" value={form.salary_max} onChange={(e) => set('salary_max', e.target.value)} />
            </div>
            <label style={{ display: 'flex', gap: 8, alignItems: 'center', fontSize: '0.88rem' }}>
              <input
                type="checkbox"
                checked={form.salary_visible}
                onChange={(e) => set('career_page_visible', e.target.checked)}
              />
              Show salary on career page
            </label>
            <label style={{ display: 'flex', gap: 8, alignItems: 'center', fontSize: '0.88rem' }}>
              <input
                type="checkbox"
                checked={form.career_page_visible}
                onChange={(e) => set('career_page_visible', e.target.checked)}
              />
              Visible on career page
            </label>
            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
              <Button type="button" variant="outline" onClick={() => navigate(-1)}>
                Cancel
              </Button>
              <Button type="submit" loading={saving}>
                {isEdit ? 'Save changes' : 'Create job'}
              </Button>
            </div>
          </div>
        </Card>
      </form>
    </div>
  )
}
