import { test, expect } from '@playwright/test'

test('homepage loads', async ({ page }) => {
  await page.goto('/landing')
  await expect(page).toHaveTitle(/Clip AI/i)
})
