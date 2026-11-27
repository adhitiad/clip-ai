import { queryOptions } from '@tanstack/react-query'

import { apiGet, apiGetDynamic } from '#/lib/api'

const get = (
  path: Parameters<typeof apiGet>[0]['data']['path'],
  query?: Record<string, string>,
) => apiGet({ data: { path, query } })

export const authMeQuery = () =>
  queryOptions({
    queryKey: ['auth-me'],
    queryFn: () => get('/auth/me'),
  })

export const overviewQuery = () =>
  queryOptions({
    queryKey: ['overview'],
    queryFn: () => get('/dashboard/overview'),
  })

export const profileQuery = () =>
  queryOptions({
    queryKey: ['profile'],
    queryFn: () => get('/dashboard/profile'),
  })

export const statsQuery = () =>
  queryOptions({
    queryKey: ['stats'],
    queryFn: () => get('/dashboard/stats'),
  })

export const healthQuery = () =>
  queryOptions({
    queryKey: ['health'],
    queryFn: () => get('/dashboard/health'),
  })

export const historyQuery = (params: {
  page: number
  pageSize: number
  search: string
  sortBy: string
  sortDir: string
}) =>
  queryOptions({
    queryKey: ['history', params],
    queryFn: () =>
      get('/dashboard/history', {
        page: String(params.page),
        page_size: String(params.pageSize),
        search: params.search,
        sort_by: params.sortBy,
        sort_dir: params.sortDir,
      }),
  })

export const clipsQuery = () =>
  queryOptions({
    queryKey: ['clips'],
    queryFn: () => get('/clips'),
  })

export const clipDetailQuery = (id: string) =>
  queryOptions({
    queryKey: ['clip-detail', id],
    queryFn: () => apiGetDynamic({ data: { path: `/clips/${id}` } }),
    enabled: /^\d+$/.test(id),
  })

export const taskDetailQuery = (id: string) =>
  queryOptions({
    queryKey: ['task-detail', id],
    queryFn: () => apiGetDynamic({ data: { path: `/tasks/${id}` } }),
    enabled: /^[a-zA-Z0-9_-]+$/.test(id),
  })

export const trendingQuery = (geo: string, maxItems: number) =>
  queryOptions({
    queryKey: ['trending', geo, maxItems],
    queryFn: () => get('/niche/trending', { geo, max_items: String(maxItems) }),
  })

export const suggestQuery = (geo: string, maxTrends: number) =>
  queryOptions({
    queryKey: ['suggest', geo, maxTrends],
    queryFn: () =>
      get('/niche/suggest', { geo, max_trends: String(maxTrends) }),
  })

export const findVideosQuery = (query: string, maxResults: number) =>
  queryOptions({
    queryKey: ['find-videos', query, maxResults],
    queryFn: () =>
      get('/niche/find-videos', {
        query,
        max_results: String(maxResults),
      }),
    enabled: query.trim().length > 0,
  })

export const searchWebQuery = (query: string, searchType: string) =>
  queryOptions({
    queryKey: ['search-web', query, searchType],
    queryFn: () =>
      get('/niche/search-web', {
        query,
        num_results: '5',
        search_type: searchType,
      }),
    enabled: query.trim().length > 0,
  })

export const providersQuery = () =>
  queryOptions({
    queryKey: ['providers'],
    queryFn: () => get('/tools/providers'),
  })

export const platformsQuery = () =>
  queryOptions({
    queryKey: ['platforms'],
    queryFn: () => get('/tools/platforms'),
  })

export const modelStatusQuery = () =>
  queryOptions({
    queryKey: ['model-status'],
    queryFn: () => get('/tools/model-status'),
  })

export const calibrationQuery = () =>
  queryOptions({
    queryKey: ['calibration'],
    queryFn: () => get('/tools/calibration'),
  })

export const opsTasksQuery = () =>
  queryOptions({
    queryKey: ['ops-tasks'],
    queryFn: () => get('/ops/tasks'),
  })

export const opsQueueQuery = () =>
  queryOptions({
    queryKey: ['ops-queue'],
    queryFn: () => get('/ops/queue'),
  })

export const opsWorkersQuery = () =>
  queryOptions({
    queryKey: ['ops-workers'],
    queryFn: () => get('/ops/workers'),
  })

export const opsCacheQuery = () =>
  queryOptions({
    queryKey: ['ops-cache'],
    queryFn: () => get('/ops/cache'),
  })

export const opsTracesQuery = () =>
  queryOptions({
    queryKey: ['ops-traces'],
    queryFn: () => get('/ops/traces'),
  })

export const opsExportQuery = () =>
  queryOptions({
    queryKey: ['ops-export'],
    queryFn: () => get('/ops/export'),
  })

export const opsAuditQuery = () =>
  queryOptions({
    queryKey: ['ops-audit'],
    queryFn: () => get('/ops/audit'),
  })

export type AccessLogEntry = {
  timestamp: string
  level: string
  actor: string
  flag: string
  ip: string
  email: string
  user_type: string
  device_id: string
  device_name: string
  browser: string
  http_version: string
  method: string
  path: string
  status: number
  keterangan: string
  line: string
}

export const opsAccessLogQuery = () =>
  queryOptions({
    queryKey: ['ops-access-log'],
    queryFn: async () => (await get('/ops/access-log')) as AccessLogEntry[],
  })

export const settingsMeQuery = () =>
  queryOptions({
    queryKey: ['settings-me'],
    queryFn: () => get('/settings/me'),
  })

export const settingsOwnerQuery = () =>
  queryOptions({
    queryKey: ['settings-owner'],
    queryFn: () => get('/settings/owner'),
  })

export const youtubeSchedulerQuery = () =>
  queryOptions({
    queryKey: ['youtube-scheduler'],
    queryFn: () => get('/youtube/scheduler/status'),
  })

export const revenueSummaryQuery = () =>
  queryOptions({
    queryKey: ['revenue-summary'],
    queryFn: () => get('/revenue/summary'),
  })

export const revenueAdviceQuery = () =>
  queryOptions({
    queryKey: ['revenue-advice'],
    queryFn: () => get('/revenue/advice'),
    enabled: false,
  })
