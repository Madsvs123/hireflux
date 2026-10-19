import { useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { talentApi } from '../../api/talent'
import { useApi } from '../../hooks/useApi'
import { PageHeader } from '../../components/layout/PageHeader'
import { Badge, Button, Card, DataTable, EmptyState, Input, Modal, Textarea, useToast } from '../../components/ui'
import { formatDate } from '../../utils/format'
import { ApiError } from '../../api/http'

export function TalentPoolsPage() {
  const { toast } = useToast()
  const [open, setOpen] = useState(false)
  const pools = useApi(() => talentApi.listPools({ page_size: 50 }), [])

  return (
    <div className="hf-page">
      <PageHeader
        title="Talent pools"
        subtitle="Segment passive candidates for future roles."
        actions={
          <>
            <Link to="/app/talent/referrals" style={{ textDecoration: 'none' }}>
              <Button variant="outline">Referrals</Button>
            </Link>
            <Button onClick={() => setOpen(true)}>New pool</Button>
          </>
        }
      />
      {pools.error && (
        <Card>
          <p className="hf-muted">{pools.error}</p>
        </Card>
      )}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: 14 }}>
        {(pools.data?.results || []).map((p) => (
          <Card key={p.id} title={p.name} subtitle={p.description}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <strong>{p.candidate_count} candidates</strong>
              <Badge tone={p.is_active ? 'success' : 'neutral'}>{p.is_active ? 'Active' : 'Inactive'}</Badge>
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 10 }}>
              {(p.tags || []).map((t) => (
                <Badge key={t}>{t}</Badge>
              ))}
            </div>
          </Card>
        ))}
      </div>
      {!pools.loading && !pools.data?.results?.length && (
        <Card>
          <EmptyState title="No talent pools" description="Create a pool to nurture passive talent." actionLabel="Create pool" onAction={() => setOpen(true)} />
        </Card>
      )}
      <CreatePoolModal
        open={open}
        onClose={() => setOpen(false)}
        onCreated={() => {
          setOpen(false)
          toast('Pool created', 'success')
          pools.reload()
        }}
      />
    </div>
  )
}

function CreatePoolModal({
  open,
  onClose,
  onCreated,
}: {
  open: boolean
  onClose: () => void
  onCreated: () => void
}) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [loading, setLoading] = useState(false)
  const { toast } = useToast()

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setLoading(true)
    try {
      await talentApi.createPool({ name, description, tags: [], is_active: true, candidate_count: 0 })
      onCreated()
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Failed', 'error')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Modal open={open} onClose={onClose} title="New talent pool">
      <form onSubmit={onSubmit} style={{ display: 'grid', gap: 12 }}>
        <Input label="Name" required value={name} onChange={(e) => setName(e.target.value)} />
        <Textarea label="Description" value={description} onChange={(e) => setDescription(e.target.value)} />
        <Button type="submit" loading={loading}>
          Create
        </Button>
      </form>
    </Modal>
  )
}

export function ReferralsPage() {
  const referrals = useApi(() => talentApi.listReferrals({ page_size: 50 }), [])

  return (
    <div className="hf-page">
      <PageHeader title="Referrals" subtitle="Employee and agency referrals across open roles." />
      <Card padding={0}>
        <DataTable
          loading={referrals.loading}
          columns={[
            { key: 'candidate', header: 'Candidate', render: (r) => r.candidate_name },
            { key: 'email', header: 'Email', render: (r) => r.candidate_email },
            { key: 'job', header: 'Job', render: (r) => r.job_title || '—' },
            { key: 'by', header: 'Referred by', render: (r) => r.referred_by_name },
            { key: 'status', header: 'Status', render: (r) => <Badge status={r.status} /> },
            { key: 'date', header: 'Date', render: (r) => formatDate(r.created_at) },
          ]}
          rows={referrals.data?.results || []}
          rowKey={(r) => r.candidate_email}
          emptyTitle="No referrals"
          emptyDescription={referrals.error || 'Referrals will appear here once submitted.'}
        />
      </Card>
    </div>
  )
}
