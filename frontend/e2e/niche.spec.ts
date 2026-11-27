import { expect, test } from '@playwright/test'

import { mockApiGet, mockSession } from '../tests/helpers/server-fn'

test('niche menampilkan topik trends dan bisa mengubah wilayah', async ({
  page,
}) => {
  await mockSession(page)
  await mockApiGet(page, '/niche/trending', {
    status: 'success',
    geo: 'id',
    total: 1,
    trending: [{ title: 'Topik uji', query: 'topik uji' }],
  })
  await page.goto('/niche')

  await expect(page.getByRole('heading', { name: 'Penemuan' })).toBeVisible()
  await expect(page.getByText('Topik uji')).toBeVisible()

  await page.getByLabel('Wilayah').fill('us')
  await expect(page.getByLabel('Wilayah')).toHaveValue('us')
})
