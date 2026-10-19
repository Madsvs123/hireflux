import { analyticsApi } from '../../api/analytics'
import { useApi } from '../../hooks/useApi'
import { PageHeader } from '../../components/layout/PageHeader'
import { Card, EmptyState, Spinner, StatCard } from '../../components/ui'

const FALLBACK = {
  open_jobs: 12,
  active_candidates: 248,
  applications_this_month: 86,
  interviews_scheduled: 19,
  offers_pending: 4,
  hires_this_month: 7,
  avg_time_to_hire_days: 24,
  funnel: [
    { stage: 'Applied', count: 320 },
    { stage: 'Screen', count: 180 },
    { stage: 'Interview', count: 92 },
    { stage: 'Offer', count: 28 },
    { stage: 'Hired', count: 18 },
  ],
  sources: [
    { source: 'Career page', count: 120 },
    { source: 'LinkedIn', count: 88 },
    { source: 'Referral', count: 54 },
    { source: 'Agency', count: 31 },
    { source: 'Other', count: 27 },
  ],
  time_to_hire_by_dept: [
    { department: 'Engineering', days: 28 },
    { department: 'Product', days: 22 },
    { department: 'Sales', days: 18 },
    { department: 'People', days: 20 },
  ],
}

export function AnalyticsPage() {
  const overview = useApi(() => analyticsApi.overview(), [])
  const data = overview.data || (overview.error ? FALLBACK : null)
  const usingFallback = Boolean(overview.error && data)

  if (overview.loading && !data) {
    return (
      <div style={{ padding: 64, display: 'grid', placeItems: 'center' }}>
        <Spinner label="Loading analytics…" />
      </div>
    )
  }

  if (!data) {
    return <EmptyState title="No analytics yet" description="Publish jobs and move candidates to populate insights." />
  }

  const maxFunnel = Math.max(...data.funnel.map((f) => f.count, 1)
  const maxSource = Math.max(...data.sources.map((s) => s.count), 1)
  const maxDays = Math.max(...data.time_to_hire_by_dept.map((d) => d.days), 1)

  return (
    <div className="hf-page">
      <PageHeader
        title="Analytics"
        subtitle={
          usingFallback
            ? 'Showing sample insights while the analytics API is unavailable.'
            : 'Funnel health, source mix, and time-to-hire across departments.'
        }
      />
      <div className="hf-grid-stats">
        <StatCard label="Open jobs" value={data.open_jobs} />
        <StatCard label="Active candidates" value={data.active_candidates} />
        <StatCard label="Applications (month)" value={data.applications_this_month} />
        <StatCard label="Interviews" value={data.interviews_scheduled} />
        <StatCard label="Pending offers" value={data.offers_pending} />
        <StatCard label="Avg time to hire" value={`${data.avg_time_to_hire_days}d`} />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: 16 }}>
        <Card title="Hiring funnel">
          <div className="hf-bar-chart">
            {data.funnel.map((row) => (
              <div key={row.stage} className="hf-bar-row">
                <span>{row.stage}</span>
                <div className="hf-bar-track">
                  <div className="hf-bar-fill" style={{ width: `${(row.count / maxFunnel) * 100}%` }} />
                </div>
                <strong>{row.count}</strong>
              </div>
            ))}
          </div>
        </Card>
        <Card title="Sources">
          <div className="hf-bar-chart">
            {data.sources.map((row) => (
              <div key={row.source} className="hf-bar-row">
                <span>{row.source}</span>
                <div className="hf-bar-track">
                  <div
                    className="hf-bar-fill"
                    style={{
                      width: `${(row.count / maxSource) * 100}%`,
                      background: 'linear-gradient(90deg, #0ea5e9, #2dd4bf)',
                    }}
                  />
                </div>
                <strong>{row.count}</strong>
              </div>
            ))}
          </div>
        </Card>
      </div>

      <Card title="Time to hire by department">
        <div className="hf-bar-chart">
          {data.time_to_hire_by_dept.map((row) => (
            <div key={row.department} className="hf-bar-row">
              <span>{row.department}</span>
              <div className="hf-bar-track">
                <div
                  className="hf-bar-fill"
                  style={{
                    width: `${(row.days / maxDays) * 100}%`,
                    background: 'linear-gradient(90deg, #115e59, #14b8a6)',
                  }}
                />
              </div>
              <strong>{row.days}d</strong>
            </div>
          ))}
        </div>
      </Card>
    </div>
  )
}
