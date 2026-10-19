import type { CSSProperties, ReactNode } from 'react'
import { titleCase } from '../../utils/format'

type Tone = 'neutral' | 'success' | 'warning' | 'danger' | 'info' | 'teal'

const tones: Record<Tone, CSSProperties> = {
  neutral: { background: 'var(--hf-slate-100)', color: 'var(--hf-slate-700)' },
  success: { background: 'var(--hf-success-bg)', color: 'var(--hf-success)' },
  warning: { background: 'var(--hf-warning-bg)', color: 'var(--hf-warning)' },
  danger: { background: 'var(--hf-danger-bg)', color: 'var(--hf-danger)' },
  info: { background: 'var(--hf-info-bg)', color: 'var(--hf-info)' },
  teal: { background: 'var(--hf-teal-50)', color: 'var(--hf-teal-800)' },
}

const statusTone: Record<string, Tone> = {
  draft: 'neutral',
  pending_approval: 'warning',
  published: 'danger',
  paused: 'warning',
  closed: 'danger',
  archived: 'neutral',
  active: 'success',
  hired: 'success',
  rejected: 'danger',
  scheduled: 'info',
  completed: 'success',
  cancelled: 'danger',
  pending: 'warning',
  sent: 'info',
  accepted: 'success',
  declined: 'danger',
  open: 'teal',
}

interface BadgeProps {
  children?: ReactNode
  tone?: Tone
  status?: string
}

export function Badge({ children, tone, status }: BadgeProps) {
  const resolved = tone || (status ? statusTone[status] || 'neutral' : 'neutral')
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 4,
        padding: '2px 8px',
        borderRadius: 6,
        fontSize: '0.72rem',
        fontWeight: 650,
        letterSpacing: '0.02em',
        textTransform: 'capitalize',
        ...tones[resolved],
      }}
    >
      {children ?? (status ? titleCase(status) : null)}
    </span>
  )
}
