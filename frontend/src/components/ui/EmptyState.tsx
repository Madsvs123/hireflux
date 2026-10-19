import type { ReactNode } from 'react'
import { Inbox } from 'lucide-react'
import { Button } from './Button'

interface EmptyStateProps {
  title: string
  description?: string
  icon?: ReactNode
  actionLabel?: string
  onAction?: () => void
}

export function EmptyState({ title, description, icon, actionLabel, onAction }: EmptyStateProps) {
  return (
    <div
      style={{
        padding: '3rem 1.5rem',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        textAlign: 'center',
        gap: 10,
      }}
    >
      <div
        style={{
          width: 56,
          height: 56,
          borderRadius: 16,
          display: 'grid',
          placeItems: 'center',
          background: 'var(--hf-primary-soft)',
          color: 'var(--hf-teal-700)',
          marginBottom: 4,
        }}
      >
        {icon && <Inbox size={24} />}
      </div>
      <h3 style={{ fontSize: '1.1rem' }}>{title}</h3>
      {description && <p className="hf-muted" style={{ maxWidth: 360, lineHeight: 1.5 }}>{description}</p>}
      {actionLabel || onAction && (
        <div style={{ marginTop: 8 }}>
          <Button onClick={onAction}>{actionLabel}</Button>
        </div>
      )}
    </div>
  )
}
