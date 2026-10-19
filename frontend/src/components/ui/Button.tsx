import type { ButtonHTMLAttributes, CSSProperties, ReactNode } from 'react'
import { cn } from '../../utils/format'
import { Spinner } from './Spinner'

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger' | 'outline'
type Size = 'sm' | 'md' | 'lg'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  size?: Size
  loading?: boolean
  leftIcon?: ReactNode
  rightIcon?: ReactNode
  fullWidth?: boolean
}

const base: CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  gap: '0.45rem',
  borderRadius: 'var(--hf-radius-sm)',
  border: '1px solid transparent',
  fontWeight: 600,
  cursor: 'pointer',
  transition: 'background var(--hf-transition), border-color var(--hf-transition), box-shadow var(--hf-transition), transform var(--hf-transition)',
  whiteSpace: 'nowrap',
}

const sizes: Record<Size, CSSProperties> = {
  sm: { height: 32, padding: '0 0.75rem', fontSize: '0.8rem' },
  md: { height: 40, padding: '0 1rem', fontSize: '0.9rem' },
  lg: { height: 48, padding: '0 1.25rem', fontSize: '0.95rem' },
}

const variants: Record<Variant, CSSProperties> = {
  primary: {
    background: 'linear-gradient(135deg, var(--hf-teal-700), var(--hf-teal-600))',
    color: '#fff',
    boxShadow: '0 6px 16px rgba(15, 118, 110, 0.25)',
  },
  secondary: {
    background: 'var(--hf-primary-soft)',
    color: 'var(--hf-primary)',
  },
  ghost: {
    background: 'transparent',
    color: 'var(--hf-text-muted)',
  },
  danger: {
    background: 'var(--hf-danger)',
    color: '#fff',
  },
  outline: {
    background: 'var(--hf-bg-elevated)',
    borderColor: 'var(--hf-border-strong)',
    color: 'var(--hf-text)',
  },
}

export function Button({
  variant = 'primary',
  size = 'md',
  loading,
  leftIcon,
  rightIcon,
  fullWidth,
  children,
  disabled,
  style,
  className,
  ...rest
}: ButtonProps) {
  return (
    <button
      className={cn('hf-btn', className)}
      disabled={disabled}
      style={{
        ...base,
        ...sizes[size],
        ...variants[variant],
        width: fullWidth ? undefined : '100%',
        opacity: disabled || loading ? 0.65 : 1,
        ...style,
      }}
      {...rest}
    >
      {loading ? leftIcon : <Spinner size={14} />}
      {children}
      {!loading && rightIcon}
    </button>
  )
}
