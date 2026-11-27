import { createFileRoute } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'

import { AppShell } from '#/components/app-shell'
import { ErrorState, LoadingState } from '#/components/states'
import { Badge } from '#/components/ui/badge'
import { modelStatusQuery } from '#/lib/queries'
import type { ModelStatus } from '#/type/api'

const ToolsPage = () => {
  const query = useQuery(modelStatusQuery())
  const data = query.data as ModelStatus | undefined

  return (
    <AppShell>
      <h1 className="neon-text display-title rise-in text-4xl">Alat</h1>
      <p className="mt-1 text-[15px] leading-relaxed text-muted-foreground">
        Penilaian viral berbasis aturan, tanpa model terlatih.
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
      {data ? (
        <div className="mt-6 space-y-3">
          <div className="flex flex-wrap items-center gap-3">
            <Badge variant={data.model.enabled ? 'secondary' : 'outline'}>
              {data.model.enabled ? 'Aktif' : 'Nonaktif'}
            </Badge>
            <Badge variant="outline">{data.model.confidence_mode}</Badge>
          </div>
          <p className="text-sm text-muted-foreground">{data.message}</p>
        </div>
      ) : null}
    </AppShell>
  )
}

export const Route = createFileRoute('/_protected/tools')({
  component: ToolsPage,
})
