import { createFileRoute } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'
import { useStore } from '@tanstack/react-store'

import { AppShell } from '#/components/app-shell'
import { EmptyState, ErrorState, LoadingState } from '#/components/states'
import { Input } from '#/components/ui/input'
import { Label } from '#/components/ui/label'
import { trendingQuery } from '#/lib/queries'
import { trendingGeoStore } from '#/stores/ui'
import type { Trending } from '#/type/api'

const NichePage = () => {
  const { geo, maxItems } = useStore(trendingGeoStore)
  const query = useQuery(trendingQuery(geo, maxItems))
  const data = query.data as Trending | undefined
  const items = data?.trending ?? []

  return (
    <AppShell>
      <h1 className="neon-text display-title rise-in text-4xl">Penemuan</h1>
      <p className="mt-1 text-[15px] leading-relaxed text-muted-foreground">
        Topik Google Trends per wilayah, dengan batas jumlah dari backend.
      </p>
      <div className="mt-4 flex flex-wrap items-end gap-3">
        <div className="space-y-1">
          <Label htmlFor="geo">Wilayah</Label>
          <Input
            id="geo"
            name="geo"
            autoComplete="off"
            spellCheck={false}
            className="min-h-11"
            value={geo}
            onChange={(event) =>
              trendingGeoStore.setState((s) => ({
                ...s,
                geo: event.target.value,
              }))
            }
          />
          <p className="text-sm text-[var(--ink-muted)]">
            Kode Google Trends: id, us, atau global.
          </p>
        </div>
        <div className="space-y-1">
          <Label htmlFor="maxItems">Jumlah topik</Label>
          <Input
            id="maxItems"
            name="maxItems"
            type="number"
            inputMode="numeric"
            autoComplete="off"
            min={5}
            max={50}
            className="min-h-11"
            value={maxItems}
            onChange={(event) =>
              trendingGeoStore.setState((s) => ({
                ...s,
                maxItems: Number(event.target.value),
              }))
            }
          />
          <p className="text-sm text-[var(--ink-muted)]">
            Antara 5 dan 50, sesuai batas backend.
          </p>
        </div>
      </div>
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
          {items.length > 0 ? (
            <ul className="space-y-2">
              {items.map((item, index) => (
                <li
                  key={index}
                  className="border-b border-[var(--line)] py-2 text-sm"
                >
                  {item.title ?? item.query ?? JSON.stringify(item)}
                </li>
              ))}
            </ul>
          ) : (
            <EmptyState
              message={`Google Trends tidak mengembalikan topik untuk ${geo}. Coba wilayah lain.`}
              action={{
                label: 'Muat ulang',
                onClick: () => void query.refetch(),
              }}
            />
          )}
        </div>
      ) : null}
    </AppShell>
  )
}

export const Route = createFileRoute('/_protected/niche')({
  component: NichePage,
})
