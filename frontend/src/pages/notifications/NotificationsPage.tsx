import { coreApi } from '../../api/core'
import { useApi } from '../../hooks/useApi'
import { PageHeader } from '../../components/layout/PageHeader'
import { Badge, Button, Card, EmptyState, Spinner, useToast } from '../../components/ui'
import { formatRelative } from '../../utils/format'
import { ApiError } from '../../api/http'
import { useNavigate } from 'react-router-dom'

export function NotificationsPage() {
  const { data, loading, error, reload } = useApi(() => coreApi.listNotifications({ page_size: 50 ), [])
  const { toast } = useToast()
  const navigate = useNavigate()

  async function markAll() {
    try {
      await coreApi.markAllNotificationsRead()
      toast('Marked all as read', 'success')
      reload()
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Failed', 'error')
    }
  }

  async function markOne(id: string) {
    try {
      await coreApi.markNotificationRead(id)
      reload()
    } catch {
      /* ignore */
    }
  }

  return (
    <div className="hf-page">
      <PageHeader
        title="Notifications"
        subtitle="Approvals, stage moves, interviews, and system alerts."
        actions={
          <Button variant="outline" onClick={() => void markAll()}>
            Mark all read
          </Button>
        }
      />
      {loading && (
        <div style={{ padding: 48, display: 'grid', placeItems: 'center' }}>
          <Spinner />
        </div>
      )}
      {error && (
        <Card>
          <p style={{ color: 'var(--hf-danger)' }}>{error}</p>
          <Button variant="outline" size="sm" onClick={reload}>
            Retry
          </Button>
        </Card>
      )}
      <Card padding={0}>
        {(data?.results || []).map((n) => (
          <button
            key={n.id}
            onClick={() => {
              void markOne(n.id)
              if (n.link) navigate(n.link)
            }}
            style={{
              width: '100%',
              textAlign: 'left',
              border: 'none',
              borderBottom: '1px solid var(--hf-border)',
              background: n.is_read ? 'var(--hf-primary-soft)' : 'transparent',
              padding: '1rem 1.25rem',
              cursor: 'pointer',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}>
              <div>
                <div style={{ fontWeight: 650 }}>{n.title}</div>
                <p className="hf-muted" style={{ marginTop: 4, fontSize: '0.88rem' }}>
                  {n.body}
                </p>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 6 }}>
                <Badge tone={n.level === 'error' ? 'danger' : n.level === 'warning' ? 'warning' : 'info'}>
                  {n.category || n.level}
                </Badge>
                <span className="hf-subtle" style={{ fontSize: '0.72rem' }}>
                  {formatRelative(n.created_at)}
                </span>
              </div>
            </div>
          </button>
        ))}
        {!loading && !data?.results?.length && (
          <EmptyState title="You're all caught up" description="New notifications will show up here." />
        )}
      </Card>
    </div>
  )
}
