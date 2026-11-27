import { expect, test } from '@playwright/test'

import { mockSession } from '../tests/helpers/server-fn'

test('session owner membuka home', async ({ page }) => {
  await mockSession(page)
  await page.goto('/')
  await expect(
    page.getByRole('heading', { name: 'Clip AI: Model Provider' }),
  ).toBeVisible()
  await expect(page.getByRole('button', { name: /OW Owner/ })).toBeVisible()
})
