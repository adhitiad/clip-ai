import { createFileRoute } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'

import { AppShell } from '#/components/app-shell'
import { EmptyState, ErrorState, LoadingState } from '#/components/states'
import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import {
  healthQuery,
  overviewQuery,
  revenueAdviceQuery,
  revenueSummaryQuery,
  statsQuery,
} from '#/lib/queries'
import type {
  Health,
  Overview,
  RevenueAdvice,
  RevenueSummary,
  Stats,
} from '#/type/api'

const DashboardPage = () => {
  const overview = useQuery(overviewQuery())
  const stats = useQuery(statsQuery())
  const health = useQuery(healthQuery())
  const revenue = useQuery(revenueSummaryQuery())
  const advice = useQuery(revenueAdviceQuery())

  const data = overview.data as Overview | undefined
  const statData = stats.data as Stats | undefined
  const healthData = health.data as Health | undefined
  const revenueData = revenue.data as RevenueSummary | undefined
  const adviceData = advice.data as RevenueAdvice | undefined

  const isLoading = overview.isLoading || stats.isLoading || health.isLoading
  const error = overview.error ?? stats.error ?? health.error

  return (
    <AppShell>
      <h1 className="neon-text display-title rise-in text-4xl">Dashboard</h1>
      <p className="mt-1 text-[15px] leading-relaxed text-muted-foreground">
        Skor clip, statistik tujuh hari, pendapatan platform, dan status
        database serta RabbitMQ.
      </p>
      {isLoading ? (
        <div className="mt-6">
          <LoadingState />
        </div>
      ) : null}
      {error ? (
        <div className="mt-6">
          <ErrorState
            message={error.message}
            onRetry={() => {
              void overview.refetch()
              void stats.refetch()
              void health.refetch()
            }}
          />
        </div>
      ) : null}
      {!isLoading && !error ? (
        <div className="mt-6 space-y-6">
          <section>
            <h2 className="text-lg font-semibold">Clip</h2>
            {data ? (
              <div className="mt-2 flex flex-wrap items-center gap-3">
                <Badge variant="secondary">Total {data.clips.total}</Badge>
                <Badge variant="secondary">
                  Rata-rata {data.clips.average_score.toFixed(2)}
                </Badge>
                <Badge variant="secondary">Maks {data.clips.max_score}</Badge>
              </div>
            ) : (
              <EmptyState
                message="Ringkasan belum tersedia karena backend tidak mengembalikan data clip."
                action={{
                  label: 'Muat ulang',
                  onClick: () => void overview.refetch(),
                }}
              />
            )}
          </section>
          <section>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h2 className="text-lg font-semibold">Pendapatan platform</h2>
              <Button asChild variant="outline" size="sm">
                <a href="/api/youtube/oauth/start">Hubungkan YouTube</a>
              </Button>
            </div>
            {revenueData ? (
              <div className="mt-2">
                <div className="flex flex-wrap items-center gap-3">
                  <Badge variant="secondary">
                    Total {revenueData.total_available.toFixed(2)}{' '}
                    {revenueData.currency}
                  </Badge>
                  <Badge variant="outline">
                    Periode {revenueData.days} hari
                  </Badge>
                </div>
                <ul
                  className="mt-3 space-y-2"
                  aria-label="Pendapatan per platform"
                >
                  {revenueData.platforms.map((item) => (
                    <li
                      key={item.platform}
                      className="neon-panel rounded-xl p-3 text-sm"
                    >
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-medium">{item.platform}</span>
                        <Badge
                          variant={item.available ? 'secondary' : 'outline'}
                        >
                          {item.available
                            ? `${item.amount ?? 0} ${item.currency ?? ''}`
                            : 'Dilewati'}
                        </Badge>
                      </div>
                      {!item.available ? (
                        <p className="mt-1 text-[13px] text-muted-foreground">
                          {item.note}
                        </p>
                      ) : null}
                    </li>
                  ))}
                </ul>
                <Button
                  type="button"
                  className="shonen-action mt-3"
                  disabled={advice.isFetching}
                  onClick={() => void advice.refetch()}
                >
                  {advice.isFetching ? 'Meminta saran…' : 'Saran AI'}
                </Button>
                {advice.isError ? (
                  <p role="alert" className="mt-2 text-sm text-destructive">
                    {advice.error.message}
                  </p>
                ) : null}
                {adviceData ? (
                  <ul
                    className="mt-3 list-disc space-y-1 pl-5 text-sm"
                    aria-label="Saran peningkatan pendapatan"
                  >
                    {adviceData.recommendations.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                ) : null}
              </div>
            ) : (
              <EmptyState
                message="Ringkasan pendapatan belum tersedia dari backend."
                action={{
                  label: 'Muat ulang',
                  onClick: () => void revenue.refetch(),
                }}
              />
            )}
          </section>
          <section>
            <h2 className="text-lg font-semibold">Statistik 7 hari</h2>
            {statData ? (
              <div className="mt-2 flex flex-wrap items-center gap-3">
                <Badge variant="secondary">Total {statData.total}</Badge>
                <Badge variant="secondary">Puncak {statData.peak}</Badge>
              </div>
            ) : (
              <EmptyState
                message="Statistik 7 hari belum tersedia dari backend."
                action={{
                  label: 'Muat ulang',
                  onClick: () => void stats.refetch(),
                }}
              />
            )}
          </section>
          <section>
            <h2 className="text-lg font-semibold">Kesehatan</h2>
            {healthData ? (
              <div className="mt-2 flex flex-wrap items-center gap-3">
                <Badge
                  variant={
                    healthData.health.database.ok ? 'secondary' : 'destructive'
                  }
                >
                  Database {healthData.health.database.ok ? 'aktif' : 'mati'}
                </Badge>
                <Badge
                  variant={
                    healthData.health.rabbitmq.ok ? 'secondary' : 'destructive'
                  }
                >
                  RabbitMQ {healthData.health.rabbitmq.ok ? 'aktif' : 'mati'}
                </Badge>
              </div>
            ) : (
              <EmptyState
                message="Status database dan RabbitMQ belum dikembalikan backend."
                action={{
                  label: 'Muat ulang',
                  onClick: () => void health.refetch(),
                }}
              />
            )}
          </section>
        </div>
      ) : null}
    </AppShell>
  )
}

export const Route = createFileRoute('/_protected/dashboard')({
  component: DashboardPage,
})
