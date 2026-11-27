import { expect, test } from '@playwright/test'

import { mockSession, stubServerFn } from '../tests/helpers/server-fn'

test('/backend mengonsumsi endpoint GET dan kontrolnya bekerja', async ({
  page,
}) => {
  await mockSession(page)
  await stubServerFn(page, 'apiGet', { status: 'success', items: [] })
  await stubServerFn(page, 'apiGetDynamic', { status: 'success' })

  await page.goto('/backend')
  await page.getByRole('button', { name: 'Muat data backend' }).click()
  await expect(
    page.getByRole('heading', { name: 'Data Backend' }),
  ).toBeVisible()

  const refresh = page.getByRole('button', { name: 'Muat ulang' })
  expect(await refresh.count()).toBeGreaterThan(20)
  await refresh.first().click()

  await page.getByLabel('ID clip').fill('1')
  await page.getByLabel('ID task').fill('abc-123')
  await page.getByRole('button', { name: 'Ambil saran' }).click()

  await expect(page.getByRole('heading', { name: 'Detail clip' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Detail task' })).toBeVisible()
})
