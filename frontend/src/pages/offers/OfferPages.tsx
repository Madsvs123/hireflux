import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { offersApi } from '../../api/offers'
import { useApi } from '../../hooks/useApi'
import { PageHeader } from '../../components/layout/PageHeader'
import { Badge, Button, Card, DataTable, EmptyState, Pagination, Spinner, useToast } from '../../components/ui'
import { formatCurrency, formatDate } from '../../utils/format'
import { ApiError } from '../../api/http'

export function OfferListPage() {
  const navigate = useNavigate()
  const [page, setPage] = useState(1)
  const { data, loading, error, reload } = useApi(() => offersApi.list({ page, page_size: 20 }), [page])

  return (
    <div className="hf-page">
      <PageHeader title="Offers" subtitle="Approve, send, and track offer letters." />
      {error && (
        <Card>
          <p style={{ color: 'var(--hf-danger)' }}>{error}</p>
          <Button variant="outline" size="sm" onClick={reload}>
            Retry
          </Button>
        </Card>
      )}
      <Card padding={0}>
        <DataTable
          loading={loading}
          columns={[
            { key: 'candidate', header: 'Candidate', render: (o) => o.candidate_name || '—' },
            { key: 'job', header: 'Job', render: (o) => o.job_title || '—' },
            {
              key: 'salary',
              header: 'Salary',
              render: (o) => formatCurrency(o.salary, o.currency),
            },
            { key: 'status', header: 'Status', render: (o) => <Badge status={o.status} /> },
            { key: 'approval', header: 'Approval', render: (o) => <Badge status={o.approval_status} /> },
            { key: 'start', header: 'Start', render: (o) => formatDate(o.created_at) },
          ]}
          rows={data?.results || []}
          rowKey={(o) => o.id}
          emptyTitle="No offers"
          emptyDescription={error ? 'Offers API may not be available yet.' : 'Create an offer from a hired application.'}
          onRowClick={(o) => navigate(`/app/offers/${o.id}`)}
        />
        {data && <Pagination page={page} pageSize={20} total={data.count} onChange={setPage} />}
      </Card>
    </div>
  )
}

export function OfferDetailPage() {
  const { id = '' } = useParams()
  const navigate = useNavigate()
  const { toast } = useToast()
  const offer = useApi(() => offersApi.get(id), [id], { enabled: Boolean(id) })
  const [acting, setActing] = useState(false)

  async function act(fn: () => Promise<unknown>, msg: string) {
    setActing(true)
    try {
      await fn()
      toast(msg, 'success')
      offer.reload()
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Action failed', 'error')
    } finally {
      setActing(false)
    }
  }

  if (offer.loading) {
    return (
      <div style={{ padding: 64, display: 'grid', placeItems: 'center' }}>
        <Spinner />
      </div>
    )
  }
  if (offer.error || !offer.data) {
    return (
      <EmptyState
        title="Offer not found"
        description={offer.error || undefined}
        actionLabel="Back"
        onAction={() => navigate('/app/offers')}
      />
    )
  }
  const o = offer.data
  return (
    <div className="hf-page">
      <PageHeader
        title={`Offer · ${o.candidate_name || 'Candidate'}`}
        subtitle={o.job_title}
        actions={
          <>
            <Badge status={o.status} />
            <Button variant="secondary" loading={acting} onClick={() => act(() => offersApi.submitApproval(id), 'Submitted for approval')}>
              Submit approval
            </Button>
            <Button variant="outline" loading={acting} onClick={() => act(() => offersApi.approve(id), 'Offer approved')}>
              Approve
            </Button>
            <Button loading={acting} onClick={() => act(() => offersApi.send(id), 'Offer sent')}>
              Send offer
            </Button>
          </>
        }
      />
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        <Card title="Compensation">
          <dl style={{ margin: 0, display: 'grid', gap: 10 }}>
            <Row label="Salary" value={formatCurrency(o.salary, o.currency)} />
            <Row label="Bonus" value={o.bonus || '—'} />
            <Row label="Equity" value={o.equity || '—'} />
            <Row label="Start date" value={formatDate(o.start_date)} />
            <Row label="Approval" value={o.approval_status} />
          </dl>
        </Card>
        <Card title="Notes & benefits">
          <p className="hf-muted" style={{ whiteSpace: 'pre-wrap' }}>
            {o.benefits || 'No benefits listed.'}
          </p>
          {o.notes && (
            <p className="hf-muted" style={{ marginTop: 12, whiteSpace: 'pre-wrap' }}>
              {o.notes}
            </p>
          )}
        </Card>
      </div>
    </div>
  )
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, fontSize: '0.9rem' }}>
      <dt className="hf-muted">{label}</dt>
      <dd style={{ margin: 0, fontWeight: 600 }}>{value}</dd>
    </div>
  )
}
