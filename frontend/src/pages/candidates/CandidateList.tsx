import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { Plus } from 'lucide-react'
import { candidatesApi } from '../../api/candidates'
import { useApi } from '../../hooks/useApi'
import { PageHeader } from '../../components/layout/PageHeader'
import { Avatar, Badge, Button, Card, DataTable, FilterBar, Modal, Input, Pagination, useToast } from '../../components/ui'
import { formatRelative } from '../../utils/format'
import { ApiError } from '../../api/http'

export function CandidateListPage() {
  const navigate = useNavigate()
  const { toast } = useToast()
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [createOpen, setCreateOpen] = useState(false)
  const { data, loading, error, reload } = useApi(
    () => candidatesApi.list({ page, page_size: 20, search: search || undefined }),
    [page, search],
  )

  return (
    <div className="hf-page">
      <PageHeader
        title="Candidates"
        subtitle="Search, enrich, and manage your talent database."
        actions={
          <Button leftIcon={<Plus size={16} />} onClick={() => setCreateOpen(true)}>
            Add candidate
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
          searchPlaceholder="Search by name, email, skills…"
          onClear={() => {
            setSearch('')
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
              key: 'name',
              header: 'Candidate',
              render: (c) => (
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <Avatar name={c.full_name || c.name} size={34} />
                  <div>
                    <div style={{ fontWeight: 650 }}>{c.full_name || c.name}</div>
                    <div className="hf-subtle" style={{ fontSize: '0.75rem' }}>
                      {c.email}
                    </div>
                  </div>
                </div>
              ),
            },
            { key: 'headline', header: 'Headline', render: (c) => c.headline || '—' },
            { key: 'location', header: 'Location', render: (c) => c.location || '—' },
            {
              key: 'tags',
              header: 'Tags',
              render: (c) => (
                <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                  {(c.tags || []).slice(0, 3).map((t) => (
                    <Badge key={t} tone="neutral">
                      {t}
                    </Badge>
                  ))}
                </div>
              ),
            },
            { key: 'source', header: 'Source', render: (c) => c.source || '—' },
            { key: 'updated', header: 'Updated', render: (c) => formatRelative(c.created_at) },
          ]}
          rows={data?.results || []}
          rowKey={(c) => c.email}
          emptyTitle="No candidates"
          emptyDescription="Add candidates manually or receive applications from the career page."
          onRowClick={(c) => navigate(`/app/candidates/${c.id}`)}
        />
        {data && <Pagination page={page} pageSize={20} total={data.count} onChange={setPage} />}
      </Card>

      <CreateCandidateModal
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        onCreated={(id) => {
          setCreateOpen(false)
          toast('Candidate created', 'success')
          navigate(`/app/candidates/${id}`)
        }}
      />
    </div>
  )
}

function CreateCandidateModal({
  open,
  onClose,
  onCreated,
}: {
  open: boolean
  onClose: () => void
  onCreated: (id: string) => void
}) {
  const [form, setForm] = useState({
    first_name: ''
    last_name: '',
    email: '',
    phone: '',
    headline: '',
    source: 'manual',
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const c = await candidatesApi.create(form)
      onCreated(c.id)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Create failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Add candidate"
      footer={
        <>
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button loading={loading} onClick={() => void (document.getElementById('create-candidate-form') as HTMLFormElement | null)?.requestSubmit()}>
            Create
          </Button>
        </>
      }
    >
      <form id="create-candidate-form" onSubmit={onSubmit} style={{ display: 'grid', gap: 12 }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
          <Input label="First name" required value={form.first_name} onChange={(e) => setForm({ ...form, first_name: e.target.value })} />
          <Input label="Last name" value={form.last_name} onChange={(e) => setForm({ ...form, last_name: e.target.value })} />
        </div>
        <Input label="Email" type="email" required value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
        <Input label="Phone" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
        <Input label="Headline" value={form.headline} onChange={(e) => setForm({ ...form, headline: e.target.value })} />
        {error && <p style={{ color: 'var(--hf-danger)', fontSize: '0.85rem' }}>{error}</p>}
      </form>
    </Modal>
  )
}
