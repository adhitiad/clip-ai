import { expect, test } from '@playwright/test'

import { mockApiGets, mockSession } from '../tests/helpers/server-fn'

test('dashboard menampilkan ringkasan dari backend', async ({ page }) => {
  await mockSession(page)
  await mockApiGets(page, {
    '/dashboard/overview': {
      status: 'success',
      clips: { total: 4, average_score: 7.25, max_score: 9 },
      recent: [],
    },
    '/dashboard/stats': { status: 'success', daily: {}, total: 4, peak: 2 },
    '/dashboard/health': {
      status: 'success',
      health: { database: { ok: true }, rabbitmq: { ok: false } },
    },
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
      recommendations: ['Tambah CTA di akhir klip.'],
      generated_at: '2026-11-25T00:00:00+00:00',
      note: 'Saran AI.',
    },
  })

  await page.goto('/dashboard')
  await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible()
  await expect(page.getByText('Total 4').first()).toBeVisible()
  await expect(page.getByText('Rata-rata 7.25')).toBeVisible()

  await page.getByRole('button', { name: 'Saran AI' }).click()
  await expect(page.getByText('Tambah CTA di akhir klip.')).toBeVisible()
})
