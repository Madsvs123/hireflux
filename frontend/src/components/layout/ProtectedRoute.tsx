import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'
import { Spinner } from '../ui'

interface ProtectedRouteProps {
  staffOnly?: boolean
  candidateOnly?: boolean
}

export function ProtectedRoute({ staffOnly, candidateOnly }: ProtectedRouteProps) {
  const { isAuthenticated, isStaff, isCandidate, loading } = useAuth()
  const location = useLocation()

  if (loading) {
    return (
      <div style={{ minHeight: '60vh', display: 'grid', placeItems: 'center' }}>
        <Spinner label="Loading…" />
      </div>
    )
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />
  }

  if (staffOnly && !isStaff && !isCandidate) {
    return <Navigate to="/portal" replace />
  }

  if (candidateOnly && !isCandidate) {
    return <Navigate to="/app" replace />
  }

  return <Outlet />
}
