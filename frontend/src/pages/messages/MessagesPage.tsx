import { useState } from 'react'
import { commsApi } from '../../api/comms'
import { useApi } from '../../hooks/useApi'
import { PageHeader } from '../../components/layout/PageHeader'
import { Badge, Button, Card, EmptyState, Spinner, Textarea, useToast } from '../../components/ui'
import { formatRelative } from '../../utils/format'
import { ApiError } from '../../api/http'

export function MessagesPage() {
  const threads = useApi(() => commsApi.listThreads({ page_size: 50 }), [])
  const [activeId, setActiveId] = useState<string | null>(null)
  const messages = useApi(
    () => commsApi.listMessages(activeId!),
    [activeId],
    { enabled: Boolean(activeId) },
  )
  const [body, setBody] = useState('')
  const [sending, setSending] = useState(false)
  const { toast } = useToast()

  async function send() {
    if (!body.trim()) return
    setSending(true)
    try {
      await commsApi.sendMessage(activeId, body.trim())
      setBody('')
      messages.reload()
      threads.reload()
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Send failed', 'error')
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="hf-page">
      <PageHeader title="Messages" subtitle="Candidate and hiring-team conversations." />
      {threads.error && (
        <Card>
          <p className="hf-muted">{threads.error}</p>
        </Card>
      )}
      <div style={{ display: 'grid', gridTemplateColumns: '300px 1fr', gap: 12, minHeight: 480 }}>
        <Card padding={0}>
          {threads.loading ? (
            <div style={{ padding: 24, display: 'grid', placeItems: 'center' }}>
              <Spinner />
            </div>
          ) : (threads.data?.results || []).length ? (
            (threads.data?.results || []).map((t) => (
              <button
                key={t.id}
                onClick={() => setActiveId(t.id)}
                style={{
                  width: '100%',
                  textAlign: 'left',
                  border: 'none',
                  borderBottom: '1px solid var(--hf-border)',
                  background: activeId === t.id ? 'var(--hf-primary-soft)' : 'transparent',
                  padding: '0.85rem 1rem',
                  cursor: 'pointer',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
                  <strong style={{ fontSize: '0.88rem' }}>{t.subject}</strong>
                  {t.unread_count > 0 && <Badge tone="info">{t.unread_count}</Badge>}
                </div>
                <div className="hf-subtle" style={{ fontSize: '0.75rem', marginTop: 4 }}>
                  {formatRelative(t.last_message_at)} · {t.last_message || '—'}
                </div>
              </button>
            ))
          ) : (
            <EmptyState title="No threads" description="Messages will appear here." />
          )}
        </Card>
        <Card title={activeId ? 'Conversation' : 'Select a thread'} style={{ display: 'flex', flexDirection: 'column' }}>
          {!activeId ? (
            <p className="hf-muted">Choose a conversation from the left.</p>
          ) : (
            <>
              <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 10, minHeight: 280, marginBottom: 16 }}>
                {messages.loading && <Spinner />}
                {(messages.data?.results || []).map((m) => (
                  <div key={m.id} style={{ padding: 10, borderRadius: 10, background: 'var(--hf-primary-soft)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, marginBottom: 4 }}>
                      <strong style={{ fontSize: '0.8rem' }}>{m.sender_name}</strong>
                      <span className="hf-subtle" style={{ fontSize: '0.72rem' }}>
                        {formatRelative(m.created_at)}
                      </span>
                    </div>
                    <p style={{ fontSize: '0.88rem', whiteSpace: 'pre-wrap' }}>{m.body}</p>
                  </div>
                ))}
                {messages.error && <p className="hf-muted">{messages.error}</p>}
              </div>
              <div style={{ display: 'grid', gap: 8 }}>
                <Textarea value={body} onChange={(e) => setBody(e.target.value)} placeholder="Write a message…" />
                <Button onClick={() => void send()} loading={sending} disabled={!body.trim()}>
                  Send
                </Button>
              </div>
            </>
          )}
        </Card>
      </div>
    </div>
  )
}
