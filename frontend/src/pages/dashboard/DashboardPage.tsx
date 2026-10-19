import { useMemo } from 'react'
import { Link } from 'react-router-dom'
import { Briefcase, Users, Calendar, FileSignature, TrendingUp, Clock } from 'lucide-react'
import { jobsApi } from '../../api/jobs'
import { candidatesApi } from '../../api/candidates'
import { applicationsApi } from '../../api/pipelines'
import { interviewsApi } from '../../api/interviews'
import { offersApi } from '../../api/offers'
import { useApi } from '../../hooks/useApi'
import { PageHeader } from '../../components/layout/PageHeader'
import { Badge, Card, DataTable, Spinner, StatCard } from '../../components/ui'
import { formatDate, formatRelative, titleCase } from '../../utils/format'
import { useAuth } from '../../hooks/useAuth'

export function DashboardPage() {
  const { user } = useAuth()
  const jobs = useApi(() => jobsApi.list({ page_size: 5, ordering: '-created_at' }), [])
  const candidates = useApi(() => candidatesApi.list({ page_size: 5 }), [])
  const apps = useApi(() => applicationsApi.list({ page_size: 8, ordering: '-applied_at' }), [])
  const interviews = useApi(() => interviewsApi.list({ page_size: 5, ordering: 'scheduled_at' }), [])
  const offers = useApi(() => offersApi.list({ page_size: 5, status: 'pending' }), [])

  const loading = jobs.loading && candidates.loading && apps.loading

  const stats = useMemo(
    () => [
      {
        label: 'Open jobs',
        value: jobs.data?.count ?? '—',
        icon: <Briefcase size={16} />,
        hint: 'Active requisitions',
      },
      {
        label: 'Candidates',
        value: candidates.data?.count ?? '—',
        icon: <Users size={16} />,
        hint: 'In your talent database',
      },
      {
        label: 'Applications',
        value: apps.data?.count ?? '—',
        icon: <TrendingUp size={16} />,
        hint: 'Across all pipelines',
      },
      {
        label: 'Interviews',
        value: interviews.data?.count ?? '—',
        icon: <Calendar size={16} />,
        hint: 'Scheduled upcoming',
      },
      {
        label: 'Pending offers',
        value: offers.data?.count ?? '—',
        icon: <FileSignature size={16} />,
        hint: 'Awaiting response',
      },
      {
        label: 'Time to hire',
        value: '24d',
        icon: <Clock size={16} />,
        hint: 'Org average (sample)',
        trend: '↓ 3d',
      },
    ],
    [jobs.data, candidates.data, apps.data, interviews.data, offers.data],
  )

  return (
    <div className="hf-page">
      <PageHeader
        title={`Good ${greeting()}, ${user?.last_name || 'there'}`}
        subtitle="Here’s what’s happening across your hiring pipeline today."
        actions={
          <>
            <Link to="/app/jobs/new" style={{ textDecoration: 'none' }}>
              <span
                style={{
                  display: 'inline-flex',
                  height: 40,
                  alignItems: 'center',
                  padding: '0 1rem',
                  borderRadius: 8,
                  background: 'linear-gradient(135deg, var(--hf-teal-700), var(--hf-teal-600))',
                  color: '#fff',
                  fontWeight: 600,
                  fontSize: '0.9rem',
                }}
              >
                New job
              </span>
            </Link>
          </>
        }
      />

      {loading ? (
        <div style={{ padding: 48, display: 'grid', placeItems: 'center' }}>
          <Spinner label="Loading dashboard…" />
        </div>
      ) : (
        <>
          <div className="hf-grid-stats">
            {stats.map((s) => (
              <StatCard key={s.label} {...s} />
            ))}
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1.4fr 1fr', gap: 16 }}>
            <Card title="Recent applications" subtitle="Latest candidates moving through the funnel">
              <DataTable
                columns={[
                  {
                    key: 'candidate',
                    header: 'Candidate',
                    render: (r) => (
                      <div>
                        <div style={{ fontWeight: 600 }}>{r.candidate_name}</div>
                        <div className="hf-subtle" style={{ fontSize: '0.75rem' }}>
                          {r.candidate_email}
                        </div>
                      </div>
                    ),
                  },
                  { key: 'job', header: 'Job', render: (r) => r.job_title },
                  { key: 'stage', header: 'Stage', render: (r) => r.stage_name || titleCase(r.status) },
                  {
                    key: 'applied',
                    header: 'Applied',
                    render: (r) => formatRelative(r.applied_at),
                  },
                ]}
                rows={apps.data?.results || []}
                rowKey={(r) => r.id}
                emptyTitle="No applications yet"
                emptyDescription="Publish a job and start receiving applications."
                onRowClick={(r) => {
                  window.location.href = `/app/pipeline/applications/${r.id}`
                }}
              />
            </Card>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              <Card title="Open roles" actions={<Link to="/app/jobs">View all</Link>}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                  {(jobs.data?.results || []).slice(0, 5).map((job) => (
                    <Link
                      key={job.id}
                      to={`/app/jobs/${job.id}`}
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        gap: 8,
                        padding: '0.65rem 0',
                        borderBottom: '1px solid var(--hf-border)',
                        textDecoration: 'none',
                        color: 'inherit',
                      }}
                    >
                      <div>
                        <div style={{ fontWeight: 600, fontSize: '0.9rem' }}>{job.title}</div>
                        <div className="hf-subtle" style={{ fontSize: '0.75rem' }}>
                          {job.department_name || 'No department'} · {formatDate(job.created_at)}
                        </div>
                      </div>
                      <Badge status={job.status} />
                    </Link>
                  ))}
                  {!jobs.data?.results?.length && (
                    <p className="hf-muted" style={{ fontSize: '0.85rem' }}>
                      No jobs yet.
                    </p>
                  )}
                </div>
              </Card>

              <Card title="Upcoming interviews" actions={<Link to="/app/interviews">Calendar</Link>}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                  {(interviews.data?.results || []).slice(0, 4).map((iv) => (
                    <Link
                      key={iv.id}
                      to={`/app/interviews/${iv.id}`}
                      style={{ textDecoration: 'none', color: 'inherit', padding: '0.4rem 0' }}
                    >
                      <div style={{ fontWeight: 600, fontSize: '0.88rem' }}>
                        {iv.candidate_name || iv.title}
                      </div>
                      <div className="hf-subtle" style={{ fontSize: '0.75rem' }}>
                        {formatDate(iv.scheduled_at)} · {iv.job_title || titleCase(iv.interview_type)}
                      </div>
                    </Link>
                  ))}
                  {(interviews.error || !interviews.data?.results?.length) && (
                    <p className="hf-muted" style={{ fontSize: '0.85rem' }}>
                      {interviews.error ? 'Interviews API not available yet.' : 'No interviews scheduled.'}
                    </p>
                  )}
                </div>
              </Card>
            </div>
          </div>
        </>
      )}
      <style>{`
        @media (max-width: 960px) {
          .hf-page > div[style*="grid-template-columns: 1.4fr"] {
            grid-template-columns: 1fr !important;
          }
        }
      `}</style>
    </div>
  )
}

function greeting() {
  const h = new Date().getHours()
  if (h < 12 return 'morning'
  if (h < 18) return 'afternoon'
  return 'evening'
}
