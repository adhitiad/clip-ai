import { expect, test } from '@playwright/test'

import { mockApiGet, mockSession } from '../tests/helpers/server-fn'

const history = {
  status: 'success',
  page: 1,
  page_size: 20,
  total: 1,
  search: '',
  sort_by: 'id',
  sort_dir: 'desc',
  items: [
    {
      id: 7,
      title: 'Judul klip uji',
      score: 8,
      start_time: 0,
      end_time: 15,
      video_url: 'https://example.test/video',
    },
  ],
}

test('history menampilkan clip dari backend', async ({ page }) => {
  await mockSession(page)
  await mockApiGet(page, '/dashboard/history', history)
  await page.goto('/history')

  await expect(
    page.getByRole('heading', { name: 'Riwayat clip' }),
  ).toBeVisible()
  await expect(page.getByRole('cell', { name: 'Judul klip uji' })).toBeVisible()
})

test('history menampilkan empty state', async ({ page }) => {
  await mockSession(page)
  await mockApiGet(page, '/dashboard/history', {
    ...history,
    items: [],
    total: 0,
  })
  await page.goto('/history')

  await expect(
    page.getByText('Belum ada clip tersimpan. Buat clip dari halaman Shorts.'),
  ).toBeVisible()
})
