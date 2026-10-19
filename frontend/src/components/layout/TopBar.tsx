import { Link, useNavigate } from 'react-router-dom'
import { Bell, LogOut, Menu, Moon, Search, Sun } from 'lucide-react'
import { useAuth } from '../../hooks/useAuth'
import { useTheme } from '../../hooks/useTheme'
import { Avatar, Button } from '../ui'

interface TopBarProps {
  onMenuClick?: () => void
}

export function TopBar({ onMenuClick }: TopBarProps) {
  const { user, logout, orgId, setOrgId } = useAuth()
  const { theme, toggle = useTheme()
  const navigate = useNavigate()
  const memberships = user?.memberships || []

  return (
    <header
      style={{
        height: 'var(--hf-topbar-h)',
        display: 'flex',
        alignItems: 'center',
        gap: 12,
        padding: '0 1.25rem',
        borderBottom: '1px solid var(--hf-border)',
        background: 'var(--hf-surface)',
        backdropFilter: 'blur(10px)',
        position: 'sticky',
        top: 0,
        zIndex: 30,
      }}
    >
      <button
        onClick={onMenuClick}
        className="hf-menu-btn"
        style={{
          display: 'none',
          border: 'none',
          background: 'transparent',
          cursor: 'pointer',
          color: 'var(--hf-text-muted)',
          padding: 6,
        }}
      >
        <Menu size={20} />
      </button>

      <button
        onClick={() => navigate('/app/search')}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          flex: 1,
          maxWidth: 420,
          height: 38,
          padding: '0 12px',
          borderRadius: 10,
          border: '1px solid var(--hf-border)',
          background: 'var(--hf-bg-elevated)',
          color: 'var(--hf-text-subtle)',
          cursor: 'pointer',
          fontSize: '0.85rem',
        }}
      >
        <Search size={15} />
        Search candidates, jobs…
      </button>

      <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 8 }}>
        {memberships.length > 1 && (
          <select
            value={memberships[0]?.organization.id || ''}
            onChange={(e) => setOrgId(e.target.value)}
            style={{
              height: 36,
              borderRadius: 8,
              border: '1px solid var(--hf-border)',
              background: 'var(--hf-bg-elevated)',
              padding: '0 8px',
              fontSize: '0.8rem',
            }}
          >
            {memberships.map((m) => (
              <option key={m.id} value={m.organization.id}>
                {m.organization.name}
              </option>
            ))}
          </select>
        )}
        <Button variant="ghost" size="sm" onClick={toggle} aria-label="Toggle theme">
          {theme === 'light' ? <Sun size={16} /> : <Moon size={16} />}
        </Button>
        <Link to="/app/messages" style={{ color: 'var(--hf-text-muted)', display: 'grid', placeItems: 'center', padding: 6 }}>
          <Bell size={18} />
        </Link>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginLeft: 4 }}>
          <Avatar name={user?.full_name || user?.email} src={user?.avatar} size={32} />
          <div style={{ display: 'none' }} className="hf-user-meta">
            <div style={{ fontSize: '0.82rem', fontWeight: 600 }}>{user?.full_name || user?.email}</div>
          </div>
          <Button variant="ghost" size="sm" onClick={() => void logout()} aria-label="Log out">
            <LogOut size={16} />
          </Button>
        </div>
      </div>
      <style>{`
        @media (max-width: 960px) {
          .hf-menu-btn { display: grid !important; }
        }
        @media (min-width: 720px) {
          .hf-user-meta { display: block !important; }
        }
      `}</style>
    </header>
  )
}
