/**
 * HireFlux Billing pages.
 *
 * Exported components (for App.tsx routing):
 *  - BillingPage          -> /app/billing
 *  - PlansPage            -> /app/billing/plans
 *  - InvoicesPage         -> /app/billing/invoices
 *  - PaymentMethodsPage   -> /app/billing/payment-methods
 */
import { useEffect, useRef, useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  BarChart3,
  Building2,
  CreditCard,
  Download,
  HardDrive,
  Plus,
  Receipt,
  Trash2,
  Users,
  Zap,
} from 'lucide-react'
import {
  billingApi,
  type Invoice,
  type PaymentMethod,
  type Plan,
  type PlanChangePreview,
  type Subscription,
} from '../../api/billing'
import { useApi } from '../../hooks/useApi'
import { PageHeader } from '../../components/layout/PageHeader'
import {
  Badge,
  Button,
  Card,
  ConfirmDialog,
  DataTable,
  EmptyState,
  FilterBar,
  Input,
  Modal,
  Pagination,
  Select,
  Spinner,
  StatCard,
  Tabs,
  Timeline,
  useToast,
} from '../../components/ui'
import { formatCurrency, formatDate, formatDateTime, titleCase } from '../../utils/format'
import { ApiError } from '../../api/http'

type Tone = 'neutral' | 'success' | 'warning' | 'danger' | 'info' | 'teal'

const INVOICE_STATUS_FILTERS = [
  { value: 'Draft', label: 'Draft' },
  { value: 'Open', label: 'Open' },
  { value: 'Paid', label: 'Paid' },
  { value: 'Void', label: 'Void' },
  { value: 'Uncollectible', label: 'Uncollectible' },
]
const invoiceStatusToApi: Record<string, string> = {
  Draft: 'draft',
  Open: 'open',
  Paid: 'paid',
  Void: 'void',
  Uncollectible: 'uncollectible',
}

const GRANULARITY_FILTERS = [
  { value: 'Day', label: 'Day' },
  { value: 'Hour', label: 'Hour' },
  { value: 'Month', label: 'Month' },
]
const granularityToApi: Record<string, string> = { Day: 'day', Hour: 'hour', Month: 'month' }

const PAYMENT_TYPE_FILTERS = [
  { value: 'Card', label: 'Card' },
  { value: 'Bank', label: 'Bank' },
]
const paymentTypeToApi: Record<string, string> = { Card: 'card', Bank: 'bank' }

function subscriptionTone(status: string): Tone {
  if (status === 'active') return 'success'
  if (status === 'trialing') return 'info'
  if (status === 'past_due') return 'warning'
  if (status === 'canceled') return 'danger'
  return 'neutral'
}

function invoiceTone(status: string): Tone {
  if (status === 'paid') return 'success'
  if (status === 'open') return 'warning'
  if (status === 'uncollectible') return 'danger'
  return 'neutral'
}

function transactionTone(status: string): Tone {
  if (status === 'succeeded') return 'success'
  if (status === 'pending') return 'warning'
  if (status === 'failed') return 'danger'
  return 'info'
}

