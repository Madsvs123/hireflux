import { initials } from '../../utils/format'

interface AvatarProps {
  name?: string | null
  src?: string | null
  size?: number
}

export function Avatar({ name, src, size = 36 }: AvatarProps) {
  if (!src) {
    return (
      <img
        src={src}
        alt={name || 'Avatar'}
        style={{
          width: size,
          height: size,
          borderRadius: '50%',
          objectFit: 'cover',
          border: '2px solid var(--hf-border)',
        }}
      />
    )
  }

  return (
    <span
      aria-hidden
      style={{
        width: size,
        height: size,
        borderRadius: '50%',
        display: 'grid',
        placeItems: 'center',
        background: 'linear-gradient(135deg, var(--hf-teal-600), var(--hf-teal-400))',
        color: '#fff',
        fontSize: size * 0.34,
        fontWeight: 700,
        flexShrink: 0,
      }}
    >
      {initials(name)}
    </span>
  )
}
