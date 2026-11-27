import { expect, test } from '@playwright/test'

import { mockApiGets, mockSession } from '../tests/helpers/server-fn'

const fixtures = {
  '/dashboard/health': {
    status: 'success',
    health: { database: { ok: true }, rabbitmq: { ok: true } },
  },
  '/ops/queue': {
    status: 'success',
    broker: { ok: true },
    counts: { SUCCESS: 0 },
    dead_letter_queue: 'shorts-render-dlq',
  },
  '/ops/tasks': [],
  '/dashboard/overview': {
    status: 'success',
    clips: { total: 2, average_score: 7.1, max_score: 9 },
  },
  '/dashboard/stats': { status: 'success', daily: {}, total: 2, peak: 1 },
  '/revenue/summary': {
    status: 'success',
    total_available: 0,
    currency: 'USD',
    platforms: [],
  },
  '/revenue/advice': {
    status: 'success',
    provider: 'openrouter',
    model: 'free',
    recommendations: ['Uji hook 3 detik.'],
    generated_at: '2026-11-25T00:00:00+00:00',
    note: 'Saran AI.',
  },
}

test('protected menampilkan status dan aksi kontekstual', async ({ page }) => {
  await mockSession(page)
  await mockApiGets(page, fixtures)
  await page.goto('/protected')

  await expect(page.getByRole('heading', { name: 'Ruang kerja' })).toBeVisible()
  await expect(page.getByText('RabbitMQ aktif')).toBeVisible()
  await expect(
    page.getByRole('link', { name: 'Buat brief baru' }),
  ).toBeVisible()
  await expect(
    page.getByText('Belum ada task. Buat brief di Shorts.'),
  ).toBeVisible()
})

test('protected bisa meminta saran pendapatan', async ({ page }) => {
  await mockSession(page)
  await mockApiGets(page, fixtures)
  await page.goto('/protected')

  await page.getByRole('button', { name: 'Ambil saran' }).click()
  await expect(page.getByText('Uji hook 3 detik.')).toBeVisible()
})

test('tautan jejak kerja menuju backend', async ({ page }) => {
  await mockSession(page)
  await mockApiGets(page, fixtures)
  await page.goto('/protected')

  await page.getByRole('link', { name: 'Semua data backend' }).click()
  await expect(page).toHaveURL(/\/backend$/)
})
