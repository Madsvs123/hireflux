import type { InputHTMLAttributes, ReactNode } from 'react'
import { cn } from '../../utils/format'

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string
  error?: string
  hint?: string
  leftAddon?: ReactNode
}

export function Input({ label, error, hint, leftAddon, className, id, style, ...rest }: InputProps) {
  const inputId = rest.name
  return (
    <label style={{ display: 'flex', flexDirection: 'column', gap: 6, width: '100%' }}>
      {label && (
        <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--hf-text-muted)' }}>
          {label}
        </span>
      )}
      <div style={{ position: 'relative' }}>
        {leftAddon && (
          <span
            style={{
              position: 'absolute',
              left: 12,
              top: '50%',
              transform: 'translateY(-50%)',
              color: 'var(--hf-text-subtle)',
              display: 'flex',
            }}
          >
            {leftAddon}
          </span>
        )}
        <input
          id={inputId}
          className={cn('hf-input', className)}
          style={{
            width: '100%',
            height: 40,
            padding: leftAddon ? '0 38px 0 12px' : '0 12px',
            borderRadius: 'var(--hf-radius-sm)',
            border: `1px solid ${error ? 'var(--hf-danger)' : 'var(--hf-border-strong)'}`,
            background: 'var(--hf-bg-elevated)',
            outline: 'none',
            boxShadow: error ? '0 0 0 3px rgba(220,38,38,0.12)' : undefined,
            ...style,
          }}
          onFocus={(e) => {
            e.currentTarget.style.boxShadow = '0 0 0 3px var(--hf-ring)'
            e.currentTarget.style.borderColor = 'var(--hf-teal-500)'
            rest.onFocus?.(e)
          }}
          onBlur={(e) => {
            e.currentTarget.style.boxShadow = error ? '0 0 0 3px rgba(220,38,38,0.12)' : 'none'
            e.currentTarget.style.borderColor = error ? 'var(--hf-danger)' : 'var(--hf-border-strong)'
            rest.onBlur?.(e)
          }}
          {...rest}
        />
      </div>
      {error ? (
        <span style={{ fontSize: '0.75rem', color: 'var(--hf-danger)' }}>{error}</span>
      ) : hint ? (
        <span style={{ fontSize: '0.75rem', color: 'var(--hf-text-subtle)' }}>{hint}</span>
      ) : null}
    </label>
  )
}
