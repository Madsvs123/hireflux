import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { interviewsApi } from '../../api/interviews'
import { useApi } from '../../hooks/useApi'
import { PageHeader } from '../../components/layout/PageHeader'
import { Badge, Button, Card, DataTable, FilterBar, Pagination } from '../../components/ui'
import { formatDateTime, titleCase } from '../../utils/format'

export function InterviewListPage() {
  const navigate = useNavigate()
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [view, setView] = useState<'list' | 'calendar'>('list'
  const { data, loading, error, reload } = useApi(
    () => interviewsApi.list({ page, page_size: 20, search: search || undefined }),
    [page, search],
  )

  return (
    <div className="hf-page">
      <PageHeader
        title="Interviews"
        subtitle="Schedule scorecards and keep interview loops on track."
        actions={
          <>
            <Button variant={view === 'list' ? 'primary' : 'outline'} size="sm" onClick={() => setView('list')}>
              List
            </Button>
            <Button
              variant={view === 'calendar' ? 'primary' : 'outline'}
              size="sm"
              onClick={() => setView('list')}
            >
              Calendar
            </Button>
          </>
        }
      />
      <Card padding="1rem">
        <FilterBar
          search={search}
          onSearchChange={(v) => {
            setPage(1)
            setSearch(v)
          }}
          searchPlaceholder="Search interviews…"
        />
      </Card>
      {error && (
        <Card>
          <p style={{ color: 'var(--hf-danger)' }}>{error}</p>
          <Button variant="outline" size="sm" onClick={reload}>
            Retry
          </Button>
        </Card>
      )}
      {view === 'calendar' ? (
        <Card title="Interview calendar">
          <div style={{ display: 'grid', gap: 10 }}>
            {(data?.results || []).map((iv) => (
              <button
                key={iv.id}
                onClick={() => navigate(`/app/interviews/${iv.id}`)}
                style={{
                  textAlign: 'left',
                  border: '1px solid var(--hf-border)',
                  borderRadius: 12,
                  padding: 12,
                  background: 'var(--hf-bg-elevated)',
                  cursor: 'pointer',
                }}
              >
                <div style={{ fontWeight: 650 }}>{iv.candidate_name || iv.title}</div>
                <div className="hf-subtle" style={{ fontSize: '0.8rem' }}>
                  {formatDateTime(iv.scheduled_at)} · {iv.job_title || titleCase(iv.interview_type)}
                </div>
              </button>
            ))}
            {!data?.results?.length && <p className="hf-muted">No interviews scheduled.</p>}
          </div>
        </Card>
      ) : (
        <Card padding={0}>
          <DataTable
            loading={loading}
            columns={[
              { key: 'candidate', header: 'Candidate', render: (r) => r.candidate_name || r.title },
              { key: 'job', header: 'Job', render: (r) => r.job_title || '—' },
              { key: 'type', header: 'Type', render: (r) => titleCase(r.interview_type) },
              { key: 'when', header: 'When', render: (r) => formatDateTime(r.scheduled_at) },
              { key: 'status', header: 'Status', render: (r) => <Badge status={r.status} /> },
            ]}
            rows={data?.results || []}
            rowKey={(r) => r.id}
            emptyTitle="No interviews"
            emptyDescription={
              error ? 'Interviews API may not be available yet.' : 'Schedule interviews from an application.'
            }
            onRowClick={(r) => navigate(`/app/interviews/${r.id}`)}
          />
          {data && <Pagination page={page} pageSize={20} total={data.count} onChange={setPage} />}
        </Card>
      )}
    </div>
  )
}
