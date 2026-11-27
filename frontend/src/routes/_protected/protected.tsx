import { Link, createFileRoute } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'

import { AppShell } from '#/components/app-shell'
import { EmptyState, ErrorState, LoadingState } from '#/components/states'
import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import {
  healthQuery,
  opsQueueQuery,
  opsTasksQuery,
  overviewQuery,
  revenueAdviceQuery,
  revenueSummaryQuery,
  statsQuery,
} from '#/lib/queries'

type Health = {
  health: { database: { ok: boolean }; rabbitmq: { ok: boolean } }
}
type Queue = { counts: Record<string, number>; dead_letter_queue: string }
type Task = { task_id: string; status: string; attempts: number }
type Overview = { clips: { total: number; average_score: number } }
type Stats = { total: number; peak: number }

const ProtectedPage = () => {
  const health = useQuery(healthQuery())
  const queue = useQuery(opsQueueQuery())
  const tasks = useQuery(opsTasksQuery())
  const overview = useQuery(overviewQuery())
  const stats = useQuery(statsQuery())
  const revenue = useQuery(revenueSummaryQuery())
  const advice = useQuery(revenueAdviceQuery())

  const healthData = health.data as Health | undefined
  const queueData = queue.data as Queue | undefined
  const taskData = tasks.data as Task[] | undefined
  const overviewData = overview.data as Overview | undefined
  const statsData = stats.data as Stats | undefined
  const revenueData = revenue.data as
    { total_available: number; currency: string } | undefined

  const brokerOk = healthData?.health.rabbitmq.ok ?? false
  const hasProgress =
    taskData?.some((task) => task.status === 'PROGRESS') ?? false
  const action = !brokerOk
    ? { label: 'Buka antrean', to: '/backend' as const }
    : hasProgress
      ? { label: 'Lihat task', to: '/backend' as const }
      : { label: 'Buat brief baru', to: '/shorts' as const }

  const isLoading =
    health.isLoading || queue.isLoading || tasks.isLoading || overview.isLoading
  const error = health.error ?? queue.error ?? tasks.error ?? overview.error

  return (
    <AppShell>
      <h1 className="neon-text display-title rise-in text-4xl">Ruang kerja</h1>
      <p className="mt-1 text-[15px] leading-relaxed text-muted-foreground">
        Status antrean dan pekerjaan berikutnya untuk pemilik studio.
      </p>

      {isLoading ? (
        <div className="mt-6">
          <LoadingState label="Memuat status kapal dari backend." />
        </div>
      ) : null}
      {error ? (
        <div className="mt-6">
          <ErrorState
            message={error.message}
            onRetry={() => {
              void health.refetch()
              void queue.refetch()
              void tasks.refetch()
              void overview.refetch()
            }}
          />
        </div>
      ) : null}

      {!isLoading && !error ? (
        <div className="mt-6 space-y-6">
          <section className="neon-panel rise-in rounded-xl p-4">
            <div className="flex flex-wrap items-center gap-2">
              <Badge
                variant={
                  healthData?.health.database.ok ? 'secondary' : 'destructive'
                }
              >
                Database {healthData?.health.database.ok ? 'aktif' : 'mati'}
              </Badge>
              <Badge variant={brokerOk ? 'secondary' : 'destructive'}>
                RabbitMQ {brokerOk ? 'aktif' : 'mati'}
              </Badge>
              <Badge variant="outline">
                DLQ {queueData?.dead_letter_queue ?? '-'}
              </Badge>
            </div>
            <Button
              asChild
              type="button"
              variant="outline"
              className="mt-3 min-h-11"
            >
              <Link to={action.to}>{action.label}</Link>
            </Button>
          </section>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
            <section className="neon-panel rise-in rounded-xl p-4 lg:col-span-2">
              <h2 className="text-lg font-semibold">Task terbaru</h2>
              {taskData?.length ? (
                <ul className="mt-3 space-y-2 text-sm">
                  {taskData.slice(0, 8).map((task) => (
                    <li
                      key={task.task_id}
                      className="flex flex-wrap items-center gap-2"
                    >
                      <span className="min-w-0 flex-1 truncate">
                        {task.task_id}
                      </span>
                      <Badge variant="outline">{task.status}</Badge>
                      <Badge variant="outline">attempt {task.attempts}</Badge>
                    </li>
                  ))}
                </ul>
              ) : (
                <div className="mt-3">
                  <EmptyState message="Belum ada task. Buat brief di Shorts." />
                </div>
              )}
            </section>

            <section className="neon-panel rise-in rounded-xl p-4">
              <h2 className="text-lg font-semibold">Statistik</h2>
              <div className="mt-3 flex flex-wrap gap-2">
                <Badge variant="secondary">
                  Clip {overviewData?.clips.total ?? 0}
                </Badge>
                <Badge variant="secondary">
                  Rata-rata{' '}
                  {(overviewData?.clips.average_score ?? 0).toFixed(2)}
                </Badge>
                <Badge variant="secondary">Puncak {statsData?.peak ?? 0}</Badge>
              </div>
            </section>
          </div>

          <section className="neon-panel rise-in rounded-xl p-4">
            <h2 className="text-lg font-semibold">Pendapatan</h2>
            <p className="mt-2 text-sm text-[var(--ink-muted)]">
              Total {revenueData?.total_available ?? 0}{' '}
              {revenueData?.currency ?? ''}
            </p>
            <Button
              type="button"
              variant="outline"
              className="mt-3 min-h-11"
              disabled={advice.isFetching}
              onClick={() => void advice.refetch()}
            >
              {advice.isFetching ? 'Meminta saran…' : 'Ambil saran'}
            </Button>
            {advice.data ? (
              <pre className="mt-3 max-h-64 overflow-auto whitespace-pre-wrap break-words rounded-md border border-[var(--line)] p-3 text-xs">
                {JSON.stringify(advice.data, null, 2)}
              </pre>
            ) : null}
          </section>

          <section className="neon-panel rise-in rounded-xl p-4">
            <h2 className="text-lg font-semibold">Jejak kerja</h2>
            <div className="mt-3 flex flex-wrap gap-2">
              <Button
                asChild
                type="button"
                variant="outline"
                className="min-h-11"
              >
                <Link to="/backend">Semua data backend</Link>
              </Button>
              <Button
                asChild
                type="button"
                variant="ghost"
                className="min-h-11"
              >
                <Link to="/shorts">Buat brief</Link>
              </Button>
            </div>
          </section>
        </div>
      ) : null}
    </AppShell>
  )
}

export const Route = createFileRoute('/_protected/protected')({
  component: ProtectedPage,
})
