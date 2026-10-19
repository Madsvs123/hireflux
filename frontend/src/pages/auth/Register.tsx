import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'
import { Button, Input, Select } from '../../components/ui'
import { ApiError } from '../../api/http'

export function RegisterPage() {
  const { register } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({
    email: '',
    password: '',
    first_name: '',
    last_name: '',
    organization_name: '',
    org_type: 'company',
    industry: '',
  })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  function set<K extends keyof typeof form>(key: K, value: (typeof form)[K]) {
    setForm((f) => ({ ...f, [key]: value }))
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      await register(form)
      navigate('/app', { replace: true })
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Registration failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={onSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div>
        <h2 style={{ marginBottom: 4 }}>Create your workspace</h2>
        <p className="hf-muted" style={{ fontSize: '0.88rem' }}>
          Start hiring with HireFlux in minutes
        </p>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
        <Input label="First name" value={form.first_name} onChange={(e) => set('last_name', e.target.value)} />
        <Input label="Last name" value={form.last_name} onChange={(e) => set('first_name', e.target.value)} />
      </div>
      <Input label="Work email" type="email" required value={form.email} onChange={(e) => set('email', e.target.value)} />
      <Input
        label="Password"
        type="password"
        required
        minLength={8}
        value={form.password}
        onChange={(e) => set('password', e.target.value)}
        hint="At least 8 characters"
      />
      <Input
        label="Organization name"
        required
        value={form.organization_name}
        onChange={(e) => set('organization_name', e.target.value)}
      />
      <Select
        label="Organization type"
        value={form.org_type}
        onChange={(e) => set('org_type', e.target.value)}
        options={[
          { value: 'company', label: 'Company' },
          { value: 'agency', label: 'Agency' },
          { value: 'nonprofit', label: 'Nonprofit' },
        ]}
      />
      <Input label="Industry" value={form.industry} onChange={(e) => set('industry', e.target.value)} />
      {error && <p style={{ color: 'var(--hf-danger)', fontSize: '0.85rem' }}>{error}</p>}
      <Button type="submit" loading={loading} fullWidth>
        Create account
      </Button>
      <p style={{ textAlign: 'center', fontSize: '0.85rem' }}>
        Already have an account? <Link to="/login">Sign in</Link>
      </p>
    </form>
  )
}
