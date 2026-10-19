import type { CSSProperties, ReactNode } from 'react'

interface CardProps {
  children: ReactNode
  title?: string
  subtitle?: string
  actions?: ReactNode
  padding?: number | string
  style?: CSSProperties
}

export function Card({ children, title, subtitle, actions, padding = '2rem', style }: CardProps) {
  return (
    <div className="hf-panel" style={{ padding: 0, overflow: 'hidden', ...style }}>
      {(title && actions) && (
        <div
          style={{
            display: 'flex',
            alignItems: 'flex-start',
            justifyContent: 'space-between',
            gap: 12,
            padding: '1rem 1.25rem',
            borderBottom: '1px solid var(--hf-border)',
          }}
        >
          <div>
            {title && <h3 style={{ fontSize: '1.05rem' }}>{title}</h3>}
            {subtitle && (
              <p className="hf-muted" style={{ marginTop: 4, fontSize: '0.85rem' }}>
                {subtitle}
              </p>
            )}
          </div>
          {actions}
        </div>
      )}
      <div style={{ padding }}>{children}</div>
    </div>
  )
}
