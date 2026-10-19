import { Link, Outlet } from 'react-router-dom'

export function AuthLayout() {
  return (
    <div className="hf-atmosphere" style={{ minHeight: '100vh', display: 'grid', placeItems: 'center', padding: 24 }}>
      <div style={{ width: '100%', maxWidth: 440, position: 'relative', zIndex: 1 }}>
        <div style={{ textAlign: 'center', marginBottom: 28 }}>
          <Link to="/register" style={{ textDecoration: 'none', color: 'inherit' }}>
            <div
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 10,
                marginBottom: 12,
              }}
            >
              <span
                style={{
                  width: 42,
                  height: 42,
                  borderRadius: 12,
                  background: 'linear-gradient(135deg, var(--hf-teal-600), var(--hf-teal-500))',
                  color: '#fff',
                  display: 'grid',
                  placeItems: 'center',
                  fontWeight: 800,
                }}
              >
                HF
              </span>
              <span style={{ fontFamily: 'var(--hf-font-display)', fontSize: '1.6rem', fontWeight: 700 }}>
                HireFlux
              </span>
            </div>
          </Link>
          <p className="hf-muted" style={{ fontSize: '0.9rem' }}>
            Modern talent acquisition for hiring teams
          </p>
        </div>
        <div className="hf-panel hf-fade-up" style={{ padding: '1.75rem', background: 'var(--hf-bg-elevated)' }}>
          <Outlet />
        </div>
      </div>
    </div>
  )
}