/** Refetch when filter/pagination state changes (the shared useApi hook only refetches on reload()). */
function useReloadOnChange(reload: () => void, deps: unknown[]) {
  const first = useRef(true)
  useEffect(() => {
    if (first.current) {
      first.current = false
      return
    }
    reload()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)
}

/* ---------------------------------------------------------------------------
 * Billing overview
 * ------------------------------------------------------------------------ */

export function BillingPage() {
  const navigate = useNavigate()
  const { toast } = useToast()
  const [usageOpen, setUsageOpen] = useState(false)
  const [cancelOpen, setCancelOpen] = useState(false)
  const [acting, setActing] = useState(false)

  const overview = useApi(() => billingApi.overview.get(), [], { enabled: true })
  const activity = useApi(() => billingApi.paymentTransactions.list({ page_size: 5 }), [], {
    enabled: true,
  })

  const sub = overview.data?.subscription ?? null
  const usage = overview.data?.usage ?? {}

  async function cancelSubscription() {
    if (!sub) return
    setActing(true)
    try {
      await billingApi.subscriptions.cancel(sub.id)
      toast('Subscription canceled', 'success')
      overview.reload()
      setCancelOpen(false)
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Cancel failed', 'error')
    } finally {
      setActing(false)
    }
  }

  async function resumeSubscription() {
    if (!sub) return
    setActing(true)
    try {
      await billingApi.subscriptions.resume(sub.id)
      toast('Subscription resumed', 'success')
      overview.reload()
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Resume failed', 'error')
    } finally {
      setActing(false)
    }
  }

  if (overview.loading) {
    return (
      <div style={{ padding: 64, display: 'grid', placeItems: 'center' }}>
        <Spinner label="Loading billing…" />
      </div>
    )
  }
  if (overview.error) {
    return (
      <EmptyState
        title="Billing unavailable"
        description={overview.error || undefined}
        actionLabel="Retry"
        onAction={overview.reload}
      />
    )
  }

  return (
    <div className="hf-page">
      <PageHeader
        title="Billing"
        subtitle="Your plan, invoices, payment methods, and usage at a glance."
        actions={
          <>
            <Button variant="outline" onClick={() => navigate('/app/billing/invoices')}>
              <Receipt size={16} />
              Invoices
            </Button>
            <Button variant="outline" onClick={() => navigate('/app/billing/payment-methods')}>
              <CreditCard size={16} />
              Payment methods
            </Button>
            <Button variant="outline" onClick={() => setUsageOpen(true)}>
              <BarChart3 size={16} />
              Usage details
            </Button>
            <Button onClick={() => navigate('/app/billing/plans')}>Change plan</Button>
          </>
        }
      />

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(190px, 1fr))',
          gap: 14,
        }}
      >
        <StatCard
          label="Outstanding balance"
          value={formatCurrency(overview.data?.outstanding_balance ?? 0)}
          icon={<Receipt size={16} />}
          hint="Open invoices"
        />
        <StatCard
          label="Active jobs"
          value={usage.active_jobs ?? 0}
          icon={<Building2 size={16} />}
          hint="Current metric"
        />
        <StatCard label="Candidates" value={usage.candidates ?? 0} icon={<Users size={16} />} hint="Current metric" />
        <StatCard
          label="Storage (MB)"
          value={usage.storage ?? 0}
          icon={<HardDrive size={16} />}
          hint="Current metric"
        />
        <StatCard label="API calls" value={usage.api_calls ?? 0} icon={<Zap size={16} />} hint="Current metric" />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 16, marginTop: 16 }}>
        <Card>
          <h3 style={{ margin: '0 0 4px' }}>Current plan</h3>
          {sub ? (
            <>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
                <span style={{ fontFamily: 'var(--hf-font-display)', fontSize: '1.35rem', fontWeight: 700 }}>
                  {sub.plan.name}
                </span>
                <Badge tone={subscriptionTone(sub.status)}>{titleCase(sub.status)}</Badge>
                <Badge tone="info">{titleCase(sub.plan.billing_cycle)}</Badge>
                {sub.cancel_at_period_end && <Badge tone="warning">Cancels at period end</Badge>}
              </div>
              <p style={{ margin: '8px 0 14px' }} className="hf-muted">
                {formatCurrency(sub.plan.price_per_month, sub.plan.currency)} / month · {sub.seats}{' '}
                seat(s)
              </p>
              <dl style={{ display: 'grid', gap: 10, margin: 0, fontSize: '0.88rem' }}>
                <Row
                  label="Period"
                  value={`${formatDate(sub.current_period_start)} – ${formatDate(sub.current_period_end)}`}
                />
                <Row label="Trial ends" value={formatDate(sub.trial_end)} />
              </dl>
              <div style={{ display: 'flex', gap: 8, marginTop: 16, flexWrap: 'wrap' }}>
                <Button size="sm" onClick={() => navigate('/app/billing/plans')}>
                  Change plan
                </Button>
                {sub.cancel_at_period_end ? (
                  <Button size="sm" variant="outline" loading={acting} onClick={() => void resumeSubscription()}>
                    Resume
                  </Button>
                ) : (
                  <Button size="sm" variant="outline" onClick={() => setCancelOpen(true)}>
                    Cancel subscription
                  </Button>
                )}
              </div>
            </>
          ) : (
            <EmptyState
              title="No active subscription"
              description="Pick a plan to start billing."
              actionLabel="Browse plans"
              onAction={() => navigate('/app/billing/plans')}
            />
          )}
        </Card>

        <Card>
          <h3 style={{ margin: '0 0 12px' }}>Payment methods</h3>
          {(overview.data?.payment_methods || []).length ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {overview.data!.payment_methods.map((m) => (
                <div
                  key={m.id}
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    gap: 8,
                    padding: 10,
                    borderRadius: 10,
                    border: '1px solid var(--hf-border)',
                    fontSize: '0.88rem',
                  }}
                >
                  <span>
                    {m.brand || titleCase(m.type)} •••• {m.last4 || '—'}
                  </span>
                  {m.is_default && <Badge tone="success">Default</Badge>}
                </div>
              ))}
            </div>
          ) : (
            <p className="hf-muted">No payment methods on file.</p>
          )}
          <div style={{ marginTop: 12 }}>
            <Button size="sm" variant="outline" onClick={() => navigate('/app/billing/payment-methods')}>
              Manage
            </Button>
          </div>
        </Card>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 16, marginTop: 16 }}>
        <Card padding={0}>
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              padding: '0.75rem 1rem',
              borderBottom: '1px solid var(--hf-border)',
            }}
          >
            <h3 style={{ margin: 0 }}>Recent invoices</h3>
            <Button size="sm" variant="ghost" onClick={() => navigate('/app/billing/invoices')}>
              View all
            </Button>
          </div>
          <DataTable
            loading={false}
            columns={[
              { key: 'number', header: 'Invoice', render: (i) => <strong>{i.invoice_number}</strong> },
              {
                key: 'status',
                header: 'Status',
                render: (i) => <Badge tone={invoiceTone(i.status)}>{titleCase(i.status)}</Badge>,
              },
              {
                key: 'total',
                header: 'Total',
                render: (i) => formatCurrency(i.total, i.currency),
              },
              { key: 'due', header: 'Due', render: (i) => formatDate(i.due_at) },
            ]}
            rows={overview.data?.recent_invoices || []}
            rowKey={(i) => i.id}
            emptyTitle="No invoices yet"
          />
        </Card>

        <Card>
          <h3 style={{ margin: '0 0 12px' }}>Recent activity</h3>
          <Timeline
            items={(activity.data?.results || []).map((t) => ({
              id: t.id,
              title: `${titleCase(t.status)} · ${formatCurrency(t.amount, t.currency)}`,
              description: t.invoice_number ? `Invoice ${t.invoice_number}` : 'Payment transaction',
              at: t.created_at,
              meta: t.provider || undefined,
            }))}
          />
        </Card>
      </div>

      <UsageByPeriodModal open={usageOpen} onClose={() => setUsageOpen(false)} />

      <ConfirmDialog
        open={cancelOpen}
        title="Cancel subscription"
        message={
          sub?.cancel_at_period_end
            ? 'This subscription already cancels at the end of the current period.'
            : 'Cancel at the end of the current billing period? You keep access until then.'
        }
        confirmLabel="Cancel subscription"
        danger
        loading={acting}
        onCancel={() => setCancelOpen(false)}
        onConfirm={() => void cancelSubscription()}
      />
    </div>
  )
}

function UsageByPeriodModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [granularity, setGranularity] = useState('Day')
  const usage = useApi(
    () =>
      billingApi.usage.usageByPeriod({
        granularity: granularityToApi[granularity] ?? 'day',
      }),
    [granularity],
    { enabled: open },
  )
  useReloadOnChange(usage.reload, [granularity])

  return (
    <Modal open={open} onClose={onClose} title="Usage by period" width={680}>
      <div style={{ maxWidth: 200, marginBottom: 12 }}>
        <Select
          label="Granularity"
          value={granularity}
          onChange={(e) => setGranularity(e.target.value)}
          options={GRANULARITY_FILTERS}
        />
      </div>
      <DataTable
        loading={usage.loading}
        columns={[
          { key: 'bucket', header: 'Period', render: (b) => formatDate(b.bucket) },
          {
            key: 'metrics',
            header: 'Metrics',
            render: (b) => (
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                {Object.entries(b.metrics || {}).map(([metric, qty]) => (
                  <Badge key={metric} tone="teal">
                    {metric}: {qty}
                  </Badge>
                ))}
              </div>
            ),
          },
        ]}
        rows={usage.data?.buckets || []}
        rowKey={(b) => b.bucket}
        emptyTitle="No usage recorded"
        emptyDescription="Usage records appear here once metrics are aggregated."
      />
      {usage.error && <p style={{ color: 'var(--hf-danger)', marginTop: 10 }}>{usage.error}</p>}
    </Modal>
  )
}

/* ---------------------------------------------------------------------------
 * Plans / change plan
 * ------------------------------------------------------------------------ */

