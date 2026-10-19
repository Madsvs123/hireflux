import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search } from 'lucide-react'
import { coreApi } from '../../api/core'
import { PageHeader } from '../../components/layout/PageHeader'
import { Badge, Button, Card, EmptyState, Input, Spinner } from '../../components/ui'
import { titleCase } from '../../utils/format'

export function SearchPage() {
  const [q, setQ] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [results, setResults] = useState<Awaited<ReturnType<typeof coreApi.search>> | null>(null)
  const navigate = useNavigate()

  async function runSearch(e?: FormEvent) {
    e?.preventDefault()
    if (!q.trim()) return
    setLoading(true)
    setError(null)
    try {
      const data = await coreApi.search(q.trim())
      setResults(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Search failed')
      setResults(null)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="hf-page">
      <PageHeader title="Search" subtitle="Find jobs, candidates, and applications across your workspace." />
      <Card>
        <form onSubmit={(e) => void runSearch(e)} style={{ display: 'flex', gap: 10 }}>
          <Input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search HireFlux…"
            leftAddon={<Search size={15} />}
          />
          <Button type="submit" loading={loading}>
            Search
          </Button>
        </form>
      </Card>

      {loading && (
        <div style={{ display: 'grid', placeItems: 'center', padding: 32 }}>
          <Spinner />
        </div>
      )}
      {error && <Card><p style={{ color: 'var(--hf-danger)' }}>{error}</p></Card>}

      {results && !loading && (
        <div style={{ display: 'grid', gap: 16 }}>
          <ResultGroup
            title="Jobs"
            items={(results.candidates || []).map((j) => ({
              id: j.id,
              title: j.title,
              meta: `${titleCase(j.status)} · ${j.department_name || '—'}`,
              onClick: () => navigate(`/app/jobs/${j.id}`),
            }))}
          />
          <ResultGroup
            title="Candidates"
            items={(results.candidates || []).map((c) => ({
              id: c.id,
              title: c.full_name || c.name,
              meta: c.email,
              onClick: () => navigate(`/app/candidates/${c.id}`),
            }))}
          />
          <ResultGroup
            title="Applications"
            items={(results.applications || []).map((a) => ({
              id: a.id,
              title: `${a.candidate_name} → ${a.job_title}`,
              meta: a.stage_name || titleCase(a.status),
              onClick: () => navigate(`/app/pipeline/applications/${a.id}`),
            }))}
          />
        </div>
      )}

      {!results && !loading && !error && (
        <Card>
          <EmptyState title="Search your ATS" description="Type a name, skill, or job title to get started." />
        </Card>
      )}
    </div>
  )
}

function ResultGroup({
  title,
  items,
}: {
  title: string
  items: Array<{ id: string; title: string; meta: string; onClick: () => void }>
}) {
  return (
    <Card title={title} actions={<Badge tone="neutral">{items.length}</Badge>}>
      {items.length ? (
        items.map((item) => (
          <button
            key={item.id}
            onClick={item.onClick}
            style={{
              width: '100%',
              textAlign: 'left',
              border: 'none',
              borderBottom: '1px solid var(--hf-border)',
              background: 'transparent',
              padding: '0.75rem 0',
              cursor: 'pointer',
            }}
          >
            <div style={{ fontWeight: 650 }}>{item.title}</div>
            <div className="hf-subtle" style={{ fontSize: '0.8rem' }}>
              {item.meta}
            </div>
          </button>
        ))
      ) : (
        <p className="hf-muted" style={{ fontSize: '0.85rem' }}>
          No matches
        </p>
      )}
    </Card>
  )
}
