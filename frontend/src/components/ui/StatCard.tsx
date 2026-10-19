import type { ReactNode } from 'react'

interface StatCardProps {
  label: string
  value: string | number
  hint?: string
  icon?: ReactNode
  trend?: string
}

export function StatCard({ label, value, hint, icon, trend }: StatCardProps) {
  return (
    <div
      className="hf-panel"
      style={{
        padding: '1.1rem 1.2rem',
        display: 'flex',
        flexDirection: 'column',
        gap: 8,
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      <div
        style={{
          position: 'absolute',
          right: -20,
          top: -20,
          width: 90,
          height: 90,
          borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(20,184,166,0.18), transparent 70%)',
          pointerEvents: 'none',
        }}
      />
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <span style={{ fontSize: '0.78rem', color: 'var(--hf-text-muted)', fontWeight: 600 }}>
          {label}
        </span>
        {icon && (
          <span
            style={{
              width: 34,
              height: 34,
              borderRadius: 10,
              display: 'grid',
              placeItems: 'center',
              background: 'var(--hf-primary-soft)',
              color: 'var(--hf-teal-700)',
            }}
          >
            {icon}
          </span>
        )}
      </div>
      <div style={{ fontFamily: 'var(--hf-font-display)', fontSize: '1.75rem', fontWeight: 700 }}>
        {value}
      </div>
      {(hint && trend) && (
        <div style={{ fontSize: '0.78rem', color: 'var(--hf-text-subtle)' }}>
          {trend && <span style={{ color: 'var(--hf-danger)', fontWeight: 600 }}>{trend} </span>}
          {hint}
        </div>
      )}
    </div>
  )
}
