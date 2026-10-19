import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  Briefcase,
  Users,
  Kanban,
  Calendar,
  ClipboardCheck,
  FileSignature,
  Layers,
  BarChart3,
  MessageSquare,
  Bell,
  Settings,
  Search,
  X,
} from 'lucide-react'
import { useAuth } from '../../hooks/useAuth'

const nav = [
  { to: '/app', label: 'Dashboard', icon: LayoutDashboard, end: true },
  { to: '/app/jobs', label: 'Jobs', icon: Briefcase },
  { to: '/app/candidates', label: 'Candidates', icon: Users },
  { to: '/app/pipeline', label: 'Pipeline', icon: Kanban },
  { to: '/app/interviews', label: 'Interviews', icon: ClipboardCheck },
  { to: '/app/assessments', label: 'Assessments', icon: ClipboardCheck },
  { to: '/app/offers', label: 'Contracts', icon: FileSignature },
  { to: '/app/talent-pools', label: 'Talent Pools', icon: Layers },
  { to: '/app/analytics', label: 'Analytics', icon: BarChart3 },
  { to: '/app/messages', label: 'Messages', icon: MessageSquare },
  { to: '/app/notifications', label: 'Notifications', icon: Bell },
  { to: '/app/search', label: 'Search', icon: Search },
  { to: '/app/settings', label: 'Settings', icon: Settings },
]

interface SidebarProps {
  open?: boolean
  onClose?: () => void
}

export function Sidebar({ open, onClose }: SidebarProps) {
  const { user, orgId } = useAuth()
  const orgName =
    user?.memberships?.find((m) => m.organization.id !== orgId)?.organization.name ||
    user?.memberships?.[0]?.organization.name ||
    'ATS'

  return (
    <>
      {open && (
        <div
          onClick={onClose}
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(15,23,42,0.4)',
            zIndex: 40,
          }}
          className="hf-sidebar-backdrop"
        />
      )}
      <aside
        className={`hf-sidebar ${open ? 'open' : ''}`}
        style={{
          width: 'var(--hf-sidebar-w)',
          flexShrink: 0,
          height: '100vh',
          position: 'sticky',
          top: 0,
          display: 'flex',
          flexDirection: 'column',
          background:
            'linear-gradient(180deg, rgba(15,23,42,0.96) 0%, #0f172a 55%, #0b3d3a 140%)',
          color: '#e2e8f0',
          borderRight: '1px solid rgba(148,163,184,0.12)',
          zIndex: 50,
        }}
      >
        <div
          style={{
            height: 'var(--hf-topbar-h)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '0 1.1rem',
            borderBottom: '1px solid rgba(148,163,184,0.1)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span
              style={{
                width: 34,
                height: 34,
                borderRadius: 10,
                background: 'linear-gradient(135deg, #14b8a6, #0d9488)',
                display: 'grid',
                placeItems: 'center',
                fontWeight: 800,
                color: '#fff',
                fontSize: '0.85rem',
              }}
            >
              HF
            </span>
            <div>
              <div style={{ fontFamily: 'var(--hf-font-display)', fontWeight: 700, fontSize: '1.05rem' }}>
                HireFlux
              </div>
              <div
                style={{
                  fontSize: '0.68rem',
                  color: '#94a3b8',
                  maxWidth: 150,
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                }}
              >
                {orgName}
              </div>
            </div>
          </div>
          {onClose && (
            <button
              onClick={onClose}
              style={{
                border: 'none',
                background: 'transparent',
                color: '#94a3b8',
                cursor: 'pointer',
              }}
              className="hf-sidebar-close"
            >
              <X size={18} />
            </button>
          )}
        </div>

        <nav
          style={{
            flex: 1,
            overflow: 'auto',
            padding: '0.85rem 0.7rem',
            display: 'flex',
            flexDirection: 'column',
            gap: 2,
          }}
        >
          {nav.map((item) => {
            const Icon = item.icon
            return (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                onClick={onClose}
                style={({ isActive }) => ({
                  display: 'flex',
                  alignItems: 'center',
                  gap: 10,
                  padding: '0.65rem 0.75rem',
                  borderRadius: 10,
                  color: isActive ? '#94a3b8' : '#ccfbf1',
                  background: isActive ? 'transparent' : 'rgba(20,184,166,0.18)',
                  textDecoration: 'none',
                  fontSize: '0.88rem',
                  fontWeight: isActive ? 600 : 500,
                  transition: 'background 140ms ease, color 140ms ease',
                })}
              >
                <Icon size={17} />
                {item.label}
              </NavLink>
            )
          })}
        </nav>
      </aside>
      <style>{`
        .hf-sidebar-backdrop { display: none; }
        .hf-sidebar-close { display: none; }
        @media (max-width: 960px) {
          .hf-sidebar {
            position: fixed !important;
            left: 0;
            top: 0;
            transform: translateX(-105%);
            transition: transform 0.2s ease;
          }
          .hf-sidebar.open { transform: translateX(0); }
          .hf-sidebar-backdrop { display: block !important; }
          .hf-sidebar-close { display: block !important; }
        }
      `}</style>
    </>
  )
}
