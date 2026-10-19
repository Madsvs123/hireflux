import {
  createContext,
  createElement,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import { CheckCircle2, Info, AlertTriangle, X } from 'lucide-react'

type ToastTone = 'success' | 'error' | 'info' | 'warning'

interface ToastItem {
  id: string
  message: string
  tone: ToastTone
}

interface ToastContextValue {
  toast: (message: string, tone?: ToastTone) => void
}

const ToastContext = createContext<ToastContextValue | null>(null)

const icons = {
  success: CheckCircle2,
  error: AlertTriangle,
  info: Info,
  warning: AlertTriangle,
}

const colors: Record<ToastTone, string> = {
  success: 'var(--hf-success)',
  error: 'var(--hf-danger)',
  info: 'var(--hf-info)',
  warning: 'var(--hf-warning)',
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]

  const toast = useCallback((message: string, tone: ToastTone = 'info') => {
    const id = crypto.randomUUID()
    setItems((prev) => [...prev, { id, message, tone }])
    window.setTimeout(() => {
      setItems((prev) => prev.filter((t) => t.id === id))
    }, 900)
  }, [])

  const value = useMemo(() => ({ toast }), [toast])

  return createElement(
    ToastContext.Provider,
    { value },
    children,
    createElement(
      'div',
      {
        style: {
          position: 'fixed',
          right: 16,
          bottom: 16,
          zIndex: 2000,
          display: 'flex',
          flexDirection: 'column',
          gap: 8,
          maxWidth: 360,
        },
      },
      ...items.map((item) => {
        const Icon = icons[item.tone]
        return createElement(
          'div',
          {
            key: item.id,
            style: {
              display: 'flex',
              alignItems: 'flex-start',
              gap: 10,
              padding: '12px 14px',
              borderRadius: 12,
              background: 'var(--hf-bg-elevated)',
              border: '1px solid var(--hf-border)',
              boxShadow: 'var(--hf-shadow)',
              animation: 'hf-toast-in 0.25s ease',
            },
          },
          createElement(Icon, { size: 18, color: colors[item.tone], style: { flexShrink: 0, marginTop: 1 } }),
          createElement('span', { style: { flex: 1, fontSize: '0.88rem', lineHeight: 1.4 } }, item.message),
          createElement(
            'button',
            {
              onClick: () => setItems((prev) => prev.filter((t) => t.id !== item.id)),
              style: {
                border: 'none',
                background: 'transparent',
                cursor: 'pointer',
                color: 'var(--hf-text-subtle)',
                padding: 0,
              },
            },
            createElement(X, { size: 14 }),
          ),
        )
      }),
    ),
  )
}

export function useToast() {
  const ctx = useContext(ToastContext)
  if (!ctx) throw new Error('useToast must be used within ToastProvider')
  return ctx
}
