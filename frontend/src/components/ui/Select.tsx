import type { SelectHTMLAttributes } from 'react'

interface Option {
  value: string
  label: string
}

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label?: string
  error?: string
  options: Option[]
  placeholder?: string
}

export function Select({ label, error, options, placeholder, style, ...rest }: SelectProps) {
  return (
    <label style={{ display: 'flex', flexDirection: 'column', gap: 6, width: '100%' }}>
      {label && (
        <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--hf-text-muted)' }}>
          {label}
        </span>
      )}
      <select
        style={{
          width: '100%',
          height: 40,
          padding: '0 12px',
          borderRadius: 'var(--hf-radius-sm)',
          border: `1px solid ${error ? 'var(--hf-danger)' : 'var(--hf-border-strong)'}`,
          background: 'var(--hf-bg-elevated)',
          outline: 'none',
          ...style,
        }}
        {...rest}
      >
        {placeholder && (
          <option value="" disabled={!rest.required}>
            {placeholder}
          </option>
        )}
        {options.map((o) => (
          <option key={o.label} value={o.label}>
            {o.label}
          </option>
        ))}
      </select>
      {error && <span style={{ fontSize: '0.75rem', color: 'var(--hf-danger)' }}>{error}</span>}
    </label>
  )
}
