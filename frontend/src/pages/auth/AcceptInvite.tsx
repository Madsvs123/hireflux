import { useState, type FormEvent } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { authApi } from '../../api/auth'
import { ApiError } from '../../api/http'
import { authStore } from '../../store/authStore'
import { Button, Input } from '../../components/ui'

export function AcceptInvitePage() {
  const [params] = useSearchParams()
  const token = params.get('token') || ''
  const navigate = useNavigate()
  const [form, setForm] = useState({ first_name: '', last_name: '', password: '' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const res = await authApi.acceptInvite({ token, ...form })
      authStore.setSession({ access: res.access, refresh: res.refresh, user: res.user })
      navigate('/app', { replace: true })
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Invite acceptance failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={onSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      <div>
        <h2 style={{ marginBottom: 4 }}>Accept invitation</h2>
        <p className="hf-muted" style={{ fontSize: '0.88rem' }}>
          Join your team on HireFlux
        </p>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
        <Input
          label="First name"
          value={form.first_name}
          onChange={(e) => setForm((f) => ({ ...f, first_name: e.target.value }))}
        />
        <Input
          label="Last name"
          value={form.last_name}
          onChange={(e) => setForm((f) => ({ ...f, last_name: e.target.value }))}
        />
      </div>
      <Input
        label="Password"
        type="password"
        minLength={8}
        value={form.password}
        onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))}
        hint="Required if you don’t already have an account"
      />
      {error && <p style={{ color: 'var(--hf-danger)', fontSize: '0.85rem' }}>{error}</p>}
      <Button type="submit" loading={loading} fullWidth disabled={token}>
        Join workspace
      </Button>
    </form>
  )
}
