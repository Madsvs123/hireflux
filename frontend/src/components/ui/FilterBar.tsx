import type { ReactNode } from 'react'
import { Search } from 'lucide-react'
import { Input } from './Input'
import { Select } from './Select'
import { Button } from './Button'

interface FilterOption {
  value: string
  label: string
}

interface FilterBarProps {
  search?: string
  onSearchChange?: (value: string) => void
  searchPlaceholder?: string
  filters?: Array<{
    key: string
    label: string
    value: string
    options: FilterOption[]
    onChange: (value: string) => void
  }>
  actions?: ReactNode
  onClear?: () => void
}

export function FilterBar({
  search,
  onSearchChange,
  searchPlaceholder = 'Search…',
  filters = [],
  actions,
  onClear,
}: FilterBarProps) {
  return (
    <div
      style={{
        display: 'flex',
        flexWrap: 'wrap',
        gap: 10,
        alignItems: 'flex-end',
      }}
    >
      {search && (
        <div style={{ flex: '1 1 220px', minWidth: 200 }}>
          <Input
            value={search || ''}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder={searchPlaceholder}
            leftAddon={<Search size={15} />}
          />
        </div>
      )}
      {filters.map((f) => (
        <div key={f.key} style={{ minWidth: 150, flex: '0 1 160px' }}>
          <Select
            label={f.label}
            value={f.value}
            onChange={(e) => f.onChange(e.target.value)}
            options={[{ value: '', label: 'All' }, ...f.options]}
          />
        </div>
      ))}
      <div style={{ display: 'flex', gap: 8, marginLeft: 'auto' }}>
        {onClear && (
          <Button variant="danger" size="sm" onClick={onClear}>
            Clear
          </Button>
        )}
        {actions}
      </div>
    </div>
  )
}