export function PlansPage() {
  const navigate = useNavigate()
  const { toast } = useToast()
  const [search, setSearch] = useState('')
  const [changePlan, setChangePlan] = useState<{
    plan: Plan
    preview: PlanChangePreview | null
  } | null>(null)
  const [previewLoading, setPreviewLoading] = useState(false)
  const [saving, setSaving] = useState(false)

  const plans = useApi(
    () => billingApi.plans.list({ page_size: 100, search: search || undefined }),
    [search],
    { enabled: true },
  )
  useReloadOnChange(plans.reload, [search])
  const subscriptions = useApi(() => billingApi.subscriptions.list({ page_size: 100 }), [], {
    enabled: true,
  })
  const current: Subscription | undefined = (subscriptions.data?.results || []).find((s) =>
    ['trialing', 'active', 'past_due'].includes(s.status),
  )

  async function openChangeModal(plan: Plan) {
    if (!current) {
      setChangePlan({ plan, preview: null })
      return
    }
    setPreviewLoading(true)
    try {
      const preview = await billingApi.subscriptions.previewChange(current.id, { plan: plan.id })
      setChangePlan({ plan, preview })
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Preview failed', 'error')
    } finally {
      setPreviewLoading(false)
    }
  }

  async function confirmChange() {
    if (!changePlan) return
    setSaving(true)
    try {
      if (current) {
        await billingApi.subscriptions.changePlan(current.id, {
          plan: changePlan.plan.id,
          immediate: true,
        })
        toast('Plan updated', 'success')
      } else {
        await billingApi.subscriptions.create({ plan: changePlan.plan.id, seats: 1 })
        toast('Subscribed', 'success')
      }
      setChangePlan(null)
      navigate('/app/billing')
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Change failed', 'error')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="hf-page">
      <PageHeader
        title="Plans"
        subtitle="Choose the plan that fits your hiring volume. Switching plans prorates the difference."
        actions={
          <Button variant="outline" onClick={() => navigate('/app/billing')}>
            Back to billing
          </Button>
        }
      />

      <Card padding="1rem">
        <FilterBar
          search={search}
          onSearchChange={setSearch}
          searchPlaceholder="Search plans…"
          onClear={() => setSearch('')}
        />
      </Card>

      {plans.error && (
        <Card>
          <p style={{ color: 'var(--hf-danger)' }}>{plans.error}</p>
        </Card>
      )}

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
          gap: 14,
        }}
      >
        {(plans.data?.results || []).map((p) => {
          const isCurrent = current?.plan === p.id
          return (
            <Card key={p.id}>
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'flex-start',
                  gap: 8,
                }}
              >
                <strong style={{ fontSize: '1.05rem' }}>{p.name}</strong>
                {p.is_default && <Badge tone="info">Default</Badge>}
              </div>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: 6, margin: '10px 0 4px' }}>
                <span style={{ fontFamily: 'var(--hf-font-display)', fontSize: '1.6rem', fontWeight: 700 }}>
                  {formatCurrency(p.price_per_month, p.currency)}
                </span>
                <span className="hf-muted" style={{ fontSize: '0.8rem' }}>
                  / month
                </span>
              </div>
              <Badge tone="neutral">{titleCase(p.billing_cycle)} billing</Badge>
              {p.description && (
                <p className="hf-muted" style={{ fontSize: '0.82rem', margin: '10px 0' }}>
                  {p.description}
                </p>
              )}
              {(p.features || []).length > 0 && (
                <ul style={{ margin: '10px 0', paddingLeft: 18, display: 'grid', gap: 6, fontSize: '0.85rem' }}>
                  {p.features.slice(0, 8).map((f) => (
                    <li key={f}>{f}</li>
                  ))}
                </ul>
              )}
              {Object.keys(p.limits || {}).length > 0 && (
                <p className="hf-subtle" style={{ fontSize: '0.75rem', margin: '8px 0 0' }}>
                  Limits: {Object.entries(p.limits as Record<string, unknown>)
                    .map(([k, v]) => `${k}: ${String(v)}`)
                    .join(' · ')}
                </p>
              )}
              <div style={{ marginTop: 14 }}>
                {isCurrent ? (
                  <Button variant="outline" disabled fullWidth>
                    Current plan
                  </Button>
                ) : current ? (
                  <Button fullWidth onClick={() => void openChangeModal(p)}>
                    Change to this plan
                  </Button>
                ) : (
                  <Button fullWidth onClick={() => void openChangeModal(p)}>
                    Choose this plan
                  </Button>
                )}
              </div>
            </Card>
          )
        })}
      </div>
      {!plans.loading && !plans.data?.results?.length && (
        <EmptyState title="No plans available" description="The plan catalog is empty." />
      )}

      <Modal
        open={Boolean(changePlan)}
        onClose={() => setChangePlan(null)}
        title={current ? 'Change plan' : 'Choose plan'}
        footer={
          <>
            <Button variant="outline" onClick={() => setChangePlan(null)}>
              Cancel
            </Button>
            <Button loading={saving} onClick={() => void confirmChange()}>
              {current ? 'Confirm change' : 'Subscribe'}
            </Button>
          </>
        }
      >
        {previewLoading ? (
          <div style={{ padding: 24, display: 'grid', placeItems: 'center' }}>
            <Spinner label="Previewing change…" />
          </div>
        ) : changePlan ? (
          <div style={{ display: 'grid', gap: 12 }}>
            <p className="hf-muted">
              {current
                ? `Switch from ${current.plan_name} to ${changePlan.plan.name}?`
                : `Subscribe to ${changePlan.plan.name}?`}
            </p>
            {changePlan.preview && (
              <div style={{ display: 'grid', gap: 10, fontSize: '0.88rem' }}>
                <Row
                  label="New plan price"
                  value={formatCurrency(changePlan.preview.new_plan.price_per_month, changePlan.preview.currency)}
                />
                <Row
                  label="Prorated credit"
                  value={formatCurrency(changePlan.preview.prorated_credit, changePlan.preview.currency)}
                />
                <Row
                  label="Prorated charge"
                  value={formatCurrency(changePlan.preview.prorated_charge, changePlan.preview.currency)}
                />
                <Row
                  label="Amount due now"
                  value={formatCurrency(changePlan.preview.prorated_amount_due, changePlan.preview.currency)}
                />
                <Row label="Effective" value={formatDate(changePlan.preview.effective_date)} />
                <Row label="Next period ends" value={formatDate(changePlan.preview.next_period_end)} />
              </div>
            )}
          </div>
        ) : null}
      </Modal>
    </div>
  )
}

