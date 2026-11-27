import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'
import { useStore } from '@tanstack/react-store'

import { AppShell } from '#/components/app-shell'
import { HistoryTable } from '#/components/history-table'
import { EmptyState, ErrorState, LoadingState } from '#/components/states'
import { historyQuery } from '#/lib/queries'
import { historyPageStore } from '#/stores/ui'
import type { History } from '#/type/api'

const HistoryPage = () => {
  const navigate = useNavigate()
  const params = useStore(historyPageStore)
  const query = useQuery(
    historyQuery({
      page: params.page,
      pageSize: params.pageSize,
      search: params.search,
      sortBy: params.sortBy,
      sortDir: params.sortDir,
    }),
  )
  const data = query.data as History | undefined

  return (
    <AppShell>
      <h1 className="neon-text display-title rise-in text-4xl">Riwayat clip</h1>
      <p className="mt-1 text-[15px] leading-relaxed text-muted-foreground">
        Cari, urutkan, dan buka clip yang tersimpan di backend.
      </p>
      {query.isLoading ? (
        <div className="mt-6">
          <LoadingState />
        </div>
      ) : null}
      {query.error ? (
        <div className="mt-6">
          <ErrorState
            message={query.error.message}
            onRetry={() => void query.refetch()}
          />
        </div>
      ) : null}
      {!query.isLoading && !query.error ? (
        <div className="mt-6">
          {data && data.items.length > 0 ? (
            <HistoryTable
              items={data.items}
              total={data.total}
              params={{
                page: params.page,
                pageSize: params.pageSize,
                search: params.search,
                sortBy: params.sortBy,
                sortDir: params.sortDir,
              }}
              onParamsChange={(next) => historyPageStore.setState(() => next)}
              onRefresh={() => void query.refetch()}
            />
          ) : (
            <EmptyState
              message="Belum ada clip tersimpan. Buat clip dari halaman Shorts."
              action={{
                label: 'Buka Shorts',
                onClick: () => void navigate({ to: '/shorts' }),
              }}
            />
          )}
        </div>
      ) : null}
    </AppShell>
  )
}

export const Route = createFileRoute('/_protected/history')({
  component: HistoryPage,
})
