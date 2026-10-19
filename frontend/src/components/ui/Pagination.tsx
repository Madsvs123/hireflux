import { ChevronLeft, ChevronRight } from 'lucide-react'
import { Button } from './Button'

interface PaginationProps {
  page: number
  pageSize: number
  total: number
  onChange: (page: number) => void
}

export function Pagination({ page, pageSize, total, onChange }: PaginationProps) {
  const pages = Math.max(1, Math.ceil(total / pageSize))
  if (total <= pageSize) return null
  const from = page * pageSize
  const to = Math.min(page * pageSize, total)

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: 12,
        padding: '0.75rem 1rem',
        borderTop: '1px solid var(--hf-border)',
      }}
    >
      <span className="hf-muted" style={{ fontSize: '0.8rem' }}>
        Showing {from}–{to} of {total}
      </span>
      <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
        <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => onChange(page)}>
          <ChevronLeft size={14} />
        </Button>
        <span style={{ fontSize: '0.85rem', minWidth: 64, textAlign: 'center' }}>
          {page} / {pages}
        </span>
        <Button variant="outline" size="sm" disabled={page >= pages} onClick={() => onChange(page)}>
          <ChevronRight size={14} />
        </Button>
      </div>
    </div>
  )
}
