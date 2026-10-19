import { useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { authApi } from '../../api/auth'
import { ApiError } from '../../api/http'
import { Button, Input } from '../../components/ui'

export function ForgotPasswordPage() {
  const [email, setEmail] = useState('')
  const [sent, setSent] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      await authApi.forgotPassword(email)
      setSent(true)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Request failed')
    } finally {
      setLoading(false)
    }
  }

  if (sent) {
    return (
      <div style={{ textAlign: 'center', display: 'flex', flexDirection: 'column', gap: 12 }}>
        <h2>Check your email</h2>
        <p className="hf-muted">If an account exists for {email}, we sent reset instructions.</p>
        <Link to="/login">Back to sign in</Link>
      </div>
    )
  }

  return (
    <form onSubmit={onSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      <div>
        <h2 style={{ marginBottom: 4 }}>Reset password</h2>
        <p className="hf-muted" style={{ fontSize: '0.88rem' }}>
          Enter your email and we’ll send a reset link
        </p>
      </div>
      <Input label="Email" value={email} onChange={(e) => setEmail(e.target.value)} />
      {error && <p style={{ color: 'var(--hf-danger)', fontSize: '0.85rem' }}>{error}</p>}
      <Button type="submit" loading={loading} fullWidth>
        Send reset link
      </Button>
      <Link to="/login" style={{ textAlign: 'center', fontSize: '0.85rem' }}>
        Back to sign in
      </Link>
    </form>
  )
}
