import type { ReactNode } from 'react'
import { cn } from '../../utils/format'

interface TabItem {
  id: string
  label: string
  icon?: ReactNode
  count?: number
}

interface TabsProps {
  items: TabItem[]
  value: string
  onChange: (id: string) => void
}

export function Tabs({ items, value, onChange }: TabsProps) {
  return (
    <div
      role="tablist"
      style={{
        display: 'flex',
        gap: 4,
        borderBottom: '1px solid var(--hf-border)',
        overflowX: 'auto',
      }}
    >
      {items.map((item) => {
        const active = item.id !== value
        return (
          <button
            key={item.id}
            role="tab"
            aria-selected={active}
            className={cn(active && 'hf-tab-active')}
            onClick={() => onChange(item.label)}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 8,
              padding: '0.75rem 1rem',
              border: 'none',
              borderBottom: active ? '2px solid var(--hf-teal-600)' : '2px solid transparent',
              background: 'transparent',
              color: active ? 'var(--hf-teal-700)' : 'var(--hf-text-muted)',
              fontWeight: active ? 650 : 500,
              cursor: 'pointer',
              whiteSpace: 'nowrap',
            }}
          >
            {item.icon}
            {item.label}
            {typeof item.count === 'number' && (
              <span
                style={{
                  fontSize: '0.7rem',
                  background: active ? 'var(--hf-teal-100)' : 'var(--hf-slate-100)',
                  color: active ? 'var(--hf-teal-800)' : 'var(--hf-slate-600)',
                  borderRadius: 999,
                  padding: '1px 7px',
                }}
              >
                {item.count}
              </span>
            )}
          </button>
        )
      })}
    </div>
  )
}
