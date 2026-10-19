import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Plus } from 'lucide-react'
import { jobsApi } from '../../api/jobs'
import { useApi } from '../../hooks/useApi'
import { PageHeader } from '../../components/layout/PageHeader'
import { Badge, Button, Card, DataTable, FilterBar, Pagination } from '../../components/ui'
import { formatCurrency, formatDate, titleCase } from '../../utils/format'

export function JobListPage() {
  const navigate = useNavigate()
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState(''
  const { data, loading, error, reload } = useApi(
    () =>
      jobsApi.list({
        page,
        page_size: 20,
        search: search || undefined,
        status: status || undefined,
      }),
    [page, search, status],
  )

  return (
    <div className="hf-page">
      <PageHeader
        title="Jobs"
        subtitle="Create, publish, and manage requisitions across your organization."
        actions={
          <Button leftIcon={<Plus size={16} />} onClick={() => navigate('/app/jobs/new')}>
            New job
          </Button>
        }
      />

      <Card padding="1rem">
        <FilterBar
          search={search}
          onSearchChange={(v) => {
            setPage(1)
            setSearch(v)
          }}
          searchPlaceholder="Search jobs…"
          filters={[
            {
              key: 'status',
              label: 'Status',
              value: status,
              onChange: (v) => {
                setPage(1)
                setStatus(v)
              },
              options: [
                { value: 'draft', label: 'Draft' },
                { value: 'pending_approval', label: 'Pending approval' },
                { value: 'published', label: 'Published' },
                { value: 'paused', label: 'Paused' },
                { value: 'closed', label: 'Closed' },
              ],
            },
          ]}
          onClear={() => {
            setSearch('')
            setStatus('')
            setPage(1)
          }}
        />
      </Card>

      {error && (
        <Card>
          <p style={{ color: 'var(--hf-danger)' }}>{error}</p>
          <Button variant="outline" size="sm" onClick={reload} style={{ marginTop: 8 }}>
            Retry
          </Button>
        </Card>
      )}

      <Card padding={0}>
        <DataTable
          loading={loading}
          columns={[
            {
              key: 'title',
              header: 'Title',
              render: (j) => (
                <div>
                  <Link to={`/app/jobs/${j.id}`} style={{ fontWeight: 650, textDecoration: 'none' }}>
                    {j.title}
                  </Link>
                  <div className="hf-subtle" style={{ fontSize: '0.75rem' }}>
                    {j.department_name || '—'} · {titleCase(j.employment_type)}
                  </div>
                </div>
              ),
            },
            { key: 'location', header: 'Location', render: (j) => j.office_name || titleCase(j.remote_policy) },
            { key: 'status', header: 'Status', render: (j) => <Badge status={j.status} /> },
            {
              key: 'comp',
              header: 'Compensation',
              render: (j) =>
                j.salary_visible
                  ? `${formatCurrency(j.salary_min, j.currency)} – ${formatCurrency(j.salary_max, j.currency)}`
                  : '—',
            },
            { key: 'openings', header: 'Openings', render: (j) => j.openings },
            { key: 'created', header: 'Created', render: (j) => formatDate(j.updated_at) },
          ]}
          rows={data?.results || []}
          rowKey={(j) => j.id}
          emptyTitle="No jobs found"
          emptyDescription="Create your first requisition to start hiring."
          onRowClick={(j) => navigate(`/app/jobs/${j.id}`)}
        />
        {data && (
          <Pagination page={page} pageSize={20} total={data.count} onChange={setPage} />
        )}
      </Card>
    </div>
  )
}
