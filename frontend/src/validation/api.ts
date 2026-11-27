import { z } from 'zod'

export const API_PATHS = [
  '/auth/me',
  '/clips',
  '/dashboard/health',
  '/dashboard/history',
  '/dashboard/overview',
  '/dashboard/profile',
  '/dashboard/stats',
  '/niche/find-videos',
  '/niche/search-web',
  '/niche/suggest',
  '/niche/trending',
  '/ops/access-log',
  '/ops/audit',
  '/ops/cache',
  '/ops/export',
  '/ops/queue',
  '/ops/tasks',
  '/ops/traces',
  '/ops/workers',
  '/revenue/advice',
  '/revenue/summary',
  '/settings/me',
  '/settings/owner',
  '/tools/calibration',
  '/tools/model-status',
  '/tools/platforms',
  '/tools/providers',
  '/youtube/scheduler/status',
] as const

export const apiGetSchema = z.object({
  path: z.enum(API_PATHS),
  query: z.record(z.string(), z.string()).optional(),
})

export const apiGetDynamicSchema = z.object({
  path: z.string().regex(/^\/(clips|tasks)\/\d+$/),
  query: z.record(z.string(), z.string()).optional(),
})

export const historyQuerySchema = z.object({
  page: z.number().int().min(1).default(1),
  pageSize: z.number().int().min(1).max(100).default(20),
})

export const trendingQuerySchema = z.object({
  geo: z.string().min(2).max(6).default('id'),
  maxItems: z.number().int().min(5).max(50).default(20),
})

export type ApiPath = (typeof API_PATHS)[number]