/* ---------------------------------------------------------------------------
 * Invoices
 * ------------------------------------------------------------------------ */

export function InvoicesPage() {
  const { toast } = useToast()
  const [tab, setTab] = useState('invoices')
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('')
  const [acting, setActing] = useState<string | null>(null)
  const [paying, setPaying] = useState<Invoice | null>(null)
  const [viewing, setViewing] = useState<Invoice | null>(null)

  useEffect(() => {
    setPage(1)
  }, [tab])

  const invoices = useApi(
    () =>
      billingApi.invoices.list({
        page,
        page_size: 10,
        search: search || undefined,
        status: status || undefined,
      }),
    [page, search, status],
    { enabled: tab === 'invoices' },
  )
  useReloadOnChange(invoices.reload, [page, search, status])
  const transactions = useApi(
    () => billingApi.paymentTransactions.list({ page, page_size: 10, search: search || undefined }),
    [page, search],
    { enabled: tab === 'transactions' },
  )
  useReloadOnChange(transactions.reload, [page, search])

  async function download(inv: Invoice) {
    setActing(inv.id)
    try {
      const blob = await billingApi.invoices.download(inv.id)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${inv.invoice_number}.csv`
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(url)
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Download failed', 'error')
    } finally {
      setActing(null)
    }
  }

  return (
    <div className="hf-page">
      <PageHeader
        title="Invoices"
        subtitle="Bills issued to your organization and the payments against them."
      />

      <Tabs
        value={tab}
        onChange={setTab}
        items={[
          { id: 'invoices', label: 'Invoices', count: invoices.data?.count },
          { id: 'transactions', label: 'Transactions', count: transactions.data?.count },
        ]}
      />

      {tab === 'invoices' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <Card padding="1rem">
            <FilterBar
              search={search}
              onSearchChange={(v) => {
                setPage(1)
                setSearch(v)
              }}
              searchPlaceholder="Search invoices…"
              filters={[
                {
                  key: 'status',
                  label: 'Status',
                  value: status,
                  onChange: (v) => {
                    setPage(1)
                    setStatus(invoiceStatusToApi[v] ?? '')
                  },
                  options: INVOICE_STATUS_FILTERS,
                },
              ]}
              onClear={() => {
                setSearch('')
                setStatus('')
                setPage(1)
              }}
            />
          </Card>
          {invoices.error && (
            <Card>
              <p style={{ color: 'var(--hf-danger)' }}>{invoices.error}</p>
            </Card>
          )}
          <Card padding={0}>
            <DataTable
              loading={invoices.loading}
              columns={[
                { key: 'number', header: 'Invoice', render: (i) => <strong>{i.invoice_number}</strong> },
                { key: 'plan', header: 'Plan', render: (i) => i.subscription_plan || '—' },
                {
                  key: 'status',
                  header: 'Status',
                  render: (i) => <Badge tone={invoiceTone(i.status)}>{titleCase(i.status)}</Badge>,
                },
                {
                  key: 'total',
                  header: 'Total',
                  render: (i) => formatCurrency(i.total, i.currency),
                },
                { key: 'issued', header: 'Issued', render: (i) => formatDate(i.issued_at) },
                { key: 'due', header: 'Due', render: (i) => formatDate(i.due_at) },
                {
                  key: 'actions',
                  header: 'Actions',
                  render: (i) => (
                    <div style={{ display: 'flex', gap: 6 }} onClick={(e) => e.stopPropagation()}>
                      {['open', 'uncollectible'].includes(i.status) && (
                        <Button size="sm" variant="outline" onClick={() => setPaying(i)}>
                          Pay
                        </Button>
                      )}
                      <Button
                        size="sm"
                        variant="outline"
                        loading={acting === i.id}
                        disabled={acting !== null}
                        onClick={() => void download(i)}
                      >
                        <Download size={13} />
                      </Button>
                      <Button size="sm" variant="ghost" onClick={() => setViewing(i)}>
                        View
                      </Button>
                    </div>
                  ),
                },
              ]}
              rows={invoices.data?.results || []}
              rowKey={(i) => i.id}
              emptyTitle="No invoices"
              emptyDescription="Invoices appear here once issued."
            />
            {invoices.data && (
              <Pagination page={page} pageSize={10} total={invoices.data.count} onChange={setPage} />
            )}
          </Card>
        </div>
      )}

      {tab === 'transactions' && (
        <Card padding={0}>
          <DataTable
            loading={transactions.loading}
            columns={[
              {
                key: 'status',
                header: 'Status',
                render: (t) => <Badge tone={transactionTone(t.status)}>{titleCase(t.status)}</Badge>,
              },
              { key: 'number', header: 'Invoice', render: (t) => t.invoice_number || '—' },
              {
                key: 'amount',
                header: 'Amount',
                render: (t) => formatCurrency(t.amount, t.currency),
              },
              { key: 'provider', header: 'Provider', render: (t) => t.provider || '—' },
              { key: 'ref', header: 'Reference', render: (t) => t.provider_ref || '—' },
              { key: 'created', header: 'Date', render: (t) => formatDateTime(t.created_at) },
            ]}
            rows={transactions.data?.results || []}
            rowKey={(t) => t.id}
            emptyTitle="No transactions"
            emptyDescription="Payments will appear here as they are recorded."
          />
          {transactions.data && (
            <Pagination page={page} pageSize={10} total={transactions.data.count} onChange={setPage} />
          )}
        </Card>
      )}

      <PayInvoiceModal
        invoice={paying && 'id' in paying ? paying : null}
        onClose={() => setPaying(null)}
        onPaid={() => invoices.reload()}
      />
      <InvoiceDetailModal invoice={viewing} onClose={() => setViewing(null)} />
    </div>
  )
}

function PayInvoiceModal({
  invoice,
  onClose,
  onPaid,
}: {
  invoice: Invoice | null
  onClose: () => void
  onPaid: () => void
}) {
  const { toast } = useToast()
  const [provider, setProvider] = useState('mock')
  const [providerRef, setProviderRef] = useState('')
  const [amount, setAmount] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (invoice) {
      setProvider('mock')
      setProviderRef('')
      setAmount('')
    }
  }, [invoice])

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    if (!invoice) return
    setSaving(true)
    try {
      const res = await billingApi.invoices.pay(invoice.id, {
        provider: provider || 'mock',
        provider_ref: providerRef || undefined,
        amount: amount ? Number(amount) : null,
      })
      toast(
        `Payment ${res.transaction.status} · ${formatCurrency(res.transaction.amount, res.transaction.currency)}`,
        res.transaction.status === 'succeeded' ? 'success' : 'warning',
      )
      onPaid()
      onClose()
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Payment failed', 'error')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal open={Boolean(invoice)} onClose={onClose} title="Pay invoice">
      {invoice && (
        <form onSubmit={onSubmit} style={{ display: 'grid', gap: 12 }}>
          <p className="hf-muted">
            Paying invoice <strong>{invoice.invoice_number}</strong> for{' '}
            {formatCurrency(invoice.total, invoice.currency)}.
          </p>
          <Input label="Provider" value={provider} onChange={(e) => setProvider(e.target.value)} placeholder="mock" />
          <Input
            label="Provider reference (optional)"
            value={providerRef}
            onChange={(e) => setProviderRef(e.target.value)}
          />
          <Input
            label="Amount (optional, defaults to total)"
            type="number"
            step="0.01"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
          />
          <Button type="submit" loading={saving}>
            Pay now
          </Button>
        </form>
      )}
    </Modal>
  )
}

function InvoiceDetailModal({ invoice, onClose }: { invoice: Invoice | null; onClose: () => void }) {
  return (
    <Modal open={Boolean(invoice)} onClose={onClose} title={invoice ? `Invoice ${invoice.invoice_number}` : ''} width={600}>
      {invoice && (
        <div style={{ display: 'grid', gap: 12 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Badge tone={invoiceTone(invoice.status)}>{titleCase(invoice.status)}</Badge>
            <span className="hf-muted" style={{ fontSize: '0.8rem' }}>
              Issued {formatDate(invoice.issued_at)} · Due {formatDate(invoice.due_at)}
            </span>
          </div>
          {(invoice.line_items || []).length ? (
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
              <thead>
                <tr>
                  <th style={{ textAlign: 'left', padding: '6px 8px', borderBottom: '1px solid var(--hf-border)' }}>
                    Description
                  </th>
                  <th style={{ textAlign: 'right', padding: '6px 8px', borderBottom: '1px solid var(--hf-border)' }}>
                    Qty
                  </th>
                  <th style={{ textAlign: 'right', padding: '6px 8px', borderBottom: '1px solid var(--hf-border)' }}>
                    Unit price
                  </th>
                  <th style={{ textAlign: 'right', padding: '6px 8px', borderBottom: '1px solid var(--hf-border)' }}>
                    Amount
                  </th>
                </tr>
              </thead>
              <tbody>
                {(invoice.line_items || []).map((li, idx) => (
                  <tr key={idx}>
                    <td style={{ padding: '6px 8px' }}>{li.description || '—'}</td>
                    <td style={{ padding: '6px 8px', textAlign: 'right' }}>{String(li.quantity ?? '')}</td>
                    <td style={{ padding: '6px 8px', textAlign: 'right' }}>
                      {formatCurrency(li.unit_price, invoice.currency)}
                    </td>
                    <td style={{ padding: '6px 8px', textAlign: 'right' }}>
                      {formatCurrency(li.amount, invoice.currency)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="hf-muted">No line items.</p>
          )}
          <div style={{ display: 'grid', gap: 8, fontSize: '0.88rem', marginTop: 4 }}>
            <Row label="Subtotal" value={formatCurrency(invoice.subtotal, invoice.currency)} />
            <Row label="Tax" value={formatCurrency(invoice.tax, invoice.currency)} />
            <Row label="Total" value={formatCurrency(invoice.total, invoice.currency)} />
            <Row label="Paid" value={formatDate(invoice.paid_at)} />
          </div>
        </div>
      )}
    </Modal>
  )
}

/* ---------------------------------------------------------------------------
 * Payment methods
 * ------------------------------------------------------------------------ */

export function PaymentMethodsPage() {
  const { toast } = useToast()
  const [page, setPage] = useState(1)
  const [acting, setActing] = useState<string | null>(null)
  const [addOpen, setAddOpen] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState<PaymentMethod | null>(null)

  const methods = useApi(() => billingApi.paymentMethods.list({ page, page_size: 10 }), [page], {
    enabled: true,
  })
  useReloadOnChange(methods.reload, [page])

  async function setDefault(m: PaymentMethod) {
    setActing(m.id)
    try {
      await billingApi.paymentMethods.setDefault(m.id)
      toast('Default payment method updated', 'success')
      methods.reload()
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Failed', 'error')
    } finally {
      setActing(null)
    }
  }

  return (
    <div className="hf-page">
      <PageHeader
        title="Payment methods"
        subtitle="Cards and bank accounts used to pay invoices."
        actions={
          <Button onClick={() => setAddOpen(true)}>
            <Plus size={16} />
            Add payment method
          </Button>
        }
      />

      {methods.error && (
        <Card>
          <p style={{ color: 'var(--hf-danger)' }}>{methods.error}</p>
        </Card>
      )}

      <Card padding={0}>
        <DataTable
          loading={methods.loading}
          columns={[
            { key: 'type', header: 'Type', render: (m) => <Badge tone="info">{titleCase(m.type)}</Badge> },
            {
              key: 'method',
              header: 'Method',
              render: (m) => (
                <span style={{ fontWeight: 600 }}>
                  {m.brand || titleCase(m.type)} •••• {m.last4 || '—'}
                </span>
              ),
            },
            {
              key: 'exp',
              header: 'Expires',
              render: (m) =>
                m.exp_month && m.exp_year ? `${String(m.exp_month).padStart(2, '0')}/${m.exp_year}` : '—',
            },
            {
              key: 'default',
              header: 'Default',
              render: (m) => (m.is_default ? <Badge tone="success">Default</Badge> : '—'),
            },
            {
              key: 'actions',
              header: 'Actions',
              render: (m) => (
                <div style={{ display: 'flex', gap: 6 }} onClick={(e) => e.stopPropagation()}>
                  {!m.is_default && (
                    <Button
                      size="sm"
                      variant="outline"
                      loading={acting === m.id}
                      disabled={acting !== null}
                      onClick={() => void setDefault(m)}
                    >
                      Set default
                    </Button>
                  )}
                  <Button size="sm" variant="danger" onClick={() => setConfirmDelete(m)}>
                    <Trash2 size={13} />
                  </Button>
                </div>
              ),
            },
          ]}
          rows={methods.data?.results || []}
          rowKey={(m) => m.id}
          emptyTitle="No payment methods"
          emptyDescription="Add a card or bank account to pay invoices."
        />
        {methods.data && (
          <Pagination page={page} pageSize={10} total={methods.data.count} onChange={setPage} />
        )}
      </Card>

      <AddPaymentMethodModal
        open={addOpen}
        onClose={() => setAddOpen(false)}
        onAdded={methods.reload}
      />
      <ConfirmDialog
        open={Boolean(confirmDelete)}
        title="Remove payment method"
        message={`Remove ${confirmDelete?.brand || confirmDelete?.type || 'this method'} •••• ${confirmDelete?.last4 || '—'}?`}
        confirmLabel="Remove"
        danger
        loading={acting === 'delete'}
        onCancel={() => setConfirmDelete(null)}
        onConfirm={() => {
          if (!confirmDelete) return
          setActing('delete')
          billingApi.paymentMethods
            .remove(confirmDelete.id)
            .then(() => {
              toast('Payment method removed', 'success')
              methods.reload()
              setConfirmDelete(null)
            })
            .catch((err) => toast(err instanceof ApiError ? err.message : 'Remove failed', 'error'))
            .finally(() => setActing(null))
        }}
      />
    </div>
  )
}

function AddPaymentMethodModal({
  open,
  onClose,
  onAdded,
}: {
  open: boolean
  onClose: () => void
  onAdded: () => void
}) {
  const { toast } = useToast()
  const [typeName, setTypeName] = useState('Card')
  const [brand, setBrand] = useState('')
  const [last4, setLast4] = useState('')
  const [expMonth, setExpMonth] = useState('')
  const [expYear, setExpYear] = useState('')
  const [isDefault, setIsDefault] = useState(false)
  const [saving, setSaving] = useState(false)

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    if (!last4.trim() || last4.trim().length !== 4) {
      toast('Last 4 digits are required', 'error')
      return
    }
    setSaving(true)
    try {
      await billingApi.paymentMethods.create({
        type: (paymentTypeToApi[typeName] ?? 'card') as 'card' | 'bank',
        brand: brand.trim() || undefined,
        last4: last4.trim(),
        exp_month: expMonth ? Number(expMonth) : null,
        exp_year: expYear ? Number(expYear) : null,
        is_default: isDefault,
      })
      toast('Payment method added', 'success')
      onAdded()
      onClose()
      setBrand('')
      setLast4('')
      setExpMonth('')
      setExpYear('')
      setIsDefault(false)
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Add failed', 'error')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal open={open} onClose={onClose} title="Add payment method">
      <form onSubmit={onSubmit} style={{ display: 'grid', gap: 12 }}>
        <Select
          label="Type"
          value={typeName}
          onChange={(e) => setTypeName(e.target.value)}
          options={PAYMENT_TYPE_FILTERS}
        />
        <Input label="Brand" value={brand} onChange={(e) => setBrand(e.target.value)} placeholder="Visa" />
        <Input label="Last 4 digits" required maxLength={4} value={last4} onChange={(e) => setLast4(e.target.value)} />
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          <Input
            label="Expiry month"
            type="number"
            min={1}
            max={12}
            value={expMonth}
            onChange={(e) => setExpMonth(e.target.value)}
            placeholder="12"
          />
          <Input
            label="Expiry year"
            type="number"
            min={2026}
            value={expYear}
            onChange={(e) => setExpYear(e.target.value)}
            placeholder="2030"
          />
        </div>
        <label style={{ display: 'flex', gap: 8, alignItems: 'center', fontSize: '0.88rem' }}>
          <input type="checkbox" checked={isDefault} onChange={(e) => setIsDefault(e.target.checked)} />
          Set as default
        </label>
        <Button type="submit" loading={saving}>
          Add payment method
        </Button>
      </form>
    </Modal>
  )
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}>
      <dt className="hf-muted">{label}</dt>
      <dd style={{ margin: 0, fontWeight: 600, textAlign: 'right' }}>{value}</dd>
    </div>
  )
}
