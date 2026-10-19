import { useState, type FormEvent } from 'react'
import { Link, useSearchParams, useNavigate } from 'react-router-dom'
import { authApi } from '../../api/auth'
import { ApiError } from '../../api/http'
import { Button, Input } from '../../components/ui'

export function ResetPasswordPage() {
  const [params] = useSearchParams()
  const token = params.get('t') || ''
  const navigate = useNavigate()
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    if (password !== confirm) {
      setError('Passwords do not match')
      return
    }
    setLoading(true)
    setError('')
    try {
      await authApi.resetPassword(token, password)
      navigate('/login')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Reset failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={onSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      <div>
        <h2 style={{ marginBottom: 4 }}>Choose a new password</h2>
        <p className="hf-muted" style={{ fontSize: '0.88rem' }}>
          Enter a strong password for your account
        </p>
      </div>
      <Input
        label="New password"
        type="password"
        required
        minLength={8}
        value={password}
        onChange={(e) => setPassword(e.target.value)}
      />
      <Input
        label="Confirm password"
        type="password"
        required
        value={confirm}
        onChange={(e) => setConfirm(e.target.value)}
      />
      {error && <p style={{ color: 'var(--hf-danger)', fontSize: '0.85rem' }}>{error}</p>}
      <Button type="submit" loading={loading} fullWidth disabled={!token}>
        Update password
      </Button>
      <Link to="/login" style={{ textAlign: 'center', fontSize: '0.85rem' }}>
        Back to sign in
      </Link>
    </form>
  )
}
