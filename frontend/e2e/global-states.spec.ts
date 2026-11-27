import { expect, test } from '@playwright/test'

import { mockSession } from '../tests/helpers/server-fn'

test('rute tidak ditemukan memakai halaman anime', async ({ page }) => {
  await page.goto('/tidak-ada')
  await expect(
    page.getByRole('heading', { name: 'Halaman tidak ditemukan.' }),
  ).toBeVisible()
})

test('tombol not found kembali ke beranda', async ({ page }) => {
  await mockSession(page)
  await page.goto('/tidak-ada')
  await page.getByRole('link', { name: 'Kembali ke beranda' }).click()
  await expect(page).toHaveURL(/\/$/)
})
