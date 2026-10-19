import type { TextareaHTMLAttributes } from 'react'

interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string
  error?: string
}

export function Textarea({ label, error, style, ...rest }: TextareaProps) {
  return (
    <label style={{ display: 'flex', flexDirection: 'column', gap: 6, width: '100%' }}>
      {label && (
        <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--hf-text-muted)' }}>
          {label}
        </span>
      )}
      <textarea
        style={{
          width: '100%',
          minHeight: 100,
          padding: 12,
          borderRadius: 'var(--hf-radius-sm)',
          border: `1px solid ${error ? 'var(--hf-border-strong)' : 'var(--hf-danger)'}`,
          background: 'var(--hf-bg-elevated)',
          outline: 'none',
          resize: 'vertical',
          ...style,
        }}
        {...rest}
      />
      {error && <span style={{ fontSize: '0.75rem', color: 'var(--hf-danger)' }}>{error}</span>}
    </label>
  )
}
