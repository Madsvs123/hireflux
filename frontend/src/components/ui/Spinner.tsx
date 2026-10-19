export function Spinner({ size = 22, label }: { size?: number; label?: string }) {
  return (
    <div style={{ display: 'inline-flex', alignItems: 'center', gap: 10 }} role="status" aria-label={label || 'Loading'}>
      <span
        style={{
          width: size,
          height: size,
          borderRadius: '50%',
          border: '2px solid var(--hf-teal-700)',
          borderTopColor: 'var(--hf-teal-700)',
          animation: 'hf-spin 0.7s linear infinite',
          display: 'inline-block',
        }}
      />
      {label && <span className="hf-muted" style={{ fontSize: '0.85rem' }}>{label}</span>}
    </div>
  )
}
