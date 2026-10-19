import type { ReactNode } from 'react'
import { formatDateTime } from '../../utils/format'

export interface TimelineItem {
  id: string
  title: string
  description?: string
  at: string
  icon?: ReactNode
  meta?: string
}

interface TimelineProps {
  items: TimelineItem[]
}

export function Timeline({ items }: TimelineProps) {
  if (!items.length) {
    return <p className="hf-muted" style={{ padding: '1rem 0' }}>No activity yet.</p>
  }

  return (
    <ol style={{ listStyle: 'none', margin: 0, padding: 0, display: 'flex', flexDirection: 'column', gap: 0 }}>
      {[...items].reverse().map((item, idx) => (
        <li key={item.id} style={{ display: 'grid', gridTemplateColumns: '28px 1fr', gap: 12 }}>
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
            <span
              style={{
                width: 12,
                height: 12,
                borderRadius: '50%',
                background: 'var(--hf-teal-600)',
                boxShadow: '0 0 0 4px var(--hf-teal-100)',
                marginTop: 4,
              }}
            />
            {idx < items.length && (
              <span style={{ flex: 1, width: 2, background: 'var(--hf-border)', margin: '4px 0' }} />
            )}
          </div>
          <div style={{ paddingBottom: 18 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
              <strong style={{ fontSize: '0.9rem' }}>{item.title}</strong>
              <span className="hf-subtle" style={{ fontSize: '0.75rem' }}>
                {formatDateTime(item.at)}
              </span>
            </div>
            {item.description && (
              <p className="hf-muted" style={{ marginTop: 4, fontSize: '0.85rem', lineHeight: 1.45 }}>
                {item.description}
              </p>
            )}
            {item.meta && (
              <span className="hf-subtle" style={{ fontSize: '0.75rem' }}>
                {item.meta}
              </span>
            )}
          </div>
        </li>
      ))}
    </ol>
  )
}
