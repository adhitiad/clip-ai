export interface ClipSummary {
  total: number
  average_score: number
  max_score: number
}

export interface RecentClip {
  id: number
  title: string
  score: number | null
  video_url: string | null
}

export interface Overview {
  status: string
  user: { id: number; email: string; username: string }
  clips: ClipSummary
  recent: RecentClip[]
  generated_at: string
}

export interface HistoryItem {
  id: number
  title: string
  score: number | null
  start_time: number | null
  end_time: number | null
  video_url: string | null
}

export interface History {
  status: string
  page: number
  page_size: number
  total: number
  search: string
  sort_by: string
  sort_dir: string
  items: HistoryItem[]
}

export interface Stats {
  status: string
  daily: Record<string, number>
  total: number
  peak: number
}

export interface Health {
  status: string
  health: {
    database: { ok: boolean }
    rabbitmq: { ok: boolean }
  }
}

export interface TrendingItem {
  title?: string
  query?: string
  url?: string
  views?: number
  [key: string]: unknown
}

export interface Trending {
  status: string
  geo: string
  total: number
  trending: TrendingItem[]
}

export interface ModelStatus {
  status: string
  model: {
    trained: boolean
    enabled: boolean
    confidence_mode: string
  }
  message: string
}

export interface PlatformRevenue {
  platform: string
  available: boolean
  status: string
  amount: number | null
  currency: string | null
  period_start: string
  period_end: string
  source: string
  note: string
}

export interface RevenueSummary {
  status: string
  days: number
  platforms: PlatformRevenue[]
  total_available: number
  currency: string
  generated_at: string
  note: string
}

export interface RevenueAdvice {
  status: string
  provider: string
  model: string
  recommendations: string[]
  generated_at: string
  note: string
}
