import { createStore } from '@tanstack/store'

// Nilai awal mengikuti default kontrak backend, bukan pilihan frontend:
// GET /dashboard/history: page=1, page_size=20
// GET /niche/trending: geo='id', max_items=20
export const historyPageStore = createStore({
  page: 1,
  pageSize: 20,
  search: '',
  sortBy: 'id',
  sortDir: 'desc',
})
export const trendingGeoStore = createStore({ geo: 'id', maxItems: 20 })
