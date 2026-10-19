import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import {
  DndContext,
  DragOverlay,
  PointerSensor,
  closestCorners,
  useSensor,
  useSensors,
  type DragEndEvent,
  type DragStartEvent,
} from '@dnd-kit/core'
import { SortableContext, useSortable, verticalListSortingStrategy } from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { applicationsApi } from '../../api/pipelines'
import { jobsApi } from '../../api/jobs'
import { useApi } from '../../hooks/useApi'
import { PageHeader } from '../../components/layout/PageHeader'
import { Avatar, Badge, Card, EmptyState, Select, Spinner, useToast } from '../../components/ui'
import type { BoardApplication, BoardColumn } from '../../api/types'
import { ApiError } from '../../api/http'
import { formatRelative } from '../../utils/format'

export function PipelineBoardPage() {
  const [params, setParams] = useSearchParams()
  const jobId = params.get('job_id') || ''
  const navigate = useNavigate()
  const { toast } = useToast()
  const jobs = useApi(() => jobsApi.list({ page_size: 100, status: 'published' }), [])
  const board = useApi(
    () => applicationsApi.board(jobId ? { job: jobId } : undefined),
    [jobId],
  )
  const [columns, setColumns] = useState<BoardColumn[]>([])
  const [activeCard, setActiveCard] = useState<BoardApplication | null>(null)

  useEffect(() => {
    if (!board.data) return
    const cols = Array.isArray(board.data) ? board.data : board.data.columns || []
    setColumns(cols)
  }, [board.data])

  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 6 }))

  const stageIds = useMemo(() => columns.map((c) => c.stage.id), [columns])

  function findContainer(id: string) {
    if (stageIds.includes(id)) return id
    return columns.find((c) => c.applications.some((a) => a.id === id))?.stage.id
  }

  async function onDragEnd(event: DragEndEvent) {
    const { active, over } = event
    setActiveCard(null)
    if (!over) return
    const activeId = String(active.id)
    const overId = String(over.id)
    const fromStage = findContainer(activeId)
    const toStage = findContainer(overId)
    if (!fromStage || !toStage || fromStage === toStage) return

    const moving = columns.flatMap((c) => c.applications).find((a) => a.id === activeId)
    if (!moving) return

    setColumns((prev) =>
      prev.map((col) => {
        if (col.stage.id === fromStage) {
          return { ...col, applications: col.applications.filter((a) => a.id !== activeId) }
        }
        if (col.stage.id === toStage) {
          return { ...col, applications: [moving, ...col.applications] }
        }
        return col
      }),
    )

    try {
      await applicationsApi.move(activeId, { stage_id: toStage })
      toast('Moved candidate', 'success')
    } catch (err) {
      toast(err instanceof ApiError ? err.message : 'Move failed', 'error')
      board.reload()
    }
  }

  function onDragStart(event: DragStartEvent) {
    const id = String(event.active.id)
    const card = columns.flatMap((c) => c.applications).find((a) => a.id === id) || null
    setActiveCard(card)
  }

  return (
    <div className="hf-page">
      <PageHeader
        title="Pipeline"
        subtitle="Drag candidates across stages to keep hiring moving."
        actions={
          <div style={{ minWidth: 240 }}>
            <Select
              label="Job filter"
              value={jobId}
              onChange={(e) => {
                const v = e.target.value
                if (!v) setParams({ job: v })
                else setParams({})
              }}
              placeholder="All jobs"
              options={(jobs.data?.results || []).map((j) => ({ value: j.id, label: j.title }))}
            />
          </div>
        }
      />

      {board.loading ? (
        <div style={{ padding: 48, display: 'grid', placeItems: 'center' }}>
          <Spinner label="Loading board…" />
        </div>
      ) : board.error ? (
        <Card>
          <EmptyState
            title="Couldn’t load pipeline"
            description={board.error}
            actionLabel="Retry"
            onAction={board.reload}
          />
        </Card>
      ) : !columns.length ? (
        <Card>
          <EmptyState
            title="No pipeline stages"
            description="Seed a default pipeline template or publish a job with a pipeline."
          />
        </Card>
      ) : (
        <DndContext
          sensors={sensors}
          collisionDetection={closestCorners}
          onDragStart={onDragStart}
          onDragEnd={(e) => void onDragEnd(e)}
        >
          <div
            style={{
              display: 'grid',
              gridAutoFlow: 'column',
              gridAutoColumns: 'minmax(260px, 1fr)',
              gap: 12,
              overflowX: 'auto',
              paddingBottom: 8,
              minHeight: 480,
            }}
          >
            {columns.map((col) => (
              <StageColumn
                key={col.stage.id}
                column={col}
                onOpen={(id) => navigate(`/app/pipeline/applications/${id}`)}
              />
            ))}
          </div>
          <DragOverlay>
            {activeCard ? <ApplicationCard app={activeCard} dragging /> : null}
          </DragOverlay>
        </DndContext>
      )}
    </div>
  )
}

