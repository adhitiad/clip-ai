import type { CSSProperties } from 'react'
import { useEffect, useState } from 'react'

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '#/components/ui/table'
import { Button } from '#/components/ui/button'
import { Input } from '#/components/ui/input'
import { useDebouncedValue } from '#/hooks/use-debounced-value'

const SEARCH_DEBOUNCE_MS = 4000

type Accessor<T> = { key: keyof T & string; label: string }
type Action<T> = { label: string; onClick: (row: T) => void }
export type TableParams = {
  page: number
  pageSize: number
  search: string
  sortBy: string
  sortDir: string
}

export const DataTable = <T extends object>({
  data,
  accessors,
  total,
  params,
  onParamsChange,
  action,
}: {
  data: T[]
  accessors: Accessor<T>[]
  total: number
  params: TableParams
  onParamsChange: (next: TableParams) => void
  action?: Action<T>
}) => {
  const [searchInput, setSearchInput] = useState(params.search)
  const debouncedSearch = useDebouncedValue(searchInput, SEARCH_DEBOUNCE_MS)

  useEffect(() => {
    if (debouncedSearch === params.search) return
    onParamsChange({ ...params, search: debouncedSearch, page: 1 })
  }, [debouncedSearch, onParamsChange, params])

  const set = (patch: Partial<TableParams>) =>
    onParamsChange({ ...params, ...patch })
  const sort = (key: string) =>
    set({
      sortBy: key,
      sortDir:
        params.sortBy === key && params.sortDir === 'asc' ? 'desc' : 'asc',
      page: 1,
    })
  const sortMark = (key: string) =>
    params.sortBy === key ? (params.sortDir === 'asc' ? ' ↑' : ' ↓') : ''

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-end gap-3">
        <div className="space-y-1">
          <label htmlFor="table-search" className="text-sm">
            Cari
          </label>
          <Input
            id="table-search"
            name="table-search"
            autoComplete="off"
            value={searchInput}
            onChange={(event) => setSearchInput(event.target.value)}
            placeholder="Cari data…"
          />
        </div>
      </div>

      <div className="flex flex-wrap gap-2 md:hidden">
        {accessors.map((item) => (
          <Button
            key={item.key}
            type="button"
            variant="outline"
            size="sm"
            aria-label={`Urutkan ${item.label}`}
            onClick={() => sort(item.key)}
            className={`min-h-11 ${
              params.sortBy === item.key ? 'neon-glow border-[var(--neon)]' : ''
            }`}
          >
            {item.label}
            {sortMark(item.key)}
          </Button>
        ))}
      </div>

      <div className="hidden w-full overflow-x-auto md:block">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>No</TableHead>
              {accessors.map((item) => (
                <TableHead key={item.key}>
                  <button
                    type="button"
                    onClick={() => sort(item.key)}
                    className="min-h-11 text-left font-medium"
                    aria-label={`Urutkan ${item.label}`}
                  >
                    {item.label}
                    {sortMark(item.key)}
                  </button>
                </TableHead>
              ))}
              {action ? <TableHead>Aksi</TableHead> : null}
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.map((row, index) => (
              <TableRow key={index}>
                <TableCell>
                  {(params.page - 1) * params.pageSize + index + 1}
                </TableCell>
                {accessors.map((item) => (
                  <TableCell key={item.key} className="tabular-nums">
                    {String(row[item.key] ?? '')}
                  </TableCell>
                ))}
                {action ? (
                  <TableCell>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => action.onClick(row)}
                    >
                      {action.label}
                    </Button>
                  </TableCell>
                ) : null}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      <ul className="space-y-2 md:hidden">
        {data.map((row, index) => (
          <li
            key={index}
            className="neon-panel rise-in rounded-xl p-3"
            style={
              {
                '--rise-delay': `${Math.min(index, 6) * 45}ms`,
              } as CSSProperties
            }
          >
            <div className="mb-2 flex items-center justify-between gap-2">
              <span className="text-xs font-semibold tabular-nums text-[var(--neon)]">
                No {(params.page - 1) * params.pageSize + index + 1}
              </span>
              {action ? (
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="min-h-11"
                  onClick={() => action.onClick(row)}
                >
                  {action.label}
                </Button>
              ) : null}
            </div>
            <dl className="space-y-1">
              {accessors.map((item) => (
                <div
                  key={item.key}
                  className="flex items-baseline justify-between gap-3 text-sm"
                >
                  <dt className="shrink-0 text-[var(--ink-muted)]">
                    {item.label}
                  </dt>
                  <dd className="min-w-0 truncate text-right tabular-nums">
                    {String(row[item.key] ?? '')}
                  </dd>
                </div>
              ))}
            </dl>
          </li>
        ))}
      </ul>

      <div className="flex flex-wrap items-center gap-2">
        <Button
          type="button"
          variant="outline"
          className="min-h-11"
          disabled={params.page <= 1}
          onClick={() => set({ page: params.page - 1 })}
        >
          Sebelumnya
        </Button>
        <span className="text-sm tabular-nums">
          Halaman {params.page} dari{' '}
          {Math.max(1, Math.ceil(total / params.pageSize))}
        </span>
        <Button
          type="button"
          variant="outline"
          className="min-h-11 neon-glow"
          disabled={params.page * params.pageSize >= total}
          onClick={() => set({ page: params.page + 1 })}
        >
          Berikutnya
        </Button>
      </div>
    </div>
  )
}
