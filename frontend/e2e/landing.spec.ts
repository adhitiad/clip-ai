import { expect, test } from '@playwright/test'

test('landing menampilkan hero dan memilih platform', async ({ page }) => {
  await page.goto('/landing')
  await expect(
    page.getByRole('heading', { name: /Dari riset sampai klip siap unggah/ }),
  ).toBeVisible()

  await expect(page.getByText('Hook 3 detik')).toBeVisible()
  await page.waitForTimeout(1000)
  await page.getByRole('button', { name: 'reels' }).click()
  await expect(page.getByText('Hook visual')).toBeVisible()
})

test('tombol landing menuju login', async ({ page }) => {
  await page.goto('/landing')
  await page.waitForTimeout(600)
  await page.getByRole('link', { name: 'Masuk ke studio' }).first().click()
  await expect(page).toHaveURL(/\/login$/)
})