function StageColumn({
  column,
  onOpen,
}: {
  column: BoardColumn
  onOpen: (id: string) => void
}) {
  const ids = column.applications.map((a) => a.id)
  return (
    <div
      className="hf-panel"
      style={{
        padding: 10,
        background: 'rgba(255,255,255,0.55)',
        minHeight: 420,
        display: 'flex',
        flexDirection: 'column',
        gap: 8,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '4px 6px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span
            style={{
              width: 10,
              height: 10,
              borderRadius: '50%',
              background: column.stage.color || 'var(--hf-teal-600)',
            }}
          />
          <strong style={{ fontSize: '0.88rem' }}>{column.stage.name}</strong>
        </div>
        <Badge tone="neutral">{column.applications.length}</Badge>
      </div>
      <SortableContext items={ids} strategy={verticalListSortingStrategy} id={column.stage.id}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8, flex: 1 }}>
          {column.applications.map((app) => (
            <SortableCard key={app.id} app={app} onOpen={() => onOpen(app.id)} />
          ))}
        </div>
      </SortableContext>
    </div>
  )
}

function SortableCard({ app, onOpen }: { app: BoardApplication; onOpen: () => void }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: app.id,
  })
  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.4 : 1,
  }
  return (
    <div ref={setNodeRef} style={style} {...attributes} {...listeners}>
      <ApplicationCard app={app} onOpen={onOpen} />
    </div>
  )
}

function ApplicationCard({
  app,
  onOpen,
  dragging,
}: {
  app: BoardApplication
  onOpen?: () => void
  dragging?: boolean
}) {
  return (
    <button
      type="button"
      onClick={onOpen}
      style={{
        width: '100%',
        textAlign: 'left',
        border: '1px solid var(--hf-border)',
        borderRadius: 12,
        padding: 12,
        background: 'var(--hf-bg-elevated)',
        boxShadow: dragging ? 'var(--hf-shadow)' : 'var(--hf-shadow-sm)',
        cursor: 'grab',
        display: 'flex',
        flexDirection: 'column',
        gap: 8,
      }}
    >
      <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
        <Avatar name={app.candidate_name} size={30} />
        <div style={{ minWidth: 0 }}>
          <div style={{ fontWeight: 650, fontSize: '0.88rem', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
            {app.candidate_name}
          </div>
          <div className="hf-subtle" style={{ fontSize: '0.72rem' }}>
            {formatRelative(app.applied_at)}
          </div>
        </div>
      </div>
      {app.headline && (
        <div className="hf-muted" style={{ fontSize: '0.78rem', lineHeight: 1.35 }}>
          {app.headline}
        </div>
      )}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        {app.relevance_score != null ? (
          <Badge tone="teal">{Math.round(app.relevance_score)}%</Badge>
        ) : (
          <span />
        )}
        {app.knockout_failed && <Badge tone="danger">Knockout</Badge>}
      </div>
    </button>
  )
}
