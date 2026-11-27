import type { HistoryItem } from '#/type/api'

import { DataTable } from '#/components/data-table'
import type { TableParams } from '#/components/data-table'

export const HistoryTable = ({
  items,
  total,
  params,
  onParamsChange,
  onRefresh,
}: {
  items: HistoryItem[]
  total: number
  params: TableParams
  onParamsChange: (next: TableParams) => void
  onRefresh: () => void
}) => (
  <DataTable<HistoryItem>
    data={items}
    total={total}
    params={params}
    onParamsChange={onParamsChange}
    accessors={[
      { key: 'title', label: 'Judul' },
      { key: 'score', label: 'Skor' },
      { key: 'id', label: 'ID' },
    ]}
    action={{ label: 'Muat ulang', onClick: onRefresh }}
  />
)
