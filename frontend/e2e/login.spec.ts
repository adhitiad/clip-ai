import { expect, test } from '@playwright/test'

test('login hanya punya satu aksi Google', async ({ page }) => {
  await page.goto('/login')
  await expect(
    page.getByRole('heading', { name: 'Masuk ke studio.' }),
  ).toBeVisible()
  await expect(
    page.getByRole('button', { name: 'Lanjut dengan Google' }),
  ).toBeEnabled()
  await expect(page.getByLabel('Kata sandi')).toHaveCount(0)
})
